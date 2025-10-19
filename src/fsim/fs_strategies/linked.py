import struct
from typing import List, Dict, Any, Iterable, Optional, Callable

# Importamos la clase base (contrato) y los protocolos
from ..core.filesystem_base import FilesystemBase, DiskLike, FreeSpaceManagerLike

# --- Constantes para la gestión de punteros ---

# Marcador para el final de la cadena de bloques (fin de archivo)
END_OF_FILE_MARKER = -1

# Usamos un entero 'long long' (8 bytes) para los punteros.
# '!' = network (big-endian), 'q' = signed long long
POINTER_FORMAT = "!q"
POINTER_SIZE_BYTES = struct.calcsize(POINTER_FORMAT)


class LinkedFS(FilesystemBase):
    """
    Implementación de un sistema de archivos con asignación enlazada (Linked Allocation).

    Lógica:
    - El directorio (self.file_table) almacena el bloque de inicio de cada archivo.
    - Cada bloque en el disco utiliza sus primeros 'POINTER_SIZE_BYTES' bytes
      para almacenar el índice del *siguiente* bloque.
    - El último bloque de un archivo apunta a 'END_OF_FILE_MARKER'.
    - El resto del bloque (block_size - POINTER_SIZE_BYTES) se usa para datos.
    """

    def __init__(
        self,
        disk: DiskLike,
        free_space_manager: FreeSpaceManagerLike,
        *,
        on_event: Optional[Callable[..., None]] = None,
    ) -> None:
        """
        Inicializa el FS. Valida que los bloques sean lo suficientemente grandes
        para albergar, como mínimo, un puntero.
        """
        super().__init__(disk, free_space_manager, on_event=on_event)

        # Validación crítica: ¿Caben nuestros punteros en un bloque?
        if self.disk.block_size <= POINTER_SIZE_BYTES:
            raise ValueError(
                f"El tamaño de bloque ({self.disk.block_size}B) debe ser "
                f"mayor que el tamaño del puntero ({POINTER_SIZE_BYTES}B)"
            )

    # ---------------------------------------------------------------------
    # Helpers internos para manejo de punteros
    # ---------------------------------------------------------------------

    def _read_pointer(self, block_index: int) -> int:
        """
        Lee el bloque 'block_index' del disco y extrae el puntero
        (los primeros bytes) del siguiente bloque.
        """
        data = self.disk.read_block(block_index)
        if data is None or len(data) < POINTER_SIZE_BYTES:
            # Esto indica corrupción. Un bloque asignado en una cadena NUNCA
            # debería estar vacío o ser más pequeño que el puntero.
            raise IOError(
                f"Error de E/S: Bloque {block_index} en la cadena está "
                f"corrupto o vacío (no se pudo leer el puntero)."
            )

        # Desempaca los primeros bytes para obtener el índice
        (next_block_index,) = struct.unpack(POINTER_FORMAT, data[:POINTER_SIZE_BYTES])
        return int(next_block_index)

    def _write_pointer(self, block_index: int, next_block_index: int) -> None:
        """
        Escribe el puntero 'next_block_index' al inicio del bloque 'block_index'.
        Preserva los datos de usuario existentes en ese bloque si los hay.
        """
        # Empaca el puntero en formato bytes
        pointer_bytes = struct.pack(POINTER_FORMAT, next_block_index)

        # Lee los datos actuales para no borrarlos
        current_data = self.disk.read_block(block_index)

        user_data = b""
        if current_data is not None and len(current_data) > POINTER_SIZE_BYTES:
            # Preserva solo los datos de usuario (todo después del puntero antiguo)
            user_data = current_data[POINTER_SIZE_BYTES:]

        # Combina el nuevo puntero con los datos de usuario existentes
        full_block_data = pointer_bytes + user_data
        
        # Escribe de vuelta al disco. 
        # (disk.write_block valida que no exceda self.block_size)
        self.disk.write_block(block_index, full_block_data)

    def _get_all_blocks(self, name: str) -> List[int]:
        """
        Recorre la cadena completa del archivo 'name' y devuelve
        la lista de todos sus bloques físicos. Usado por delete().
        """
        self._assert_file_exists(name)
        meta = self.file_table[name]
        
        indices = []
        current_block_idx = meta["start_block"]
        
        # Confiamos en el tamaño lógico almacenado
        for _ in range(meta["size_blocks"]): 
            if current_block_idx == END_OF_FILE_MARKER:
                raise IOError(f"Corrupción detectada: Fin de archivo prematuro para '{name}'")
            
            if current_block_idx in indices:
                raise IOError(f"Corrupción detectada: Bucle en la cadena de '{name}' en el bloque {current_block_idx}")

            indices.append(current_block_idx)
            # Leemos el puntero para la siguiente iteración
            current_block_idx = self._read_pointer(current_block_idx)
        
        return indices

    # ---------------------------------------------------------------------
    # API OBLIGATORIA (Implementación del contrato)
    # ---------------------------------------------------------------------

    def create(self, name: str, size_blocks: int) -> None:
        """
        Crea un archivo 'name' de 'size_blocks', solicitando bloques
        no contiguos al FSM y enlazándolos en el disco.
        """
        self._assert_new_file(name)
        self._assert_positive_blocks(size_blocks)

        # 1. Solicitar 'n' bloques (no contiguos)
        # Esto puede lanzar MemoryError si no hay espacio, lo cual es correcto.
        allocated_indices = self.fsm.allocate(size_blocks, contiguous=False)

        # 2. Almacenar metadatos en el directorio
        self.file_table[name] = {
            "size_blocks": size_blocks,
            "start_block": allocated_indices[0],
        }

        # 3. Enlazar los bloques en el disco
        for i in range(size_blocks - 1):
            current_idx = allocated_indices[i]
            next_idx = allocated_indices[i+1]
            # Escribe el puntero (p.ej., Bloque 5 apunta a Bloque 12)
            self._write_pointer(current_idx, next_idx)

        # 4. Marcar el último bloque
        last_idx = allocated_indices[-1]
        self._write_pointer(last_idx, END_OF_FILE_MARKER)

        # 5. Emitir evento para métricas
        self._emit(
            "create",
            name=name,
            size_blocks=size_blocks,
            allocated=allocated_indices,
        )

    def delete(self, name: str) -> None:
        """
        Elimina el archivo 'name', recorriendo su cadena de bloques
        para liberarlos todos en el FSM.
        """
        self._assert_file_exists(name)

        # 1. Recorrer la cadena para saber qué bloques liberar
        try:
            blocks_to_free = self._get_all_blocks(name)
        except IOError as e:
            print(f"Advertencia: No se pudo eliminar '{name}' limpiamente: {e}. "
                  "Se intentará liberar lo encontrado...")
            # Si hay corrupción, al menos intentamos liberar lo que se pudo leer
            meta = self.file_table.get(name, {})
            start_block = meta.get("start_block")
            if isinstance(start_block, int):
                # Intenta un recorrido simple sin garantía de tamaño
                indices = []
                curr = start_block
                while curr != END_OF_FILE_MARKER and curr not in indices and len(indices) < self.n_blocks:
                    indices.append(curr)
                    try: curr = self._read_pointer(curr)
                    except IOError: break
                blocks_to_free = indices
            else:
                blocks_to_free = []

        # 2. Eliminar la entrada del directorio (primero)
        del self.file_table[name]

        # 3. Liberar los bloques en el FSM
        if blocks_to_free:
            try:
                self.fsm.free(blocks_to_free)
            except (ValueError, IndexError) as e:
                # Error en FSM (ej. doble liberación). Solo loguear.
                print(f"Error al liberar bloques para '{name}': {e}")

        # 4. Emitir evento
        self._emit("delete", name=name, freed=blocks_to_free)

    def _resolve_range(self, name: str, offset: int, n_blocks: int) -> List[int]:
        """
        Devuelve la lista de bloques físicos correspondientes al rango
        lógico [offset, offset + n_blocks) del archivo 'name'.
        
        Esta es la operación costosa en "Linked", ya que requiere 'offset'
        lecturas de punteros para llegar al inicio del rango.
        """
        self._assert_file_exists(name)
        meta = self.file_table[name]
        
        # Validación de rango (métodos heredados de FilesystemBase)
        self._assert_range_within_size(name, offset, n_blocks)

        current_block_idx = meta["start_block"]

        # 1. "Seek" (Salto): Recorrer la cadena 'offset' veces
        # (El Dev 1 midiendo esto notará el costo de acceso aleatorio)
        for _ in range(offset):
            current_block_idx = self._read_pointer(current_block_idx)
            if current_block_idx == END_OF_FILE_MARKER:
                # Esto no debería pasar si _assert_range_within_size es correcto
                raise IndexError(
                    f"Corrupción: EOF alcanzado prematuramente "
                    f"mientras se buscaba el offset {offset} en '{name}'"
                )

        # 2. "Collect" (Recolección): Juntar los 'n_blocks' físicos
        physical_indices = []
        for i in range(n_blocks):
            if current_block_idx == END_OF_FILE_MARKER:
                 raise IndexError(
                    f"Corrupción: EOF alcanzado prematuramente "
                    f"mientras se leían {n_blocks} bloques en '{name}'"
                )
            
            physical_indices.append(current_block_idx)
            
            # Solo leemos el siguiente puntero si no es el último bloque del rango
            if i < (n_blocks - 1):
                current_block_idx = self._read_pointer(current_block_idx)
        
        return physical_indices

    def read(
        self, name: str, offset: int, n_blocks: int, access_mode: str = "seq"
    ) -> List[bytes]:
        """
        Lee 'n_blocks' lógicos desde 'offset' del archivo 'name'.
        Devuelve solo los datos de *usuario* (sin los punteros).
        """
        self._assert_file_exists(name)
        self._assert_positive_blocks(n_blocks)
        self._assert_non_negative(offset)
        
        # 1. Obtener la lista de bloques físicos a leer
        physical_indices = self._resolve_range(name, offset, n_blocks)

        # 2. Emitir evento (para que métricas mida los saltos)
        self._emit(
            "read",
            name=name,
            offset=offset,
            n_blocks=n_blocks,
            physical=physical_indices,
            access_mode=access_mode
        )

        # 3. Leer del disco y extraer datos de usuario
        payloads = []
        for block_idx in physical_indices:
            full_data = self.disk.read_block(block_idx)
            
            if full_data is None:
                # Un bloque en la cadena no debería estar vacío, pero si lo está,
                # devolvemos datos vacíos por seguridad.
                payloads.append(b"")
            else:
                # Devolvemos solo los bytes *después* del puntero
                user_data = full_data[POINTER_SIZE_BYTES:]
                payloads.append(user_data)
        
        return payloads

    def write(
        self,
        name: str,
        offset: int,
        n_blocks: int,
        data: Optional[Iterable[bytes]] = None,
    ) -> None:
        """
        Escribe 'n_blocks' lógicos desde 'offset' en 'name'.
        Esto sobrescribe datos de usuario, pero *preserva* los punteros.
        Esta política no soporta crecimiento de archivo.
        """
        self._assert_file_exists(name)
        self._assert_positive_blocks(n_blocks)
        self._assert_non_negative(offset)

        # 1. Obtener bloques físicos
        physical_indices = self._resolve_range(name, offset, n_blocks)

        # 2. Preparar los datos a escribir
        data_list: List[bytes]
        if data is None:
            # Si no se proveen datos, simulamos escritura con bytes vacíos
            data_list = [b""] * n_blocks
        else:
            data_list = list(data)
            if len(data_list) != n_blocks:
                raise ValueError(
                    f"Se esperaban {n_blocks} bloques de datos, "
                    f"pero se recibieron {len(data_list)}"
                )

        # 3. Emitir evento
        self._emit(
            "write",
            name=name,
            offset=offset,
            n_blocks=n_blocks,
            physical=physical_indices
        )

        # 4. Escribir en el disco, preservando punteros
        user_data_max_size = self.disk.block_size - POINTER_SIZE_BYTES
        
        for i in range(n_blocks):
            block_idx = physical_indices[i]
            user_payload = data_list[i]

            # Validar que los datos del usuario quepan
            if len(user_payload) > user_data_max_size:
                raise ValueError(
                    f"Payload del bloque {i} ({len(user_payload)}B) excede "
                    f"el espacio de usuario disponible ({user_data_max_size}B)"
                )
            
            # ¡Crítico! Debemos leer el puntero actual para no romper la cadena
            current_pointer = self._read_pointer(block_idx)
            pointer_bytes = struct.pack(POINTER_FORMAT, current_pointer)
            
            # Combinar el puntero existente + nuevos datos de usuario
            full_block_data = pointer_bytes + user_payload
            
            # Escribir el bloque completo
            self.disk.write_block(block_idx, full_block_data)
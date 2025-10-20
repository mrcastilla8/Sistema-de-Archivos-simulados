# Owner: Dev 5
from __future__ import annotations
import struct
from typing import Iterable, List, Any, Dict, Optional, Callable

# Importamos la base y los protocolos
from ..core.filesystem_base import FilesystemBase, DiskLike, FreeSpaceManagerLike

# --- Constantes de Punteros (copiadas de linked.py para consistencia) ---
# Usamos un entero 'long long' (8 bytes) para los punteros de bloque.
# '!' = network (big-endian), 'q' = signed long long
POINTER_FORMAT_CHAR = "q"
POINTER_SIZE_BYTES = struct.calcsize(POINTER_FORMAT_CHAR)


class IndexedFS(FilesystemBase):
    """
    Estrategia de **asignación indexada (nivel único)**.

    Metadata en self.file_table[name]:
      {
        "size_blocks": int,
        "index_block": int,       # Bloque físico que contiene los punteros
        # "data_blocks" NO se almacena aquí. Se lee del "index_block"
        "overhead_blocks": 1      # 1 bloque para el índice
      }

    Lógica:
    - `create`: Reserva 1 bloque para el índice + N bloques para datos.
                Escribe la lista de punteros a datos en el bloque índice.
    - `_resolve_range`: Lee el bloque índice y devuelve la porción solicitada
                        de la tabla de punteros.
    - `delete`: Libera el bloque índice Y todos los bloques de datos.
    """

    def __init__(
        self,
        disk: DiskLike,
        free_space_manager: FreeSpaceManagerLike,
        *,
        on_event: Optional[Callable[..., None]] = None,
    ) -> None:
        super().__init__(disk, free_space_manager, on_event=on_event)
        # Calculamos cuántos punteros caben en un solo bloque de índice
        self._max_file_blocks = self.disk.block_size // POINTER_SIZE_BYTES

    # ---------------------------------------------------------------------
    # Helpers internos para leer/escribir el bloque índice
    # ---------------------------------------------------------------------

    def _read_index_block(self, index_block_idx: int, size_blocks: int) -> List[int]:
        """
        Lee el bloque índice y decodifica los punteros a bloques de datos.
        """
        data = self.disk.read_block(index_block_idx)
        if data is None:
            raise IOError(f"Corrupción: Bloque índice {index_block_idx} está vacío")

        # Formato: N punteros 'long long' (ej: '!5q')
        format_string = f"!{size_blocks}{POINTER_FORMAT_CHAR}"
        
        try:
            # Desempaca los punteros
            pointers = struct.unpack(format_string, data[:size_blocks * POINTER_SIZE_BYTES])
            return list(pointers)
        except struct.error:
            raise IOError(f"Corrupción: No se pudo decodificar el bloque índice {index_block_idx}")

    def _write_index_block(self, index_block_idx: int, data_blocks: List[int]) -> None:
        """
        Codifica la lista de punteros y la escribe en el bloque índice.
        """
        # Formato: N punteros 'long long' (ej: '!5q')
        format_string = f"!{len(data_blocks)}{POINTER_FORMAT_CHAR}"
        
        try:
            # Empaca la lista de índices (ej: [10, 5, 22]) en bytes
            packed_data = struct.pack(format_string, *data_blocks)
            
            # Rellena el resto del bloque con ceros si es necesario
            if len(packed_data) < self.disk.block_size:
                padding = b"\x00" * (self.disk.block_size - len(packed_data))
                packed_data += padding
            
            self.disk.write_block(index_block_idx, packed_data)
        except struct.error as e:
            raise IOError(f"Error al empaquetar el bloque índice: {e}")

    # ---------------------------------------------------------------------
    # API OBLIGATORIA (Implementación del contrato)
    # ---------------------------------------------------------------------

    def create(self, name: str, size_blocks: int) -> None:
        """
        Crea un archivo con un bloque índice que referencia 'size_blocks' bloques de datos.
        """
        self._assert_new_file(name)
        self._assert_positive_blocks(size_blocks)

        # Validación: ¿Caben N punteros en un solo bloque índice?
        if size_blocks > self._max_file_blocks:
            raise MemoryError(
                f"Archivo demasiado grande ({size_blocks} bloques). "
                f"Solo caben {self._max_file_blocks} punteros en un bloque índice "
                f"de {self.disk.block_size} bytes."
            )

        self._emit("create:start", strategy="indexed", name=name, size_blocks=size_blocks)

        # 1. Reservar N (datos) + 1 (índice) bloques
        total_blocks_needed = size_blocks + 1
        try:
            allocated_indices = self.fsm.allocate(total_blocks_needed, contiguous=False)
        except MemoryError:
            raise MemoryError(f"No hay espacio suficiente para {total_blocks_needed} bloques")

        # 2. Separar el índice de los datos
        index_block_idx = allocated_indices.pop(0)
        data_blocks_indices = allocated_indices
        
        # 3. Registrar metadata en el catálogo (solo el inicio)
        self.file_table[name] = {
            "size_blocks": size_blocks,
            "index_block": index_block_idx,
            "overhead_blocks": 1
        }

        # 4. Escribir la "tabla de punteros" en el bloque índice
        try:
            self._write_index_block(index_block_idx, data_blocks_indices)
        except (IOError, struct.error) as e:
            # Si falla la escritura del índice, revertimos todo
            print(f"Fallo al escribir el índice, revirtiendo creación: {e}")
            self.fsm.free(data_blocks_indices + [index_block_idx])
            del self.file_table[name]
            raise
            
        self._emit(
            "create:done",
            strategy="indexed",
            name=name,
            size_blocks=size_blocks,
            index_block=index_block_idx,
            data_blocks=data_blocks_indices
        )

    def delete(self, name: str) -> None:
        """
        Elimina el archivo 'name', liberando su bloque índice y todos sus bloques de datos.
        """
        self._assert_file_exists(name)
        meta = self.file_table[name]
        
        self._emit("delete:start", strategy="indexed", name=name)

        blocks_to_free = []
        try:
            # 1. Leer el bloque índice para saber qué bloques de datos liberar
            data_blocks = self._read_index_block(meta["index_block"], meta["size_blocks"])
            blocks_to_free.extend(data_blocks)
        except IOError as e:
            # El índice está corrupto, pero al menos liberamos el propio índice
            print(f"Advertencia: Índice de '{name}' corrupto. Se liberará solo el bloque índice. Error: {e}")

        # 2. Agregar el propio bloque índice a la lista de liberación
        blocks_to_free.append(meta["index_block"])

        # 3. Eliminar la metadata del catálogo
        del self.file_table[name]

        # 4. Liberar todos los bloques en el FSM
        try:
            self.fsm.free(blocks_to_free)
        except (ValueError, IndexError) as e:
            print(f"Error al liberar bloques para '{name}': {e}")

        self._emit("delete:done", strategy="indexed", name=name, freed=blocks_to_free)

    def _resolve_range(self, name: str, offset: int, n_blocks: int) -> List[int]:
        """
        Devuelve la lista de índices físicos para [offset, offset+n_blocks),
        leyendo el bloque índice y devolviendo una sub-lista.
        """
        self._assert_file_exists(name)
        meta = self.file_table[name]
        
        # Validación de rango
        self._assert_range_within_size(name, offset, n_blocks)
        
        # 1. Leer el bloque índice (coste de E/S simulado)
        all_data_blocks = self._read_index_block(meta["index_block"], meta["size_blocks"])

        # 2. Devolver la sub-lista (acceso directo)
        return all_data_blocks[offset : offset + n_blocks]

    def read(self, name: str, offset: int, n_blocks: int, access_mode: str = "seq") -> List[bytes]:
        """
        Lee 'n_blocks' desde 'offset' usando el bloque índice.
        """
        self._assert_file_exists(name)
        self._assert_positive_blocks(n_blocks)
        self._assert_non_negative(offset)

        # 1. Resolver el rango (esto ya simula la lectura del bloque índice)
        physical_indices = self._resolve_range(name, offset, n_blocks)
        
        self._emit(
            "read:start",
            strategy="indexed",
            name=name,
            offset=offset,
            n_blocks=n_blocks,
            physical=physical_indices,
            access_mode=access_mode
        )

        # 2. Leer los bloques de datos
        payloads = []
        for block_idx in physical_indices:
            data = self.disk.read_block(block_idx)
            # Devolvemos None o b"" si el bloque está vacío
            payloads.append(b"" if data is None else data)

        self._emit("read:done", strategy="indexed", name=name)
        return payloads

    def write(self, name: str, offset: int, n_blocks: int, data: Iterable[bytes] | None = None) -> None:
        """
        Escribe 'n_blocks' desde 'offset' consultando el índice.
        """
        self._assert_file_exists(name)
        self._assert_positive_blocks(n_blocks)
        self._assert_non_negative(offset)

        # 1. Resolver el rango (simula lectura de índice)
        physical_indices = self._resolve_range(name, offset, n_blocks)
        
        # 2. Preparar los datos
        data_list: List[bytes | None]
        if data is None:
            # Si no se proveen datos, simulamos escritura con bytes vacíos
            data_list = [b""] * n_blocks
        else:
            data_list = list(data)
            if len(data_list) != n_blocks:
                raise ValueError(f"Se esperaban {n_blocks} bloques, se recibieron {len(data_list)}")

        self._emit(
            "write:start",
            strategy="indexed",
            name=name,
            offset=offset,
            n_blocks=n_blocks,
            physical=physical_indices
        )

        # 3. Escribir en los bloques de datos
        for i in range(n_blocks):
            block_idx = physical_indices[i]
            payload = data_list[i]
            # La validación de tamaño (payload <= block_size)
            # la hace self.disk.write_block()
            self.disk.write_block(block_idx, payload)

        self._emit("write:done", strategy="indexed", name=name)
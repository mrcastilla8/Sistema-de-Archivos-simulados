# Owner: Dev 3
from __future__ import annotations
from typing import Iterable, List, Any, Dict
from ..core.filesystem_base import FilesystemBase

class ContiguousFS(FilesystemBase):
    """
    Estrategia de **asignación contigua**.

    Metadata esperada en self.file_table[name]:
      {
        "size_blocks": int,
        # Campos específicos de contigua:
        # "start": int,        # primer bloque físico
        # "length": int        # == size_blocks (si tamaño fijo)
        # (Opcional) "overhead_blocks": 0
      }

    Convenciones del proyecto:
      - Tamaño lógico fijo (no crecer en write).
      - El bloque físico para el lógico k es: start + k.
    """

    def create(self, name: str, size_blocks: int) -> None:
        """
        Crea un archivo y reserva un rango **contiguo** de 'size_blocks' bloques.

        Precondiciones:
          - name no existe.
          - size_blocks > 0.
          - Debe existir espacio contiguo suficiente.

        Efectos (cuando se implemente):
          - Solicitar a self.fsm.allocate(size_blocks, contiguous=True) -> [start..start+size-1]
          - Registrar en self.file_table[name] = {"size_blocks": size_blocks, "start": start, "length": size_blocks}
          - (Opcional) Inicializar bloques en disk (None o bytes vacíos).

        Postcondiciones:
          - Entrada consistente en file_table.
          - Bloques ocupados en fsm.
        """
        # Checks previos (no modificar estado real aquí)
        self._assert_new_file(name)
        self._assert_positive_blocks(size_blocks)

        # Hook de evento (antes)
        self._emit("create:start", strategy="contiguous", name=name, size_blocks=size_blocks)

        # TODO: implementar reserva contigua + registro en file_table.
        raise NotImplementedError("ContiguousFS.create no implementado")

        # Hook de evento (después) — mover a implementación real
        # self._emit("create:done", strategy="contiguous", name=name, size_blocks=size_blocks, start=start)

    def delete(self, name: str) -> None:
        """
        Elimina el archivo 'name' liberando su rango contiguo.

        Precondiciones:
          - name existe.

        Efectos (cuando se implemente):
          - Recuperar {"start","length"} de file_table[name].
          - Construir lista de bloques físicos del rango y llamar self.fsm.free(...).
          - Eliminar file_table[name].
        """
        self._assert_file_exists(name)

        self._emit("delete:start", strategy="contiguous", name=name)

        # TODO: implementar liberación del rango y borrado de metadata.
        raise NotImplementedError("ContiguousFS.delete no implementado")

        # self._emit("delete:done", strategy="contiguous", name=name)

    def read(self, name: str, offset: int, n_blocks: int, access_mode: str = "seq") -> List[bytes]:
        """
        Lee 'n_blocks' desde 'offset' aplicando mapeo contiguo.

        Precondiciones:
          - name existe.
          - offset >= 0, n_blocks > 0.
          - offset + n_blocks <= size_blocks.

        Efectos (cuando se implemente):
          - Resolver rango físico (start + k).
          - Llamar disk.read_block(i) por cada físico.
          - (Opcional) estimar seeks (saltos si no consecutivos, aquí suelen ser 0).
        """
        self._assert_file_exists(name)
        self._assert_non_negative(offset)
        self._assert_positive_blocks(n_blocks)
        self._assert_range_within_size(name, offset, n_blocks)

        phys = self._resolve_range(name, offset, n_blocks)
        self._emit("read:start", strategy="contiguous", name=name, offset=offset, n_blocks=n_blocks, physical=phys)

        # TODO: implementar lecturas reales desde disk y devolver lista de bytes.
        raise NotImplementedError("ContiguousFS.read no implementado")

        # self._emit("read:done", strategy="contiguous", name=name, offset=offset, n_blocks=n_blocks, physical=phys)

    def write(self, name: str, offset: int, n_blocks: int, data: Iterable[bytes] | None = None) -> None:
        """
        Escribe 'n_blocks' desde 'offset' en mapeo contiguo (tamaño fijo).

        Precondiciones:
          - name existe.
          - offset >= 0, n_blocks > 0.
          - offset + n_blocks <= size_blocks.
          - Si 'data' no es None, debe proveer 'n_blocks' elementos de tamaño <= block_size.
        """
        self._assert_file_exists(name)
        self._assert_non_negative(offset)
        self._assert_positive_blocks(n_blocks)
        self._assert_range_within_size(name, offset, n_blocks)

        phys = self._resolve_range(name, offset, n_blocks)
        self._emit("write:start", strategy="contiguous", name=name, offset=offset, n_blocks=n_blocks, physical=phys)

        # TODO: escribir en disk.write_block(...) por cada bloque físico.
        raise NotImplementedError("ContiguousFS.write no implementado")

        # self._emit("write:done", strategy="contiguous", name=name, offset=offset, n_blocks=n_blocks, physical=phys)

    def _resolve_range(self, name: str, offset: int, n_blocks: int) -> List[int]:
        """
        Devuelve la lista de índices físicos para los bloques lógicos [offset, offset+n_blocks).

        Precondiciones:
          - name existe.
          - offset >= 0, n_blocks > 0.
          - offset + n_blocks <= size_blocks.

        Nota: **no** realiza E/S. Solo mapeo lógico→físico.
        """
        self._assert_file_exists(name)
        self._assert_non_negative(offset)
        self._assert_positive_blocks(n_blocks)
        self._assert_range_within_size(name, offset, n_blocks)

        # TODO: calcular [start + offset, ..., start + offset + n_blocks - 1] a partir de metadata.
        raise NotImplementedError("ContiguousFS._resolve_range no implementado")

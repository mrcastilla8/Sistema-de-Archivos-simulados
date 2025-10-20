# Owner: Axel Cueva
from __future__ import annotations
from typing import Iterable, List, Any, Dict
from ..core.filesystem_base import FilesystemBase


class ContiguousFS(FilesystemBase):
    """
    Estrategia de **asignación contigua**.

    Metadata esperada en self.file_table[name]:
      {
        "size_blocks": int,
        "start": int,        # primer bloque físico
        "length": int,       # == size_blocks (si tamaño fijo)
        (Opcional) "overhead_blocks": 0
      }
    """

    # ------------------------------------------------------------------
    # Creación
    # ------------------------------------------------------------------
    def create(self, name: str, size_blocks: int) -> None:
        self._assert_new_file(name)
        self._assert_positive_blocks(size_blocks)

        self._emit("create:start", strategy="contiguous", name=name, size_blocks=size_blocks)

        # Reserva de espacio contiguo usando el FreeSpaceManager
        try:
            indices = self.fsm.allocate(size_blocks, contiguous=True)
        except MemoryError:
            raise MemoryError(f"No hay espacio contiguo suficiente para '{name}'")

        start = indices[0]

        # Registrar metadata
        self.file_table[name] = {
            "size_blocks": size_blocks,
            "start": start,
            "length": size_blocks,
            "overhead_blocks": 0,
        }

        # Inicializar bloques (opcional: dejar como None o ceros)
        for i in indices:
            self.disk.write_block(i, None)

        self._emit(
            "create:done",
            strategy="contiguous",
            name=name,
            size_blocks=size_blocks,
            start=start,
            physical_blocks=indices,
        )

    # ------------------------------------------------------------------
    # Eliminación
    # ------------------------------------------------------------------
    def delete(self, name: str) -> None:
        self._assert_file_exists(name)
        self._emit("delete:start", strategy="contiguous", name=name)

        meta = self.file_table[name]
        start, length = meta["start"], meta["length"]
        indices = list(range(start, start + length))

        # Liberar bloques en el gestor de espacio libre
        self.fsm.free(indices)

        # Eliminar metadata del archivo
        del self.file_table[name]

        self._emit("delete:done", strategy="contiguous", name=name, released=indices)

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    def read(self, name: str, offset: int, n_blocks: int, access_mode: str = "seq") -> List[bytes]:
        self._assert_file_exists(name)
        self._assert_non_negative(offset)
        self._assert_positive_blocks(n_blocks)
        self._assert_range_within_size(name, offset, n_blocks)

        phys = self._resolve_range(name, offset, n_blocks)
        self._emit(
            "read:start",
            strategy="contiguous",
            name=name,
            offset=offset,
            n_blocks=n_blocks,
            physical=phys,
        )

        # Lectura de bloques físicos
        data = [self.disk.read_block(i) or b"" for i in phys]

        self._emit(
            "read:done",
            strategy="contiguous",
            name=name,
            offset=offset,
            n_blocks=n_blocks,
            physical=phys,
        )
        return data

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------
    def write(self, name: str, offset: int, n_blocks: int, data: Iterable[bytes] | None = None) -> None:
        self._assert_file_exists(name)
        self._assert_non_negative(offset)
        self._assert_positive_blocks(n_blocks)
        self._assert_range_within_size(name, offset, n_blocks)

        phys = self._resolve_range(name, offset, n_blocks)
        self._emit(
            "write:start",
            strategy="contiguous",
            name=name,
            offset=offset,
            n_blocks=n_blocks,
            physical=phys,
        )

        payloads: List[bytes | None]
        if data is None:
            payloads = [b"" for _ in range(n_blocks)]
        else:
            payloads = list(data)
            if len(payloads) != n_blocks:
                raise ValueError("La cantidad de datos no coincide con n_blocks")

        # Escritura física
        self.disk.write_blocks(phys, payloads)

        self._emit(
            "write:done",
            strategy="contiguous",
            name=name,
            offset=offset,
            n_blocks=n_blocks,
            physical=phys,
        )

    # ------------------------------------------------------------------
    # Mapeo lógico→físico
    # ------------------------------------------------------------------
    def _resolve_range(self, name: str, offset: int, n_blocks: int) -> List[int]:
        self._assert_file_exists(name)
        self._assert_non_negative(offset)
        self._assert_positive_blocks(n_blocks)
        self._assert_range_within_size(name, offset, n_blocks)

        meta = self.file_table[name]
        start = meta["start"]
        return [start + i for i in range(offset, offset + n_blocks)]

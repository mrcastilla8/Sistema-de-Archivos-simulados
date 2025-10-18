# Owner: Dev 5
from __future__ import annotations
from typing import Iterable, List
from ..core.filesystem_base import FilesystemBase

class IndexedFS(FilesystemBase):
    """
    Stub de asignación indexada.
    TODO: Implementar create/delete/read/write con bloque índice.
    """
    def create(self, name: str, size_blocks: int) -> None:
        raise NotImplementedError("IndexedFS.create no implementado")

    def delete(self, name: str) -> None:
        raise NotImplementedError("IndexedFS.delete no implementado")

    def read(self, name: str, offset: int, n_blocks: int, access_mode: str = "seq") -> List[bytes]:
        raise NotImplementedError("IndexedFS.read no implementado")

    def write(self, name: str, offset: int, n_blocks: int, data: Iterable[bytes] | None = None) -> None:
        raise NotImplementedError("IndexedFS.write no implementado")

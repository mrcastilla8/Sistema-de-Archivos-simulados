# Owner: Dev 3
from __future__ import annotations
from typing import Iterable, List
from ..core.filesystem_base import FilesystemBase

class ContiguousFS(FilesystemBase):
    """
    Stub de asignación contigua.
    TODO: Implementar create/delete/read/write con bloques contiguos.
    """
    def create(self, name: str, size_blocks: int) -> None:
        raise NotImplementedError("ContiguousFS.create no implementado")

    def delete(self, name: str) -> None:
        raise NotImplementedError("ContiguousFS.delete no implementado")

    def read(self, name: str, offset: int, n_blocks: int, access_mode: str = "seq") -> List[bytes]:
        raise NotImplementedError("ContiguousFS.read no implementado")

    def write(self, name: str, offset: int, n_blocks: int, data: Iterable[bytes] | None = None) -> None:
        raise NotImplementedError("ContiguousFS.write no implementado")

# Owner: Dev 1
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable, List

class FilesystemBase(ABC):
    """
    Contrato base para las políticas de asignación.
    Las unidades de tamaño y offset son en bloques lógicos.
    """
    def __init__(self, disk, free_space_manager):
        self.disk = disk
        self.fsm = free_space_manager
        self.file_table = {}  # name -> metadata específica de estrategia

    @abstractmethod
    def create(self, name: str, size_blocks: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self, name: str, offset: int, n_blocks: int, access_mode: str = "seq") -> List[bytes]:
        raise NotImplementedError

    @abstractmethod
    def write(self, name: str, offset: int, n_blocks: int, data: Iterable[bytes] | None = None) -> None:
        raise NotImplementedError

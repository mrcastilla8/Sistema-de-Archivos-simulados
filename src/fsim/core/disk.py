# Owner: Dev 2
from __future__ import annotations
from typing import List
from .block import Block

class Disk:
    """
    Disco lógico en memoria.
    """
    def __init__(self, n_blocks: int, block_size: int):
        self.n_blocks = n_blocks
        self.block_size = block_size
        self._storage: List[Block] = [Block(i, None) for i in range(n_blocks)]

    def read_block(self, i: int) -> bytes | None:
        self._check(i)
        return self._storage[i].data

    def write_block(self, i: int, data: bytes | None) -> None:
        self._check(i)
        if data is not None and len(data) > self.block_size:
            raise ValueError("Data size exceeds block_size")
        self._storage[i].data = data

    def _check(self, i: int):
        if not (0 <= i < self.n_blocks):
            raise IndexError("Block index out of range")

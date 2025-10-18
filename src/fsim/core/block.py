# Owner: Dev 2
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Block:
    index: int
    data: bytes | None = None

# Owner: Dev 2
from __future__ import annotations
from typing import List

class FreeSpaceManager:
    """
    Gestor de espacio libre usando bitmap simple.
    """
    def __init__(self, n_blocks: int):
        self.n_blocks = n_blocks
        self.bitmap = [0] * n_blocks  # 0 libre, 1 ocupado

    def allocate(self, n: int, contiguous: bool = False) -> List[int]:
        if contiguous:
            # búsqueda lineal del primer hueco contiguo de tamaño n
            run = 0
            start = 0
            for i, bit in enumerate(self.bitmap):
                if bit == 0:
                    if run == 0:
                        start = i
                    run += 1
                    if run == n:
                        idxs = list(range(start, start + n))
                        for j in idxs:
                            self.bitmap[j] = 1
                        return idxs
                else:
                    run = 0
            raise MemoryError("No hay espacio contiguo suficiente")
        else:
            idxs = []
            for i, bit in enumerate(self.bitmap):
                if bit == 0:
                    idxs.append(i)
                    if len(idxs) == n:
                        for j in idxs:
                            self.bitmap[j] = 1
                        return idxs
            raise MemoryError("No hay bloques libres suficientes")

    def free(self, block_list: List[int]) -> None:
        for i in block_list:
            if not (0 <= i < self.n_blocks):
                raise IndexError("Índice de bloque inválido al liberar")
            self.bitmap[i] = 0

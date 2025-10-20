# Owner: Dev 2
from __future__ import annotations
# MODIFICADO: Añadir Callable y List
from typing import Iterable, List, Sequence, Tuple, Optional, Callable 


class FreeSpaceManager:
    """
    Gestor de espacio libre basado en un bitmap.
    ...
    """

    # ---------------------------------------------------------------------
    # Construcción
    # ---------------------------------------------------------------------
    # MODIFICADO: Añadir on_bitmap_update al constructor
    def __init__(
        self, 
        n_blocks: int, 
        *, 
        preoccupied: Optional[Sequence[int]] = None,
        on_bitmap_update: Optional[Callable[[List[int]], None]] = None
    ) -> None:
    # --- FIN MODIFICACIÓN ---
        if n_blocks <= 0:
            raise ValueError("n_blocks debe ser > 0")
        self.n_blocks: int = int(n_blocks)
        self.bitmap: List[int] = [0] * self.n_blocks  # 0 libre, 1 ocupado
        
        # MODIFICADO: Guardar el callback
        self.on_bitmap_update = on_bitmap_update
        # --- FIN MODIFICACIÓN ---

        if preoccupied:
            self._check_indices(preoccupied)
            for i in preoccupied:
                self._set_used(i)

    # ---------------------------------------------------------------------
    # API de contrato
    # ---------------------------------------------------------------------
    def allocate(self, n: int, contiguous: bool = False) -> List[int]:
        """
        Reserva 'n' bloques y devuelve sus índices físicos.
        ...
        """
        if n <= 0:
            raise ValueError("n debe ser > 0")

        indices: List[int] = [] # MODIFICADO: Mover la declaración aquí
        
        if contiguous:
            run = self._find_first_fit_run(n)
            if run is None:
                raise MemoryError("No hay espacio contiguo suficiente")
            start, length = run
            indices = list(range(start, start + n))
            for i in indices:
                self._set_used(i)
        else:
            # No contiguo: tomamos los primeros 'n' libres
            for i, bit in enumerate(self.bitmap):
                if bit == 0:
                    indices.append(i)
                    if len(indices) == n:
                        break
            if len(indices) < n:
                raise MemoryError("No hay bloques libres suficientes")
            for i in indices:
                self._set_used(i)
        
        # MODIFICADO: Llamar al callback si existe
        if self.on_bitmap_update:
            self.on_bitmap_update(self.bitmap)
        # --- FIN MODIFICACIÓN ---
            
        return indices

    def free(self, block_list: List[int]) -> None:
        """
        Libera todos los bloques en 'block_list'.
        ...
        """
        if not block_list:
            return
        self._check_indices(block_list)

        if len(set(block_list)) != len(block_list):
            raise ValueError("La lista de bloques a liberar contiene duplicados")

        for i in block_list:
            if self.bitmap[i] == 0:
                raise ValueError(f"El bloque {i} ya está libre (posible doble liberación)")

        for i in block_list:
            self._set_free(i)

        # MODIFICADO: Llamar al callback si existe
        if self.on_bitmap_update:
            self.on_bitmap_update(self.bitmap)
        # --- FIN MODIFICACIÓN ---

    # ... (El resto del archivo free_space.py sigue igual) ...
    # ---------------------------------------------------------------------
    # Helpers de asignación (internos)
    # ---------------------------------------------------------------------
    def _find_first_fit_run(self, needed: int) -> Optional[Tuple[int, int]]:
        """
        Devuelve (start, length) del primer run contiguo libre con length >= needed,
        o None si no existe.
        """
        run_len = 0
        run_start = 0
        for i, bit in enumerate(self.bitmap):
            if bit == 0:
                if run_len == 0:
                    run_start = i
                run_len += 1
                if run_len >= needed:
                    return (run_start, run_len)
            else:
                run_len = 0
        return None

    def _set_used(self, i: int) -> None:
        self.bitmap[i] = 1

    def _set_free(self, i: int) -> None:
        self.bitmap[i] = 0

    # ---------------------------------------------------------------------
    # Validaciones
    # ---------------------------------------------------------------------
    def _check_index(self, i: int) -> None:
        if not isinstance(i, int):
            raise TypeError("El índice debe ser int")
        if i < 0 or i >= self.n_blocks:
            raise IndexError(f"Índice fuera de rango: {i} (0..{self.n_blocks-1})")

    def _check_indices(self, idxs: Sequence[int]) -> None:
        for i in idxs:
            self._check_index(i)

    # ---------------------------------------------------------------------
    # Métricas e introspección (opcionales para runner/UI)
    # ---------------------------------------------------------------------
    def used_count(self) -> int:
        """Bloques ocupados (bitmap=1)."""
        return sum(self.bitmap)

    def free_count(self) -> int:
        """Bloques libres (bitmap=0)."""
        return self.n_blocks - self.used_count()

    def occupancy_pct(self) -> float:
        """Porcentaje de ocupación física (0..100)."""
        if self.n_blocks == 0:
            return 0.0
        return 100.0 * (self.used_count() / self.n_blocks)

    def free_runs(self) -> List[Tuple[int, int]]:
        """
        Lista de runs libres [(start, length), ...], en orden de aparición.
        Útil para visualizar fragmentación externa.
        """
        runs: List[Tuple[int, int]] = []
        run_len = 0
        run_start = 0
        for i, bit in enumerate(self.bitmap):
            if bit == 0:
                if run_len == 0:
                    run_start = i
                run_len += 1
            else:
                if run_len > 0:
                    runs.append((run_start, run_len))
                run_len = 0
        if run_len > 0:
            runs.append((run_start, run_len))
        return runs

    def largest_free_run_size(self) -> int:
        """Tamaño del mayor hueco contiguo libre."""
        runs = self.free_runs()
        return 0 if not runs else max(length for _, length in runs)

    def external_fragmentation_ratio(self) -> float:
        """
        Heurística común de fragmentación externa:
          - Si no hay bloques libres → 0.0
          - Si hay libres → 1 - (largest_free_run / total_free)
            (cuanto más cerca de 1.0, más fragmentado está el espacio libre)
        """
        total_free = self.free_count()
        if total_free == 0:
            return 0.0
        largest = self.largest_free_run_size()
        return 1.0 - (largest / total_free)

    def snapshot_bitmap(self) -> List[int]:
        """Copia superficial del bitmap (para inspección/serialización)."""
        return list(self.bitmap)

    # ---------------------------------------------------------------------
    # Utilidades opcionales (no parte del contrato)
    # ---------------------------------------------------------------------
    def reserve_exact(self, indices: Sequence[int]) -> None:
        """
        Marca como usados los índices indicados (útil cuando la estrategia
        ya decidió qué bloques usar). Falla si alguno ya estaba ocupado.
        """
        self._check_indices(indices)
        # validación previa
        for i in indices:
            if self.bitmap[i] == 1:
                raise ValueError(f"El bloque {i} ya está ocupado")
        for i in indices:
            self._set_used(i)
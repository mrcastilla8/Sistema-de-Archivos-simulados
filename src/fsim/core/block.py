# Owner: Dev 2
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

_ZERO = b"\x00"  # Útil para rellenar con ceros si se desea


@dataclass
class Block:
    """
    Modelo de bloque lógico del 'disco' en memoria.

    Diseño:
      - Un bloque tiene un índice inmutable 'index' (posición en el disco).
      - 'data' es opcional: None significa "sin datos escritos".
        También puede ser 'b""' (vacío) si quieres distinguir "escrito con vacío".
      - No conoce el tamaño máximo del bloque por sí mismo; eso lo controla Disk.
        (Disk ya valida que len(data) <= block_size en write_block()).

    ¿Por qué este nivel?
      - Mantener el estado por-bloque (datos + utilidades de conveniencia)
        sin acoplarse a Disk ni a la política de asignación.
      - Permitir inspección y operaciones sencillas en la UI (p. ej. mostrar
        si un bloque está vacío, ver bytes escritos, etc.).
    """
    index: int
    data: Optional[bytes] = field(default=None, repr=False)

    # ----------------------------------------------------------------------
    # Propiedades de conveniencia
    # ----------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        """
        Indica si no hay datos almacenados (None o cadena vacía).
        - En esta simulación, None se usa comúnmente como "nunca escrito".
        - b"" podría entenderse como "escrito, pero vacío".
        """
        return self.data is None or len(self.data) == 0

    @property
    def size_bytes(self) -> int:
        """
        Tamaño actual del payload en bytes (0 si no hay datos).
        """
        return 0 if self.data is None else len(self.data)

    # ----------------------------------------------------------------------
    # Mutadores seguros (opcionales). 'Disk' no los necesita para funcionar,
    # pero son útiles si quieres trabajar con bloques desde otras capas.
    # ----------------------------------------------------------------------

    def clear(self) -> None:
        """
        Elimina el contenido del bloque (equivalente semántico a 'no escrito').
        No lanza excepción.
        """
        self.data = None

    def set_bytes(self, payload: Optional[bytes]) -> None:
        """
        Establece los bytes exactamente como llegan (sin validar tamaño).
        ¡OJO! La validación de tamaño debe hacerla la capa 'Disk'.
        Se ofrece para casos de uso fuera de Disk (e.g., UI o instrumentos).
        """
        if payload is not None and not isinstance(payload, (bytes, bytearray, memoryview)):
            raise TypeError("payload debe ser bytes-like o None")
        # Convertimos bytearray/memoryview a bytes para mantener inmutabilidad semántica
        self.data = None if payload is None else bytes(payload)

    def fill_zeros(self, block_size: int) -> None:
        """
        Rellena el bloque con 'block_size' bytes a cero (útil para demos/visual).
        No valida contra 'Disk'; se asume que 'block_size' es correcto.
        """
        if block_size < 0:
            raise ValueError("block_size debe ser >= 0")
        self.data = _ZERO * block_size

    def write_partial(
        self,
        payload: bytes,
        *,
        block_size: int | None = None,
        pad_with_zeros: bool = False,
    ) -> None:
        """
        Escribe un payload parcial:
          - Si 'block_size' es None: no se valida longitud (igual que set_bytes()).
          - Si 'block_size' se especifica:
              * Si len(payload) > block_size: ValueError.
              * Si 'pad_with_zeros' es True y len(payload) < block_size:
                    se rellena a la derecha con ceros hasta 'block_size'.
              * Si 'pad_with_zeros' es False: se guarda tal cual.

        Útil cuando quieras simular que el bloque físico tiene tamaño fijo
        pero el contenido escrito puede ser menor (fragmentación interna visible).
        """
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise TypeError("payload debe ser bytes-like")

        raw = bytes(payload)

        if block_size is not None:
            if block_size < 0:
                raise ValueError("block_size debe ser >= 0")
            if len(raw) > block_size:
                raise ValueError(
                    f"payload ({len(raw)} B) excede block_size ({block_size} B)"
                )
            if pad_with_zeros and len(raw) < block_size:
                raw = raw + (_ZERO * (block_size - len(raw)))

        self.data = raw

    # ----------------------------------------------------------------------
    # Representación / depuración
    # ----------------------------------------------------------------------

    def __repr__(self) -> str:
        """
        Representación compacta para logs.
        Mostrar solo un prefijo de los datos para no saturar la consola.
        """
        preview_len = 8
        if self.data is None:
            d = "None"
        else:
            # Mostramos primeros bytes en hex para inspección rápida
            prefix = self.data[:preview_len].hex()
            more = "" if len(self.data) <= preview_len else "…"
            d = f"{len(self.data)}B:{prefix}{more}"
        return f"Block(index={self.index}, data={d})"

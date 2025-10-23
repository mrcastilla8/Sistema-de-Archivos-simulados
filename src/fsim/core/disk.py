
from __future__ import annotations 
from typing import Iterable ,List ,Optional ,Sequence 

from .block import Block 


class Disk :
    """
    Disco lógico en memoria.

    Propiedades públicas (contrato DiskLike):
      - n_blocks: int         → cantidad de bloques físicos
      - block_size: int       → tamaño en bytes de cada bloque
      - read_block(i)         → bytes | None
      - write_block(i, data)  → None

    Semántica:
      - Un bloque puede estar en estado "no escrito" representado por `None`.
      - Si se escribe `b""` se considera "escrito pero vacío".
      - La validación de longitud de `data` se hace acá (len(data) <= block_size).
      - No simula latencias ni fallos; eso puede hacerse en capas superiores si se desea.
    """




    def __init__ (
    self ,
    n_blocks :int ,
    block_size :int ,
    *,
    prefill :Optional [str ]=None ,
    )->None :
        """
        Crea un disco lógico con `n_blocks` bloques de tamaño `block_size` bytes.

        Args:
            n_blocks: cantidad de bloques físicos (>= 1)
            block_size: tamaño máximo en bytes por bloque (>= 1)
            prefill:
                - None (default): todos los bloques quedan como "no escritos" (data=None).
                - "zeros": inicializa cada bloque con bytes nulos de longitud `block_size`.
        """
        if n_blocks <=0 :
            raise ValueError ("n_blocks debe ser > 0")
        if block_size <=0 :
            raise ValueError ("block_size debe ser > 0")

        self .n_blocks :int =int (n_blocks )
        self .block_size :int =int (block_size )

        self ._storage :List [Block ]=[Block (i ,None )for i in range (self .n_blocks )]

        if prefill is not None :
            if prefill =="zeros":
                for b in self ._storage :
                    b .fill_zeros (self .block_size )
            else :
                raise ValueError ("prefill inválido. Usa None o 'zeros'.")




    def read_block (self ,i :int )->bytes |None :
        """
        Devuelve los bytes del bloque `i` o None si nunca se escribió.
        Errores:
          - IndexError si `i` está fuera de rango.
        """
        self ._check_index (i )
        return self ._storage [i ].data 

    def write_block (self ,i :int ,data :bytes |None )->None :
        """
        Escribe `data` en el bloque `i`.
        Reglas:
          - Si data es None → el bloque queda como "no escrito".
          - Si data tiene más bytes que `block_size` → ValueError.
          - Acepta bytes-like (bytes/bytearray/memoryview).

        Errores:
          - IndexError si `i` está fuera de rango.
          - TypeError si `data` no es bytes-like ni None.
          - ValueError si len(data) > block_size.
        """
        self ._check_index (i )
        if data is None :
            self ._storage [i ].clear ()
            return 

        if not isinstance (data ,(bytes ,bytearray ,memoryview )):
            raise TypeError ("data debe ser bytes-like o None")


        b =bytes (data )
        if len (b )>self .block_size :
            raise ValueError (
            f"Tamaño de data ({len (b )}) excede block_size ({self .block_size })"
            )

        self ._storage [i ].set_bytes (b )




    def clear_block (self ,i :int )->None :
        """Deja el bloque `i` como 'no escrito' (data=None)."""
        self ._check_index (i )
        self ._storage [i ].clear ()

    def fill_block_zeros (self ,i :int )->None :
        """Rellena el bloque `i` con ceros (longitud = block_size)."""
        self ._check_index (i )
        self ._storage [i ].fill_zeros (self .block_size )

    def read_blocks (self ,indices :Sequence [int ])->List [bytes |None ]:
        """
        Lee múltiples bloques y devuelve una lista con sus contenidos.
        Lanza IndexError si algún índice está fuera de rango.
        """
        self ._check_indices (indices )
        return [self ._storage [i ].data for i in indices ]

    def write_blocks (self ,indices :Sequence [int ],payloads :Iterable [Optional [bytes ]])->None :
        """
        Escribe múltiples bloques.
        `indices` y `payloads` deben tener la misma longitud.
        Valida tamaño de cada payload antes de escribir.

        Errores:
          - ValueError si longitudes no coinciden o payload excede block_size.
          - IndexError si algún índice está fuera de rango.
          - TypeError si algún payload no es bytes-like ni None.
        """
        self ._check_indices (indices )
        payloads_list =list (payloads )
        if len (indices )!=len (payloads_list ):
            raise ValueError ("indices y payloads deben tener la misma longitud")


        for p in payloads_list :
            if p is None :
                continue 
            if not isinstance (p ,(bytes ,bytearray ,memoryview )):
                raise TypeError ("cada payload debe ser bytes-like o None")
            if len (p )>self .block_size :
                raise ValueError (
                f"payload excede block_size ({len (p )} > {self .block_size })"
                )


        for i ,p in zip (indices ,payloads_list ):
            self .write_block (i ,p )

    def used_blocks_count (self )->int :
        """
        Cuenta cuántos bloques tienen 'data' no None (es decir, fueron escritos).
        Útil para métricas de utilización física.
        """
        return sum (1 for b in self ._storage if b .data is not None )

    def empty_blocks_count (self )->int :
        """Bloques en estado 'no escrito' (data is None)."""
        return self .n_blocks -self .used_blocks_count ()

    def iter_blocks (self )->Iterable [Block ]:
        """
        Iterador sobre los bloques físicos (útil para visualización en UI).
        No retornar una copia para evitar overhead innecesario; manipular con cuidado.
        """
        return iter (self ._storage )

    def __len__ (self )->int :
        """Permite usar len(disk) == n_blocks."""
        return self .n_blocks 




    def _check_index (self ,i :int )->None :
        if not isinstance (i ,int ):
            raise TypeError ("El índice de bloque debe ser int")
        if i <0 or i >=self .n_blocks :
            raise IndexError (f"Índice fuera de rango: {i } (0..{self .n_blocks -1 })")

    def _check_indices (self ,idxs :Sequence [int ])->None :
        for i in idxs :
            self ._check_index (i )

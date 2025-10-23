
from __future__ import annotations 
from typing import Iterable ,List ,Optional ,Sequence 

from .block import Block 


class Disk :





    def __init__ (
    self ,
    n_blocks :int ,
    block_size :int ,
    *,
    prefill :Optional [str ]=None ,
    )->None :

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

        self ._check_index (i )
        return self ._storage [i ].data 

    def write_block (self ,i :int ,data :bytes |None )->None :

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

        self ._check_index (i )
        self ._storage [i ].clear ()

    def fill_block_zeros (self ,i :int )->None :

        self ._check_index (i )
        self ._storage [i ].fill_zeros (self .block_size )

    def read_blocks (self ,indices :Sequence [int ])->List [bytes |None ]:

        self ._check_indices (indices )
        return [self ._storage [i ].data for i in indices ]

    def write_blocks (self ,indices :Sequence [int ],payloads :Iterable [Optional [bytes ]])->None :

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

        return sum (1 for b in self ._storage if b .data is not None )

    def empty_blocks_count (self )->int :

        return self .n_blocks -self .used_blocks_count ()

    def iter_blocks (self )->Iterable [Block ]:

        return iter (self ._storage )

    def __len__ (self )->int :

        return self .n_blocks 




    def _check_index (self ,i :int )->None :
        if not isinstance (i ,int ):
            raise TypeError ("El índice de bloque debe ser int")
        if i <0 or i >=self .n_blocks :
            raise IndexError (f"Índice fuera de rango: {i } (0..{self .n_blocks -1 })")

    def _check_indices (self ,idxs :Sequence [int ])->None :
        for i in idxs :
            self ._check_index (i )

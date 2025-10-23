
from __future__ import annotations 
from dataclasses import dataclass ,field 
from typing import Optional 

_ZERO =b"\x00"


@dataclass 
class Block :

    index :int 
    data :Optional [bytes ]=field (default =None ,repr =False )





    @property 
    def is_empty (self )->bool :

        return self .data is None or len (self .data )==0 

    @property 
    def size_bytes (self )->int :

        return 0 if self .data is None else len (self .data )






    def clear (self )->None :

        self .data =None 

    def set_bytes (self ,payload :Optional [bytes ])->None :

        if payload is not None and not isinstance (payload ,(bytes ,bytearray ,memoryview )):
            raise TypeError ("payload debe ser bytes-like o None")

        self .data =None if payload is None else bytes (payload )

    def fill_zeros (self ,block_size :int )->None :

        if block_size <0 :
            raise ValueError ("block_size debe ser >= 0")
        self .data =_ZERO *block_size 

    def write_partial (
    self ,
    payload :bytes ,
    *,
    block_size :int |None =None ,
    pad_with_zeros :bool =False ,
    )->None :

        if not isinstance (payload ,(bytes ,bytearray ,memoryview )):
            raise TypeError ("payload debe ser bytes-like")

        raw =bytes (payload )

        if block_size is not None :
            if block_size <0 :
                raise ValueError ("block_size debe ser >= 0")
            if len (raw )>block_size :
                raise ValueError (
                f"payload ({len (raw )} B) excede block_size ({block_size } B)"
                )
            if pad_with_zeros and len (raw )<block_size :
                raw =raw +(_ZERO *(block_size -len (raw )))

        self .data =raw 





    def __repr__ (self )->str :

        preview_len =8 
        if self .data is None :
            d ="None"
        else :

            prefix =self .data [:preview_len ].hex ()
            more =""if len (self .data )<=preview_len else "…"
            d =f"{len (self .data )}B:{prefix }{more }"
        return f"Block(index={self .index }, data={d })"

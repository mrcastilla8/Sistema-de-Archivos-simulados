from __future__ import annotations 

from abc import ABC ,abstractmethod 
from typing import (
Any ,
Callable ,
Dict ,
Iterable ,
List ,
Optional ,
Protocol ,
Tuple ,
runtime_checkable ,
)






@runtime_checkable 
class DiskLike (Protocol ):

    n_blocks :int 
    block_size :int 

    def read_block (self ,i :int )->bytes |None :...
    def write_block (self ,i :int ,data :bytes |None )->None :...


@runtime_checkable 
class FreeSpaceManagerLike (Protocol ):

    n_blocks :int 

    def allocate (self ,n :int ,contiguous :bool =False )->List [int ]:...
    def free (self ,block_list :List [int ])->None :...






class FilesystemBase (ABC ):






    def __init__ (
    self ,
    disk :DiskLike ,
    free_space_manager :FreeSpaceManagerLike ,
    *,
    on_event :Optional [Callable [[str ],None ]]|Optional [Callable [[str ,Any ],None ]]=None ,
    )->None :

        if not isinstance (disk ,DiskLike .__constraints__ if hasattr (DiskLike ,"__constraints__")else DiskLike ):

            pass 
        if not hasattr (disk ,"n_blocks")or not hasattr (disk ,"block_size"):
            raise TypeError ("disk debe exponer 'n_blocks' y 'block_size'")
        if not hasattr (free_space_manager ,"allocate")or not hasattr (free_space_manager ,"free"):
            raise TypeError ("free_space_manager debe exponer 'allocate' y 'free'")

        self .disk :DiskLike =disk 
        self .fsm :FreeSpaceManagerLike =free_space_manager 
        self .file_table :Dict [str ,Dict [str ,Any ]]={}
        self .on_event :Optional [Callable [...,None ]]=on_event 

    @property 
    def n_blocks (self )->int :
        return self .disk .n_blocks 

    @property 
    def block_size (self )->int :
        return self .disk .block_size 





    @abstractmethod 
    def create (self ,name :str ,size_blocks :int )->None :

        raise NotImplementedError 

    @abstractmethod 
    def delete (self ,name :str )->None :

        raise NotImplementedError 

    @abstractmethod 
    def read (self ,name :str ,offset :int ,n_blocks :int ,access_mode :str ="seq")->List [bytes ]:

        raise NotImplementedError 

    @abstractmethod 
    def write (
    self ,
    name :str ,
    offset :int ,
    n_blocks :int ,
    data :Iterable [bytes ]|None =None ,
    )->None :

        raise NotImplementedError 





    @abstractmethod 
    def _resolve_range (self ,name :str ,offset :int ,n_blocks :int )->List [int ]:

        raise NotImplementedError 



    def _assert_new_file (self ,name :str )->None :
        if name in self .file_table :
            raise FileExistsError (f"El archivo '{name }' ya existe")

    def _assert_file_exists (self ,name :str )->None :
        if name not in self .file_table :
            raise FileNotFoundError (f"El archivo '{name }' no existe")

    def _assert_positive_blocks (self ,n_blocks :int )->None :
        if n_blocks <=0 :
            raise ValueError ("n_blocks debe ser > 0")

    def _assert_non_negative (self ,offset :int )->None :
        if offset <0 :
            raise ValueError ("offset debe ser >= 0")

    def _assert_range_within_size (self ,name :str ,offset :int ,n_blocks :int )->None :
        size =int (self .file_table [name ].get ("size_blocks",0 ))
        if offset +n_blocks >size :
            raise ValueError (
            f"Rango inválido: offset({offset }) + n_blocks({n_blocks }) > size_blocks({size })"
            )



    def list_files (self )->List [Tuple [str ,int ]]:

        return [(k ,int (v .get ("size_blocks",0 )))for k ,v in self .file_table .items ()]

    def get_file_info (self ,name :str )->Dict [str ,Any ]:

        self ._assert_file_exists (name )

        return dict (self .file_table [name ])

    def space_usage_summary (self )->Dict [str ,int ]:

        used =0 



        for meta in self .file_table .values ():
            used +=int (meta .get ("size_blocks",0 ))
            used +=int (meta .get ("overhead_blocks",0 ))
        return {
        "total_blocks":self .n_blocks ,
        "used_blocks":used ,
        "free_blocks":max (0 ,self .n_blocks -used ),
        }



    def _emit (self ,event_type :str ,**payload :Any )->None :

        if self .on_event is not None :
            try :
                self .on_event (event_type ,**payload )
            except TypeError :

                self .on_event (event_type )


from __future__ import annotations 
import struct 
from typing import Iterable ,List ,Any ,Dict ,Optional ,Callable 


from ..core .filesystem_base import FilesystemBase ,DiskLike ,FreeSpaceManagerLike 




POINTER_FORMAT_CHAR ="q"
POINTER_SIZE_BYTES =struct .calcsize (POINTER_FORMAT_CHAR )


class IndexedFS (FilesystemBase ):

    def __init__ (
    self ,
    disk :DiskLike ,
    free_space_manager :FreeSpaceManagerLike ,
    *,
    on_event :Optional [Callable [...,None ]]=None ,
    )->None :
        super ().__init__ (disk ,free_space_manager ,on_event =on_event )

        self ._max_file_blocks =self .disk .block_size //POINTER_SIZE_BYTES 





    def _read_index_block (self ,index_block_idx :int ,size_blocks :int )->List [int ]:
        data =self .disk .read_block (index_block_idx )
        if data is None :
            raise IOError (f"Corrupción: Bloque índice {index_block_idx } está vacío")


        format_string =f"!{size_blocks }{POINTER_FORMAT_CHAR }"

        try :

            pointers =struct .unpack (format_string ,data [:size_blocks *POINTER_SIZE_BYTES ])
            return list (pointers )
        except struct .error :
            raise IOError (f"Corrupción: No se pudo decodificar el bloque índice {index_block_idx }")

    def _write_index_block (self ,index_block_idx :int ,data_blocks :List [int ])->None :

        format_string =f"!{len (data_blocks )}{POINTER_FORMAT_CHAR }"

        try :

            packed_data =struct .pack (format_string ,*data_blocks )


            if len (packed_data )<self .disk .block_size :
                padding =b"\x00"*(self .disk .block_size -len (packed_data ))
                packed_data +=padding 

            self .disk .write_block (index_block_idx ,packed_data )
        except struct .error as e :
            raise IOError (f"Error al empaquetar el bloque índice: {e }")





    def create (self ,name :str ,size_blocks :int )->None :
        self ._assert_new_file (name )
        self ._assert_positive_blocks (size_blocks )


        if size_blocks >self ._max_file_blocks :
            raise MemoryError (
            f"Archivo demasiado grande ({size_blocks } bloques). "
            f"Solo caben {self ._max_file_blocks } punteros en un bloque índice "
            f"de {self .disk .block_size } bytes."
            )

        self ._emit ("create:start",strategy ="indexed",name =name ,size_blocks =size_blocks )


        total_blocks_needed =size_blocks +1 
        try :
            allocated_indices =self .fsm .allocate (total_blocks_needed ,contiguous =False )
        except MemoryError :
            raise MemoryError (f"No hay espacio suficiente para {total_blocks_needed } bloques")


        index_block_idx =allocated_indices .pop (0 )
        data_blocks_indices =allocated_indices 


        self .file_table [name ]={
        "size_blocks":size_blocks ,
        "index_block":index_block_idx ,
        "overhead_blocks":1 
        }


        try :
            self ._write_index_block (index_block_idx ,data_blocks_indices )
        except (IOError ,struct .error )as e :

            print (f"Fallo al escribir el índice, revirtiendo creación: {e }")
            self .fsm .free (data_blocks_indices +[index_block_idx ])
            del self .file_table [name ]
            raise 

        self ._emit (
        "create:done",
        strategy ="indexed",
        name =name ,
        size_blocks =size_blocks ,
        index_block =index_block_idx ,
        data_blocks =data_blocks_indices 
        )

    def delete (self ,name :str )->None :
        self ._assert_file_exists (name )
        meta =self .file_table [name ]

        self ._emit ("delete:start",strategy ="indexed",name =name )

        blocks_to_free =[]
        try :

            data_blocks =self ._read_index_block (meta ["index_block"],meta ["size_blocks"])
            blocks_to_free .extend (data_blocks )
        except IOError as e :

            print (f"Advertencia: Índice de '{name }' corrupto. Se liberará solo el bloque índice. Error: {e }")


        blocks_to_free .append (meta ["index_block"])


        del self .file_table [name ]


        try :
            self .fsm .free (blocks_to_free )
        except (ValueError ,IndexError )as e :
            print (f"Error al liberar bloques para '{name }': {e }")

        self ._emit ("delete:done",strategy ="indexed",name =name ,freed =blocks_to_free )

    def _resolve_range (self ,name :str ,offset :int ,n_blocks :int )->List [int ]:
        self ._assert_file_exists (name )
        meta =self .file_table [name ]


        self ._assert_range_within_size (name ,offset ,n_blocks )


        all_data_blocks =self ._read_index_block (meta ["index_block"],meta ["size_blocks"])


        return all_data_blocks [offset :offset +n_blocks ]

    def read (self ,name :str ,offset :int ,n_blocks :int ,access_mode :str ="seq")->List [bytes ]:
        self ._assert_file_exists (name )
        self ._assert_positive_blocks (n_blocks )
        self ._assert_non_negative (offset )


        physical_indices =self ._resolve_range (name ,offset ,n_blocks )

        self ._emit (
        "read:start",
        strategy ="indexed",
        name =name ,
        offset =offset ,
        n_blocks =n_blocks ,
        physical =physical_indices ,
        access_mode =access_mode 
        )


        payloads =[]
        for block_idx in physical_indices :
            data =self .disk .read_block (block_idx )

            payloads .append (b""if data is None else data )

        self ._emit ("read:done",strategy ="indexed",name =name )
        return payloads 

    def write (self ,name :str ,offset :int ,n_blocks :int ,data :Iterable [bytes ]|None =None )->None :
        self ._assert_file_exists (name )
        self ._assert_positive_blocks (n_blocks )
        self ._assert_non_negative (offset )


        physical_indices =self ._resolve_range (name ,offset ,n_blocks )


        data_list :List [bytes |None ]
        if data is None :

            data_list =[b""]*n_blocks 
        else :
            data_list =list (data )
            if len (data_list )!=n_blocks :
                raise ValueError (f"Se esperaban {n_blocks } bloques, se recibieron {len (data_list )}")

        self ._emit (
        "write:start",
        strategy ="indexed",
        name =name ,
        offset =offset ,
        n_blocks =n_blocks ,
        physical =physical_indices 
        )


        for i in range (n_blocks ):
            block_idx =physical_indices [i ]
            payload =data_list [i ]


            self .disk .write_block (block_idx ,payload )

        self ._emit ("write:done",strategy ="indexed",name =name )
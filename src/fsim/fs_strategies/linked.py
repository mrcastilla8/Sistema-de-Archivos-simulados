import struct 
from typing import List ,Dict ,Any ,Iterable ,Optional ,Callable 


from ..core .filesystem_base import FilesystemBase ,DiskLike ,FreeSpaceManagerLike 




END_OF_FILE_MARKER =-1 



POINTER_FORMAT ="!q"
POINTER_SIZE_BYTES =struct .calcsize (POINTER_FORMAT )


class LinkedFS (FilesystemBase ):


    def __init__ (
    self ,
    disk :DiskLike ,
    free_space_manager :FreeSpaceManagerLike ,
    *,
    on_event :Optional [Callable [...,None ]]=None ,
    )->None :

        super ().__init__ (disk ,free_space_manager ,on_event =on_event )


        if self .disk .block_size <=POINTER_SIZE_BYTES :
            raise ValueError (
            f"El tamaño de bloque ({self .disk .block_size }B) debe ser "
            f"mayor que el tamaño del puntero ({POINTER_SIZE_BYTES }B)"
            )





    def _read_pointer (self ,block_index :int )->int :

        data =self .disk .read_block (block_index )
        if data is None or len (data )<POINTER_SIZE_BYTES :


            raise IOError (
            f"Error de E/S: Bloque {block_index } en la cadena está "
            f"corrupto o vacío (no se pudo leer el puntero)."
            )


        (next_block_index ,)=struct .unpack (POINTER_FORMAT ,data [:POINTER_SIZE_BYTES ])
        return int (next_block_index )

    def _write_pointer (self ,block_index :int ,next_block_index :int )->None :


        pointer_bytes =struct .pack (POINTER_FORMAT ,next_block_index )


        current_data =self .disk .read_block (block_index )

        user_data =b""
        if current_data is not None and len (current_data )>POINTER_SIZE_BYTES :

            user_data =current_data [POINTER_SIZE_BYTES :]


        full_block_data =pointer_bytes +user_data 



        self .disk .write_block (block_index ,full_block_data )

    def _get_all_blocks (self ,name :str )->List [int ]:

        self ._assert_file_exists (name )
        meta =self .file_table [name ]

        indices =[]
        current_block_idx =meta ["start_block"]


        for _ in range (meta ["size_blocks"]):
            if current_block_idx ==END_OF_FILE_MARKER :
                raise IOError (f"Corrupción detectada: Fin de archivo prematuro para '{name }'")

            if current_block_idx in indices :
                raise IOError (f"Corrupción detectada: Bucle en la cadena de '{name }' en el bloque {current_block_idx }")

            indices .append (current_block_idx )

            current_block_idx =self ._read_pointer (current_block_idx )

        return indices 





    def create (self ,name :str ,size_blocks :int )->None :

        self ._assert_new_file (name )
        self ._assert_positive_blocks (size_blocks )



        allocated_indices =self .fsm .allocate (size_blocks ,contiguous =False )


        self .file_table [name ]={
        "size_blocks":size_blocks ,
        "start_block":allocated_indices [0 ],
        }


        for i in range (size_blocks -1 ):
            current_idx =allocated_indices [i ]
            next_idx =allocated_indices [i +1 ]

            self ._write_pointer (current_idx ,next_idx )


        last_idx =allocated_indices [-1 ]
        self ._write_pointer (last_idx ,END_OF_FILE_MARKER )


        self ._emit (
        "create",
        name =name ,
        size_blocks =size_blocks ,
        allocated =allocated_indices ,
        )

    def delete (self ,name :str )->None :

        self ._assert_file_exists (name )


        try :
            blocks_to_free =self ._get_all_blocks (name )
        except IOError as e :
            print (f"Advertencia: No se pudo eliminar '{name }' limpiamente: {e }. "
            "Se intentará liberar lo encontrado...")

            meta =self .file_table .get (name ,{})
            start_block =meta .get ("start_block")
            if isinstance (start_block ,int ):

                indices =[]
                curr =start_block 
                while curr !=END_OF_FILE_MARKER and curr not in indices and len (indices )<self .n_blocks :
                    indices .append (curr )
                    try :curr =self ._read_pointer (curr )
                    except IOError :break 
                blocks_to_free =indices 
            else :
                blocks_to_free =[]


        del self .file_table [name ]


        if blocks_to_free :
            try :
                self .fsm .free (blocks_to_free )
            except (ValueError ,IndexError )as e :

                print (f"Error al liberar bloques para '{name }': {e }")


        self ._emit ("delete",name =name ,freed =blocks_to_free )

    def _resolve_range (self ,name :str ,offset :int ,n_blocks :int )->List [int ]:

        self ._assert_file_exists (name )
        meta =self .file_table [name ]


        self ._assert_range_within_size (name ,offset ,n_blocks )

        current_block_idx =meta ["start_block"]



        for _ in range (offset ):
            current_block_idx =self ._read_pointer (current_block_idx )
            if current_block_idx ==END_OF_FILE_MARKER :

                raise IndexError (
                f"Corrupción: EOF alcanzado prematuramente "
                f"mientras se buscaba el offset {offset } en '{name }'"
                )


        physical_indices =[]
        for i in range (n_blocks ):
            if current_block_idx ==END_OF_FILE_MARKER :
                 raise IndexError (
                 f"Corrupción: EOF alcanzado prematuramente "
                 f"mientras se leían {n_blocks } bloques en '{name }'"
                 )

            physical_indices .append (current_block_idx )


            if i <(n_blocks -1 ):
                current_block_idx =self ._read_pointer (current_block_idx )

        return physical_indices 

    def read (
    self ,name :str ,offset :int ,n_blocks :int ,access_mode :str ="seq"
    )->List [bytes ]:

        self ._assert_file_exists (name )
        self ._assert_positive_blocks (n_blocks )
        self ._assert_non_negative (offset )


        physical_indices =self ._resolve_range (name ,offset ,n_blocks )


        self ._emit (
        "read",
        name =name ,
        offset =offset ,
        n_blocks =n_blocks ,
        physical =physical_indices ,
        access_mode =access_mode 
        )


        payloads =[]
        for block_idx in physical_indices :
            full_data =self .disk .read_block (block_idx )

            if full_data is None :


                payloads .append (b"")
            else :

                user_data =full_data [POINTER_SIZE_BYTES :]
                payloads .append (user_data )

        return payloads 

    def write (
    self ,
    name :str ,
    offset :int ,
    n_blocks :int ,
    data :Optional [Iterable [bytes ]]=None ,
    )->None :

        self ._assert_file_exists (name )
        self ._assert_positive_blocks (n_blocks )
        self ._assert_non_negative (offset )


        physical_indices =self ._resolve_range (name ,offset ,n_blocks )


        data_list :List [bytes ]
        if data is None :

            data_list =[b""]*n_blocks 
        else :
            data_list =list (data )
            if len (data_list )!=n_blocks :
                raise ValueError (
                f"Se esperaban {n_blocks } bloques de datos, "
                f"pero se recibieron {len (data_list )}"
                )


        self ._emit (
        "write",
        name =name ,
        offset =offset ,
        n_blocks =n_blocks ,
        physical =physical_indices 
        )


        user_data_max_size =self .disk .block_size -POINTER_SIZE_BYTES 

        for i in range (n_blocks ):
            block_idx =physical_indices [i ]
            user_payload =data_list [i ]


            if len (user_payload )>user_data_max_size :
                raise ValueError (
                f"Payload del bloque {i } ({len (user_payload )}B) excede "
                f"el espacio de usuario disponible ({user_data_max_size }B)"
                )


            current_pointer =self ._read_pointer (block_idx )
            pointer_bytes =struct .pack (POINTER_FORMAT ,current_pointer )


            full_block_data =pointer_bytes +user_payload 


            self .disk .write_block (block_idx ,full_block_data )
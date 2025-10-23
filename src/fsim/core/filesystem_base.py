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
    """Interfaz mínima esperada de un disco lógico."""
    n_blocks :int 
    block_size :int 

    def read_block (self ,i :int )->bytes |None :...
    def write_block (self ,i :int ,data :bytes |None )->None :...


@runtime_checkable 
class FreeSpaceManagerLike (Protocol ):
    """Interfaz mínima esperada del gestor de espacio libre."""
    n_blocks :int 

    def allocate (self ,n :int ,contiguous :bool =False )->List [int ]:...
    def free (self ,block_list :List [int ])->None :...






class FilesystemBase (ABC ):
    """
    Contrato base para las políticas de asignación (contigua, enlazada, indexada).

    Unidades:
      - `size_blocks`, `offset`, `n_blocks` están expresados en **bloques lógicos**.
      - `block_size` (en el `disk`) está en **bytes** (solo relevante si simulan nivel de bytes).

    Estado compartido:
      - `self.disk`: provee E/S por bloque y capacidades (`n_blocks`, `block_size`).
      - `self.fsm` : gestiona la reserva/liberación de bloques físicos.
      - `self.file_table`: catálogo de archivos -> metadatos específicos de la estrategia.
          * Debe contener, como mínimo:
              - "size_blocks": int (tamaño lógico)
          * La estrategia puede añadir lo que requiera (p. ej., "start"/"length", "chain", "index_block", "data_blocks").

    Instrumentación:
      - `on_event`: Callable opcional para reportar eventos al runner/metricador.
        Se invoca con: on_event(event_type: str, **payload)
        Ejemplos de `event_type`: "create", "delete", "read", "write".

    Convenciones (recomendadas para el proyecto):
      - Tamaños lógicos **fijos** por archivo (no crecer en `write`), para comparar
        políticas de asignación sin introducir realocaciones. Si una estrategia decide
        soportar crecimiento, debe documentarlo y respetar la interfaz igualmente.
    """





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
        """
        Crea un archivo lógico de 'size_blocks' bloques y reserva los bloques físicos necesarios
        según la política de asignación.

        Precondiciones:
          - 'name' no debe existir en self.file_table.
          - 'size_blocks' > 0 (o documentar si se permite 0).
          - Debe existir espacio suficiente (y contiguo si la política lo exige).

        Efectos:
          - Reserva bloques en self.fsm (contiguos o dispersos).
          - Inicializa metadata específica de la estrategia en self.file_table[name].
          - Opcional: inicializar contenido de bloques (e.g., None o bytes vacíos).

        Postcondiciones:
          - El archivo figura en self.file_table con un mapeo lógico→físico válido.
          - Los bloques reservados están marcados como ocupados en self.fsm.

        Errores:
          - FileExistsError si 'name' ya existe.
          - MemoryError si no hay espacio suficiente (o contiguo en contigua).
          - ValueError si 'size_blocks' es inválido.
        """
        raise NotImplementedError 

    @abstractmethod 
    def delete (self ,name :str )->None :
        """
        Elimina el archivo 'name', liberando todos sus bloques físicos (incluyendo bloque índice
        en el caso de la política indexada, si aplica) y eliminando su metadata del catálogo.

        Precondiciones:
          - 'name' debe existir en self.file_table.

        Efectos:
          - Libera todos los bloques asignados a ese archivo mediante self.fsm.free(...).
          - Elimina la entrada de self.file_table[name].

        Postcondiciones:
          - 'name' no aparece en self.file_table.
          - Sus bloques quedan marcados como libres en self.fsm.

        Errores:
          - FileNotFoundError si 'name' no existe.
        """
        raise NotImplementedError 

    @abstractmethod 
    def read (self ,name :str ,offset :int ,n_blocks :int ,access_mode :str ="seq")->List [bytes ]:
        """
        Lee 'n_blocks' bloques lógicos a partir de 'offset' del archivo 'name' y devuelve
        una lista de payloads (bytes). No debe modificar estado, solo simular el costo.

        Precondiciones:
          - 'name' debe existir.
          - offset >= 0, n_blocks > 0.
          - offset + n_blocks <= size_blocks (a menos que definas lectura parcial).

        Efectos:
          - Acceso a bloques físicos mediante mapeo lógico→físico de la política.
          - Llamadas a self.disk.read_block(i) por cada bloque físico.
          - Opcional: instrumentar “seeks”/saltos físicos en función del patrón.

        Postcondiciones:
          - No modifica self.file_table ni self.fsm.

        Errores:
          - FileNotFoundError, ValueError (rangos inválidos).
        """
        raise NotImplementedError 

    @abstractmethod 
    def write (
    self ,
    name :str ,
    offset :int ,
    n_blocks :int ,
    data :Iterable [bytes ]|None =None ,
    )->None :
        """
        Escribe 'n_blocks' a partir de 'offset' en el archivo 'name'. Puede sobrescribir bloques
        existentes. Por defecto se recomienda tamaño lógico fijo (no crecer).

        Precondiciones:
          - 'name' debe existir.
          - offset >= 0, n_blocks > 0.
          - Si tamaño fijo: offset + n_blocks <= size_blocks.

        Efectos:
          - Resuelve mapeo lógico→físico y llama a self.disk.write_block(...) por bloque.
          - Si 'data' es None, se permiten bytes sintéticos (e.g., b'' o zeros) según política.

        Postcondiciones:
          - El contenido físico de esos bloques refleja los nuevos datos.

        Errores:
          - FileNotFoundError, ValueError (rangos/datos).
          - MemoryError si la política permite crecer y no hay espacio (no recomendado).
        """
        raise NotImplementedError 





    @abstractmethod 
    def _resolve_range (self ,name :str ,offset :int ,n_blocks :int )->List [int ]:
        """
        Debe ser implementado por la estrategia:
        - Devuelve la lista de índices de bloques físicos que corresponden a los bloques
          lógicos [offset, offset + n_blocks) del archivo 'name'.
        - No realiza E/S; solo mapeo lógico→físico.

        Errores:
          - FileNotFoundError si 'name' no existe.
          - ValueError si el rango es inválido o no representable por la estructura de la estrategia.
        """
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
        """
        Devuelve [(name, size_blocks), ...] de todos los archivos registrados.
        No garantiza orden.
        """
        return [(k ,int (v .get ("size_blocks",0 )))for k ,v in self .file_table .items ()]

    def get_file_info (self ,name :str )->Dict [str ,Any ]:
        """
        Devuelve una copia superficial del metadata del archivo 'name'.
        """
        self ._assert_file_exists (name )

        return dict (self .file_table [name ])

    def space_usage_summary (self )->Dict [str ,int ]:
        """
        Resumen de uso de espacio (en bloques). Implementación genérica; el fsm puede
        mantener su propio contador más eficiente, pero esto estandariza la salida.
        """
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
        """
        Notifica un evento (create|delete|read|write|...) al 'runner' o a quien consuma
        métricas. La estrategia puede llamarlo antes/después de su operación principal.

        Ejemplos:
            self._emit("create", name=name, size_blocks=size, allocated=idxs)
            self._emit("read", name=name, offset=offset, n_blocks=n, physical=phys_idxs)
        """
        if self .on_event is not None :
            try :
                self .on_event (event_type ,**payload )
            except TypeError :

                self .on_event (event_type )

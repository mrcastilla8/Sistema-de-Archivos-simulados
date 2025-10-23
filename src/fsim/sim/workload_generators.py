
from __future__ import annotations 
import random 
from typing import Dict ,Any ,List ,Tuple ,Optional ,Set 





def _rand_size (rng :random .Random ,rng_pair :Tuple [int ,int ])->int :
    """Devuelve un tamaño en bloques dentro del rango [min, max]."""
    lo ,hi =rng_pair 
    return rng .randint (lo ,hi )

def _choose_access_mode (rng :random .Random ,seq_prob :float )->str :
    """Elige 'seq' o 'rand' según probabilidad de acceso secuencial."""
    return "seq"if rng .random ()<seq_prob else "rand"

def _ensure_min_ops_weights (delete_rate :float )->List [float ]:
    """
    Devuelve pesos [create, delete, read, write] coherentes.
    - Aumenta 'delete' en función de delete_rate para inducir fragmentación cuando se solicita.
    - Mantiene un equilibrio razonable para que haya lecturas/escrituras útiles.
    """

    w_create =0.25 

    w_delete =min (0.1 +0.8 *delete_rate ,0.45 )

    remaining =max (0.0 ,1.0 -(w_create +w_delete ))
    w_read =remaining *0.5 
    w_write =remaining *0.5 
    return [w_create ,w_delete ,w_read ,w_write ]

def _new_name (kind :str ,idx :int )->str :
    """Construye un nombre único determinista."""
    return f"{kind }_{idx :06d}"

def _next_unique_name (kind :str ,counter :int ,existing :Set [str ])->Tuple [str ,int ]:
    """
    Genera el siguiente nombre único (sin colisionar con 'existing')
    y devuelve (name, next_counter).
    """
    while True :
        name =_new_name (kind ,counter )
        counter +=1 
        if name not in existing :
            return name ,counter 

def _pick_existing (rng :random .Random ,names :List [str ])->str |None :
    """Elige un archivo existente al azar (o None si no hay)."""
    if not names :
        return None 
    return rng .choice (names )

def _compute_offset_and_len (
rng :random .Random ,
size_blocks :int ,
access_mode :str ,
seq_cursor :int |None ,
max_io_blocks :int ,
)->Tuple [int ,int ,int ]:
    """
    Devuelve (offset, n_blocks, new_cursor). Asegura que offset+n_blocks <= size_blocks.
    - Para 'seq', usa el cursor actual (o 0) y lo avanza.
    - Para 'rand', elige un offset válido al azar.
    """
    if size_blocks <=0 :
        return 0 ,0 ,seq_cursor or 0 


    n_blocks =rng .randint (1 ,min (max_io_blocks ,size_blocks ))

    if access_mode =="seq":
        cur =seq_cursor or 0 
        if cur >=size_blocks :
            cur =0 

        if cur +n_blocks >size_blocks :
            n_blocks =size_blocks -cur 
            if n_blocks <=0 :
                n_blocks =1 
                cur =0 
        offset =cur 
        new_cursor =(cur +n_blocks )%size_blocks if size_blocks >0 else 0 
        return offset ,n_blocks ,new_cursor 
    else :

        if n_blocks >=size_blocks :
            offset =0 
            n_blocks =size_blocks 
        else :
            offset =rng .randint (0 ,size_blocks -n_blocks )
        return offset ,n_blocks ,seq_cursor or 0 



def generate_workload (
cfg :Dict [str ,Any ],
seed :int |None =None ,
*,
user_files :Optional [List [Dict [str ,Any ]]]=None ,
respect_user_files_only :bool =False ,
)->List [Dict [str ,Any ]]:
    """
    Genera una lista de operaciones realista para el simulador.

    Requisitos del cfg (normalizado por scenario_definitions.get_config):
      - disk_size (int), block_size (int)
      - n_files_small (int), file_small_range (tuple[min,max])
      - n_files_large (int), file_large_range (tuple[min,max])
      - access_pattern: {'seq': float, 'rand': float} con suma 1.0
      - delete_rate (0..1), ops (int)
      - (opcional) max_io_blocks (int): límite superior de bloques por op de IO (default 8)

    Parámetros nuevos:
      - user_files: lista opcional de archivos manuales a poblar inicialmente.
          Formato por elemento: {'name': str, 'size_blocks': int (>0)}
      - respect_user_files_only: si True, NO se genera población inicial aleatoria
          (n_files_small/large se ignoran). El resto del flujo (create/delete/read/write)
          permanece igual (es decir, puede haber creates dinámicos más adelante).

    Estrategia:
      1) Población inicial:
         - Si user_files viene: se emiten 'create' para cada archivo.
         - Si respect_user_files_only es False: además, se crean archivos según
           n_files_small/n_files_large.
      2) Flujo de 'ops' operaciones: mezcla create/delete/read/write según pesos
         derivados de delete_rate, garantizando operaciones válidas (p. ej., no leer si no hay archivos).
      3) Para 'seq', mantiene un cursor por archivo; para 'rand', elige offset al azar.
    """
    rng =random .Random (seed )
    ops :List [Dict [str ,Any ]]=[]


    n_ops :int =int (cfg .get ("ops",1000 ))
    n_small :int =int (cfg .get ("n_files_small",0 ))
    n_large :int =int (cfg .get ("n_files_large",0 ))
    small_rng :Tuple [int ,int ]=tuple (cfg .get ("file_small_range",(1 ,4 )))
    large_rng :Tuple [int ,int ]=tuple (cfg .get ("file_large_range",(16 ,128 )))
    seq_prob :float =float (cfg .get ("access_pattern",{}).get ("seq",0.5 ))
    delete_rate :float =float (cfg .get ("delete_rate",0.1 ))
    max_io_blocks :int =int (cfg .get ("max_io_blocks",8 ))


    files :Dict [str ,Dict [str ,int ]]={}
    live_names :List [str ]=[]
    existing_names :Set [str ]=set ()


    counter_small =0 
    counter_large =0 




    if user_files :

        for idx ,uf in enumerate (user_files ):
            if not isinstance (uf ,dict ):
                raise ValueError (f"user_files[{idx }] debe ser dict con 'name' y 'size_blocks'")
            name =uf .get ("name")
            size =uf .get ("size_blocks")
            if not isinstance (name ,str )or not name :
                raise ValueError (f"user_files[{idx }]: 'name' debe ser str no vacío")
            if not isinstance (size ,int )or size <=0 :
                raise ValueError (f"user_files[{idx }]: 'size_blocks' debe ser int > 0")
            if name in existing_names :
                raise ValueError (f"user_files: nombre duplicado: '{name }'")

            files [name ]={"size":size ,"cursor":0 }
            live_names .append (name )
            existing_names .add (name )
            ops .append ({
            "op":"create",
            "name":name ,
            "size_blocks":size ,
            "offset":0 ,
            "n_blocks":0 ,
            "access_mode":"seq",
            })




    if not respect_user_files_only :

        for _ in range (n_small ):

            name ,counter_small =_next_unique_name ("small",counter_small ,existing_names )
            size =_rand_size (rng ,small_rng )
            files [name ]={"size":size ,"cursor":0 }
            live_names .append (name )
            existing_names .add (name )
            ops .append ({"op":"create","name":name ,"size_blocks":size ,"offset":0 ,"n_blocks":0 ,"access_mode":"seq"})

        for _ in range (n_large ):
            name ,counter_large =_next_unique_name ("large",counter_large ,existing_names )
            size =_rand_size (rng ,large_rng )
            files [name ]={"size":size ,"cursor":0 }
            live_names .append (name )
            existing_names .add (name )
            ops .append ({"op":"create","name":name ,"size_blocks":size ,"offset":0 ,"n_blocks":0 ,"access_mode":"seq"})




    weights =_ensure_min_ops_weights (delete_rate )
    kinds_for_create =["small","large"]
    kind_probs =[0.75 ,0.25 ]

    for _ in range (n_ops ):

        if not live_names :
            chosen ="create"
        else :
            chosen =rng .choices (["create","delete","read","write"],weights =weights ,k =1 )[0 ]

        if chosen =="create":
            kind =rng .choices (kinds_for_create ,weights =kind_probs ,k =1 )[0 ]
            if kind =="small":
                name ,counter_small =_next_unique_name ("small",counter_small ,existing_names )
                size =_rand_size (rng ,small_rng )
            else :
                name ,counter_large =_next_unique_name ("large",counter_large ,existing_names )
                size =_rand_size (rng ,large_rng )

            files [name ]={"size":size ,"cursor":0 }
            live_names .append (name )
            existing_names .add (name )

            ops .append ({
            "op":"create",
            "name":name ,
            "size_blocks":size ,
            "offset":0 ,
            "n_blocks":0 ,
            "access_mode":"seq",
            })

        elif chosen =="delete":

            victim =_pick_existing (rng ,live_names )
            if victim is None :

                kind =rng .choices (kinds_for_create ,weights =kind_probs ,k =1 )[0 ]
                if kind =="small":
                    name ,counter_small =_next_unique_name ("small",counter_small ,existing_names )
                    size =_rand_size (rng ,small_rng )
                else :
                    name ,counter_large =_next_unique_name ("large",counter_large ,existing_names )
                    size =_rand_size (rng ,large_rng )
                files [name ]={"size":size ,"cursor":0 }
                live_names .append (name )
                existing_names .add (name )
                ops .append ({"op":"create","name":name ,"size_blocks":size ,"offset":0 ,"n_blocks":0 ,"access_mode":"seq"})
            else :
                ops .append ({
                "op":"delete",
                "name":victim ,
                "size_blocks":0 ,
                "offset":0 ,
                "n_blocks":0 ,
                "access_mode":"seq",
                })

                live_names .remove (victim )
                existing_names .discard (victim )
                files .pop (victim ,None )

        elif chosen in ("read","write"):
            target =_pick_existing (rng ,live_names )
            if target is None :

                kind =rng .choices (kinds_for_create ,weights =kind_probs ,k =1 )[0 ]
                if kind =="small":
                    name ,counter_small =_next_unique_name ("small",counter_small ,existing_names )
                    size =_rand_size (rng ,small_rng )
                else :
                    name ,counter_large =_next_unique_name ("large",counter_large ,existing_names )
                    size =_rand_size (rng ,large_rng )
                files [name ]={"size":size ,"cursor":0 }
                live_names .append (name )
                existing_names .add (name )
                ops .append ({"op":"create","name":name ,"size_blocks":size ,"offset":0 ,"n_blocks":0 ,"access_mode":"seq"})
                continue 


            size =files [target ]["size"]
            access_mode =_choose_access_mode (rng ,seq_prob )
            cursor =files [target ]["cursor"]
            offset ,n_blocks ,new_cursor =_compute_offset_and_len (
            rng ,size ,access_mode ,cursor ,max_io_blocks 
            )
            files [target ]["cursor"]=new_cursor 

            ops .append ({
            "op":chosen ,
            "name":target ,
            "size_blocks":0 ,
            "offset":offset ,
            "n_blocks":n_blocks ,
            "access_mode":access_mode ,
            })

        else :

            name ,counter_small =_next_unique_name ("small",counter_small ,existing_names )
            size =_rand_size (rng ,small_rng )
            files [name ]={"size":size ,"cursor":0 }
            live_names .append (name )
            existing_names .add (name )
            ops .append ({"op":"create","name":name ,"size_blocks":size ,"offset":0 ,"n_blocks":0 ,"access_mode":"seq"})

    return ops 

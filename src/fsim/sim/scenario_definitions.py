
from __future__ import annotations 
import json 
from pathlib import Path 
from typing import Dict ,Any ,Tuple 





DEFAULTS :Dict [str ,Dict [str ,Any ]]={
"mix-small-large":{
"description":"Mezcla de archivos pequeños y grandes, 60% secuencial, 40% aleatorio",
"disk_size":50000 ,
"block_size":4096 ,
"n_files_small":200 ,
"file_small_range":[1 ,16 ],
"n_files_large":30 ,
"file_large_range":[256 ,2048 ],
"access_pattern":{"seq":0.6 ,"rand":0.4 },
"delete_rate":0.1 ,
"ops":1000 ,
},
"seq-vs-rand":{
"description":"Comparativa de acceso 90% secuencial vs 90% aleatorio",
"disk_size":40000 ,
"block_size":4096 ,
"n_files_small":150 ,
"file_small_range":[1 ,32 ],
"n_files_large":20 ,
"file_large_range":[128 ,1024 ],
"access_pattern":{"seq":0.9 ,"rand":0.1 },
"delete_rate":0.05 ,
"ops":800 ,
},
"frag-intensive":{
"description":"Creación/borrado intensivo para inducir fragmentación",
"disk_size":60000 ,
"block_size":4096 ,
"n_files_small":250 ,
"file_small_range":[1 ,8 ],
"n_files_large":10 ,
"file_large_range":[512 ,1024 ],
"access_pattern":{"seq":0.5 ,"rand":0.5 },
"delete_rate":0.4 ,
"ops":1500 ,
},
}


_REQUIRED_KEYS ={
"description":str ,
"disk_size":int ,
"block_size":int ,
"n_files_small":int ,
"file_small_range":(list ,tuple ),
"n_files_large":int ,
"file_large_range":(list ,tuple ),
"access_pattern":dict ,
"delete_rate":(int ,float ),
"ops":int ,
}





def load_from_json (path :str |Path )->Dict [str ,Dict [str ,Any ]]:
    """
    Carga escenarios desde un JSON opcional. El archivo debe mapear:
      { "<scenario_name>": {<config>}, ... }
    Si el archivo no existe, retorna {}.
    """
    p =Path (path )
    if not p .exists ():
        return {}
    with p .open ("r",encoding ="utf-8")as f :
        data =json .load (f )
    if not isinstance (data ,dict ):
        raise ValueError ("El JSON de escenarios debe ser un objeto {nombre: config}.")

    return data 





def _as_range_pair (value :Any ,field :str )->Tuple [int ,int ]:
    """
    Normaliza un rango ingresado como [min, max] o (min, max) a (int, int).
    Valida que 1 <= min <= max.
    """
    if not isinstance (value ,(list ,tuple ))or len (value )!=2 :
        raise ValueError (f"{field } debe ser una lista/tupla [min, max].")
    a ,b =value 
    if not (isinstance (a ,int )and isinstance (b ,int )):
        raise ValueError (f"{field } debe contener enteros.")
    if a <1 or b <1 or a >b :
        raise ValueError (f"{field } inválido: se requiere 1 <= min <= max (recibido {value }).")
    return int (a ),int (b )

def _normalize_access_pattern (p :Dict [str ,Any ])->Dict [str ,float ]:
    """
    Normaliza access_pattern para que contenga claves 'seq' y 'rand' y sume 1.0.
    Si faltan, se asigna 0.0. Si suma 0, se usa (1.0, 0.0) por defecto.
    """
    seq =float (p .get ("seq",0.0 ))
    rand =float (p .get ("rand",0.0 ))
    total =seq +rand 
    if total <=0.0 :

        return {"seq":1.0 ,"rand":0.0 }
    return {"seq":seq /total ,"rand":rand /total }

def _validate_schema (name :str ,cfg :Dict [str ,Any ])->None :
    """
    Valida tipos y rangos básicos. Lanza ValueError con mensajes claros.
    """
    for k ,typ in _REQUIRED_KEYS .items ():
        if k not in cfg :
            raise ValueError (f"[{name }] Falta clave requerida: '{k }'")
        if not isinstance (cfg [k ],typ ):
            raise ValueError (f"[{name }] Tipo inválido para '{k }': esperado {typ }, recibido {type (cfg [k ])}")

    if cfg ["disk_size"]<=0 :
        raise ValueError (f"[{name }] 'disk_size' debe ser > 0")
    if cfg ["block_size"]<=0 :
        raise ValueError (f"[{name }] 'block_size' debe ser > 0")
    if cfg ["n_files_small"]<0 or cfg ["n_files_large"]<0 :
        raise ValueError (f"[{name }] 'n_files_small' y 'n_files_large' deben ser >= 0")
    if cfg ["ops"]<=0 :
        raise ValueError (f"[{name }] 'ops' debe ser > 0")


    _as_range_pair (cfg ["file_small_range"],"file_small_range")
    _as_range_pair (cfg ["file_large_range"],"file_large_range")


    dr =float (cfg ["delete_rate"])
    if dr <0.0 or dr >1.0 :
        raise ValueError (f"[{name }] 'delete_rate' debe estar en [0, 1] (recibido {dr }).")


    if not isinstance (cfg ["access_pattern"],dict ):
        raise ValueError (f"[{name }] 'access_pattern' debe ser dict con claves 'seq'/'rand'.")

def _normalize_config (cfg :Dict [str ,Any ])->Dict [str ,Any ]:
    """
    Retorna una copia normalizada del config:
      - Rango de tamaños como tuplas (min,max)
      - access_pattern normalizado a prob distribucional
    """
    norm =dict (cfg )
    norm ["file_small_range"]=_as_range_pair (cfg ["file_small_range"],"file_small_range")
    norm ["file_large_range"]=_as_range_pair (cfg ["file_large_range"],"file_large_range")
    norm ["access_pattern"]=_normalize_access_pattern (cfg ["access_pattern"])
    return norm 





def available_scenarios (extra_path :str |Path |None =None )->Dict [str ,str ]:
    """
    Devuelve {nombre: descripción} de escenarios disponibles,
    combinando DEFAULTS con los definidos en extra_path (si existe).
    """
    combined :Dict [str ,Dict [str ,Any ]]=dict (DEFAULTS )
    if extra_path :
        combined .update (load_from_json (extra_path ))
    return {k :v .get ("description","")for k ,v in combined .items ()}

def get_config (
scenario :str |None ,
scenarios_path :str |Path |None =None ,
overrides :Dict [str ,Any ]|None =None ,
)->Dict [str ,Any ]:
    """
    Resuelve la configuración final a usar por el runner:
      1) Parte del escenario elegido desde DEFAULTS + JSON externo (si hay).
      2) Aplica overrides (si vienen).
      3) Valida y normaliza (rangos, pesos, límites).
    Lanza KeyError si no existe el escenario indicado.
    Lanza ValueError si hay inconsistencias de esquema o valores.
    """
    combined :Dict [str ,Dict [str ,Any ]]=dict (DEFAULTS )
    if scenarios_path :
        combined .update (load_from_json (scenarios_path ))

    cfg :Dict [str ,Any ]={}
    if scenario :
        if scenario not in combined :
            raise KeyError (f"Escenario '{scenario }' no existe")
        cfg .update (combined [scenario ])

    if overrides :
        cfg .update (overrides )

    if not cfg :
        raise ValueError ("No se proporcionó escenario ni overrides con configuración.")


    _validate_schema (scenario or "<overrides>",cfg )
    cfg =_normalize_config (cfg )
    return cfg 

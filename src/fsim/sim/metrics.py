
from __future__ import annotations 
from typing import Dict ,Any ,List 
import json 
import csv 
import statistics 
import time 





def summarize (results :List [Dict [str ,Any ]])->Dict [str ,float ]:
    """
    Calcula promedios básicos de rendimiento (versión resumida).
    """
    if not results :
        return {
        "avg_access_time_ms":0.0 ,
        "space_usage_pct":0.0 ,
        "fragmentation_internal_pct":0.0 ,
        "fragmentation_external_pct":0.0 ,
        }

    n =len (results )
    avg_access_time =sum (r .get ("access_time_ms",0 )for r in results )/n 
    avg_usage =sum ((r .get ("space_used",0 )/max (r .get ("space_total",1 ),1 ))*100 for r in results )/n 
    avg_external_frag =sum (r .get ("external_frag",0 )*100 for r in results )/n 

    return {
    "avg_access_time_ms":round (avg_access_time ,3 ),
    "space_usage_pct":round (avg_usage ,2 ),
    "fragmentation_internal_pct":0.0 ,
    "fragmentation_external_pct":round (avg_external_frag ,2 ),
    }






def full_metrics_summary (results :List [Dict [str ,Any ]])->Dict [str ,float ]:
    """
    Calcula métricas completas de rendimiento según las especificaciones oficiales:
      - Tiempo promedio de acceso
      - Uso de espacio
      - Fragmentación interna y externa
      - Throughput (ops/seg)
      - Hit/Miss ratio
      - Uso de CPU
      - Fairness (equidad)
    """

    if not results :
        return {
        "avg_access_time_ms":0.0 ,
        "space_usage_pct":0.0 ,
        "fragmentation_internal_pct":0.0 ,
        "fragmentation_external_pct":0.0 ,
        "throughput_ops_per_sec":0.0 ,
        "hit_miss_ratio":0.0 ,
        "cpu_usage_pct":0.0 ,
        "fairness_index":0.0 ,
        }

    n =len (results )


    avg_access_time =sum (r .get ("access_time_ms",0 )for r in results )/n 
    total_time_s =sum (r .get ("elapsed_time_s",0 )for r in results )
    throughput =n /total_time_s if total_time_s >0 else 0.0 


    avg_usage =sum ((r .get ("space_used",0 )/max (r .get ("space_total",1 ),1 ))*100 for r in results )/n 
    avg_external_frag =sum (r .get ("external_frag",0 )*100 for r in results )/n 
    avg_internal_frag =sum (r .get ("internal_frag",0 )*100 for r in results )/n 


    total_hits =sum (r .get ("hits",0 )for r in results )
    total_misses =sum (r .get ("misses",0 )for r in results )
    hit_miss_ratio =(total_hits /(total_hits +total_misses ))*100 if (total_hits +total_misses )>0 else 0.0 


    cpu_time =sum (r .get ("cpu_time",0.0 )for r in results )
    total_elapsed =total_time_s if total_time_s >0 else 1.0 
    cpu_usage_pct =(cpu_time /total_elapsed )*100 


    access_times =[r .get ("access_time_ms",0 )for r in results if "access_time_ms"in r ]
    fairness_index =0.0 
    if len (access_times )>1 :
        fairness_index =statistics .pstdev (access_times )/(sum (access_times )/len (access_times ))*100 

    return {
    "avg_access_time_ms":round (avg_access_time ,3 ),
    "space_usage_pct":round (avg_usage ,2 ),
    "fragmentation_internal_pct":round (avg_internal_frag ,2 ),
    "fragmentation_external_pct":round (avg_external_frag ,2 ),
    "throughput_ops_per_sec":round (throughput ,3 ),
    "hit_miss_ratio":round (hit_miss_ratio ,2 ),
    "cpu_usage_pct":round (cpu_usage_pct ,2 ),
    "fairness_index":round (fairness_index ,2 ),
    }






class Metrics :
    def __init__ (self ,disk ,fsm ,fs ):
        self .disk =disk 
        self .fsm =fsm 
        self .fs =fs 
        self .start_time =time .perf_counter ()
        self .start_cpu =time .process_time ()

    def compute (self )->Dict [str ,float ]:
        """Calcula métricas actuales del sistema."""
        total_blocks =self .fsm .n_blocks 
        used_blocks =self .fsm .used_count ()
        free_blocks =self .fsm .free_count ()

        external_frag =self .fsm .external_fragmentation_ratio ()*100 
        internal_frag =0.0 

        elapsed =time .perf_counter ()-self .start_time 
        cpu_time =time .process_time ()-self .start_cpu 
        cpu_usage_pct =(cpu_time /elapsed )*100 if elapsed >0 else 0.0 

        return {
        "total_blocks":total_blocks ,
        "used_blocks":used_blocks ,
        "free_blocks":free_blocks ,
        "space_usage_pct":round ((used_blocks /total_blocks )*100 ,2 ),
        "fragmentation_external_pct":round (external_frag ,2 ),
        "fragmentation_internal_pct":round (internal_frag ,2 ),
        "files_stored":len (self .fs .file_table ),
        "cpu_usage_pct":round (cpu_usage_pct ,2 ),
        }

    def print_summary (self ):
        m =self .compute ()
        print ("\n===== MÉTRICAS DEL SISTEMA =====")
        for k ,v in m .items ():
            print (f"{k }: {v }")

    def export_json (self ,path :str ="metrics.json"):
        with open (path ,"w",encoding ="utf-8")as f :
            json .dump (self .compute (),f ,indent =4 )
        print (f"Métricas exportadas a {path }")

    def export_csv (self ,path :str ="metrics.csv"):
        m =self .compute ()
        with open (path ,"w",newline ="",encoding ="utf-8")as f :
            writer =csv .writer (f )
            writer .writerow (["Métrica","Valor"])
            for k ,v in m .items ():
                writer .writerow ([k ,v ])
        print (f"Métricas exportadas a {path }")


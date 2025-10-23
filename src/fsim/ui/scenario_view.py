
import customtkinter as ctk 
from customtkinter import filedialog 
import threading 
import json 
import csv 
from typing import Callable ,Dict ,Any ,List ,Optional 


from ..sim .runner import run_simulation ,STRATEGIES 
from ..sim .scenario_definitions import available_scenarios ,get_config 


STRATEGY_MAP_ES ={
"contiguous":"Asignación Contigua",
"linked":"Asignación Enlazada",
"indexed":"Asignación Indexada",
"all":"Todas las Estrategias"
}
STRATEGY_MAP_EN ={v :k for k ,v in STRATEGY_MAP_ES .items ()}
SCENARIO_MAP_ES :Dict [str ,str ]={}
SCENARIO_MAP_EN :Dict [str ,str ]={}


class ScenarioView (ctk .CTkFrame ):
    """
    Vista para configurar y lanzar una simulación.
    Incluye lógica para carga de archivos manuales.
    """

    def __init__ (self ,
    master ,
    on_run_start :Callable [[],None ],
    on_run_complete :Callable [[Dict [str ,Any ],Optional [Dict [str ,List [int ]]]],None ],
    on_live_update :Callable [[str ,List [int ]],None ],
    palette :Dict [str ,str ],
    **kwargs ):
        super ().__init__ (master ,**kwargs )
        self .on_run_start =on_run_start 
        self .on_run_complete =on_run_complete 
        self .on_live_update =on_live_update 
        self .palette =palette 

        self .manual_file_rows :List [tuple ]=[]

        self .grid_columnconfigure (0 ,weight =1 )

        config_frame =ctk .CTkFrame (self ,fg_color ="transparent")
        config_frame .pack (pady =20 ,padx =20 ,fill ="x",expand =False )

        config_frame .grid_columnconfigure (0 ,weight =0 ,minsize =140 )
        config_frame .grid_columnconfigure (1 ,weight =1 )


        self .label_style ={"text_color":self .palette ["text_light"]}
        button_style ={
        "fg_color":self .palette ["button"],
        "hover_color":self .palette ["button_hover"],
        "text_color":self .palette ["text_on_button"]
        }
        option_style ={
        "fg_color":self .palette ["button"],
        "button_color":self .palette ["button"],
        "button_hover_color":self .palette ["button_hover"],
        "text_color":self .palette ["text_on_button"],
        "dropdown_fg_color":self .palette ["frame_bg"],
        "dropdown_hover_color":self .palette ["button_hover"],
        "dropdown_text_color":self .palette ["text_light"]
        }
        checkbox_style ={
        "text_color":self .palette ["text_light"],
        "border_color":self .palette ["button"],
        "hover_color":self .palette ["button_hover"],
        "fg_color":self .palette ["button"]
        }
        self .entry_style ={
        "border_color":self .palette ["button"],
        "text_color":self .palette ["text_light"],
        "fg_color":self .palette ["app_bg"]
        }

        current_row =0 


        self .strategy_label =ctk .CTkLabel (config_frame ,text ="Estrategia:",anchor ="w",**self .label_style )
        self .strategy_label .grid (row =current_row ,column =0 ,padx =0 ,pady =(10 ,5 ),sticky ="w")
        strategy_display_names =list (STRATEGY_MAP_ES .values ())
        default_strategy_display =STRATEGY_MAP_ES ["contiguous"]
        self .strategy_var =ctk .StringVar (value =default_strategy_display )
        self .strategy_menu =ctk .CTkOptionMenu (
        config_frame ,variable =self .strategy_var ,values =strategy_display_names ,**option_style 
        )
        self .strategy_menu .grid (row =current_row ,column =1 ,padx =0 ,pady =(10 ,5 ),sticky ="ew")
        current_row +=1 


        self .scenario_label =ctk .CTkLabel (config_frame ,text ="Escenario Base:",anchor ="w",**self .label_style )
        self .scenario_label .grid (row =current_row ,column =0 ,padx =0 ,pady =5 ,sticky ="w")
        self ._load_scenarios_maps ()
        scenario_display_names =list (SCENARIO_MAP_ES .values ())
        default_scenario_display =scenario_display_names [0 ]if scenario_display_names else "Sin Escenarios"
        self .scenario_var =ctk .StringVar (value =default_scenario_display )
        self .scenario_menu =ctk .CTkOptionMenu (
        config_frame ,variable =self .scenario_var ,values =scenario_display_names ,**option_style 
        )
        self .scenario_menu .grid (row =current_row ,column =1 ,padx =0 ,pady =5 ,sticky ="ew")
        current_row +=1 


        self .slow_mo_var =ctk .BooleanVar (value =True )
        self .slow_mo_check =ctk .CTkCheckBox (
        config_frame ,
        text ="Activar visualización lenta (Modo Demo)",
        variable =self .slow_mo_var ,
        **checkbox_style 
        )
        self .slow_mo_check .grid (row =current_row ,column =0 ,columnspan =2 ,padx =0 ,pady =10 ,sticky ="w")
        current_row +=1 


        sep =ctk .CTkFrame (config_frame ,height =2 ,border_width =0 ,fg_color =self .palette ["button"])
        sep .grid (row =current_row ,column =0 ,columnspan =2 ,sticky ="ew",pady =15 )
        current_row +=1 


        self .workload_mode_label =ctk .CTkLabel (config_frame ,text ="Carga de Archivos:",anchor ="w",**self .label_style )
        self .workload_mode_label .grid (row =current_row ,column =0 ,padx =0 ,pady =10 ,sticky ="w")
        self .workload_mode_var =ctk .StringVar (value ="Aleatorio (Seed)")
        self .workload_mode_toggle =ctk .CTkSegmentedButton (
        config_frame ,
        values =["Aleatorio (Seed)","Manual (Lista)"],
        variable =self .workload_mode_var ,
        command =self ._on_workload_mode_change ,
        text_color =self .palette ["text_on_button"],
        selected_color =self .palette ["button"],
        selected_hover_color =self .palette ["button_hover"],
        unselected_color =self .palette ["frame_bg"],
        unselected_hover_color =self .palette ["app_bg"],

        border_width =0 
        )
        self .workload_mode_toggle .grid (row =current_row ,column =1 ,sticky ="ew",pady =10 )

        self .workload_panels_row =current_row +1 
        current_row +=1 



        self .seed_label =ctk .CTkLabel (config_frame ,text ="Seed (Semilla):",**self .label_style )

        self .seed_frame =ctk .CTkFrame (config_frame ,fg_color ="transparent")
        self .seed_entry =ctk .CTkEntry (self .seed_frame ,placeholder_text ="Vacío para aleatorio",**self .entry_style )
        self .seed_entry .pack (fill ="x",expand =True )


        self .manual_frame =ctk .CTkFrame (config_frame ,fg_color ="transparent")

        self .manual_frame .grid_columnconfigure (0 ,weight =1 )


        manual_controls_frame =ctk .CTkFrame (self .manual_frame ,fg_color ="transparent")
        manual_controls_frame .grid (row =0 ,column =0 ,sticky ="ew")
        self .add_file_button =ctk .CTkButton (manual_controls_frame ,text ="Añadir Archivo",command =self ._add_file_row ,**button_style )
        self .add_file_button .pack (side ="left",padx =(0 ,10 ))
        self .import_button =ctk .CTkButton (manual_controls_frame ,text ="Importar CSV/JSON",command =self ._import_files ,**button_style )
        self .import_button .pack (side ="left",padx =10 )
        self .respect_only_var =ctk .BooleanVar (value =True )
        self .respect_only_check =ctk .CTkCheckBox (
        manual_controls_frame ,
        text ="Usar solo esta lista (ignorar aleatorios)",
        variable =self .respect_only_var ,
        **checkbox_style 
        )
        self .respect_only_check .pack (side ="left",padx =20 )
        header_frame =ctk .CTkFrame (self .manual_frame ,fg_color ="transparent")
        header_frame .grid (row =1 ,column =0 ,sticky ="ew",pady =(10 ,0 ))
        header_frame .grid_columnconfigure (0 ,weight =2 )
        header_frame .grid_columnconfigure (1 ,weight =1 )
        header_frame .grid_columnconfigure (2 ,minsize =40 )
        ctk .CTkLabel (header_frame ,text ="Nombre de Archivo",**self .label_style ,font =ctk .CTkFont (weight ="bold")).grid (row =0 ,column =0 )
        ctk .CTkLabel (header_frame ,text ="Tamaño (Bloques)",**self .label_style ,font =ctk .CTkFont (weight ="bold")).grid (row =0 ,column =1 )
        self .file_list_frame =ctk .CTkScrollableFrame (self .manual_frame ,height =150 ,fg_color =self .palette ["app_bg"])
        self .file_list_frame .grid (row =2 ,column =0 ,sticky ="ew",pady =(5 ,10 ))
        self .file_list_frame .grid_columnconfigure (0 ,weight =1 )

        current_row +=1 


        self .run_button =ctk .CTkButton (config_frame ,text ="Ejecutar Simulación",command =self ._start_simulation ,**button_style )
        self .run_button .grid (row =current_row ,column =0 ,columnspan =2 ,padx =0 ,pady =20 )
        current_row +=1 


        self .status_label =ctk .CTkLabel (config_frame ,text ="",text_color =self .palette ["text_light"])
        self .status_label .grid (row =current_row ,column =0 ,columnspan =2 ,padx =0 ,pady =0 )


        self ._on_workload_mode_change ("Aleatorio (Seed)")


    def _load_scenarios_maps (self ):
        """Carga y traduce los escenarios."""
        global SCENARIO_MAP_ES ,SCENARIO_MAP_EN 
        try :
            scenarios =available_scenarios ("data/scenarios.json")
            SCENARIO_MAP_ES .clear ()
            SCENARIO_MAP_EN .clear ()
            for key ,description in scenarios .items ():
                friendly_name =""
                if key =="mix-small-large":friendly_name ="Mezcla Pequeños y Grandes"
                elif key =="seq-vs-rand":friendly_name ="Acceso Secuencial vs Aleatorio"
                elif key =="frag-intensive":friendly_name ="Fragmentación Intensiva"
                else :friendly_name =description .split (",")[0 ]
                SCENARIO_MAP_ES [key ]=friendly_name 
                SCENARIO_MAP_EN [friendly_name ]=key 
        except Exception as e :
            print (f"Error cargando scenarios.json: {e }")

    def _on_workload_mode_change (self ,mode :str ):
        """Muestra u oculta los paneles de Seed o Manual."""
        row_to_use =self .workload_panels_row 


        if mode =="Aleatorio (Seed)":

            self .seed_label .grid (row =row_to_use ,column =0 ,padx =0 ,pady =5 ,sticky ="w")
            self .seed_frame .grid (row =row_to_use ,column =1 ,sticky ="ew",pady =5 )

            self .manual_frame .grid_forget ()
        else :

            self .seed_label .grid_forget ()
            self .seed_frame .grid_forget ()

            self .manual_frame .grid (row =row_to_use ,column =0 ,columnspan =2 ,sticky ="ew",pady =5 )


    def _add_file_row (self ,name :str ="",size :Any =""):
        row_frame =ctk .CTkFrame (self .file_list_frame ,fg_color ="transparent")
        row_frame .pack (fill ="x",pady =2 )
        row_frame .grid_columnconfigure (0 ,weight =2 )
        row_frame .grid_columnconfigure (1 ,weight =1 )
        row_frame .grid_columnconfigure (2 ,minsize =40 )

        name_entry =ctk .CTkEntry (row_frame ,**self .entry_style )
        name_entry .insert (0 ,name )
        name_entry .grid (row =0 ,column =0 ,sticky ="ew",padx =(0 ,5 ))

        size_entry =ctk .CTkEntry (row_frame ,**self .entry_style )
        size_entry .insert (0 ,str (size ))
        size_entry .grid (row =0 ,column =1 ,sticky ="ew",padx =5 )

        remove_btn =ctk .CTkButton (
        row_frame ,text ="X",width =28 ,height =28 ,
        fg_color ="#D00000",hover_color ="#FF0000",text_color ="white"
        )
        remove_btn .configure (command =lambda f =row_frame :self ._remove_file_row (f ))
        remove_btn .grid (row =0 ,column =2 ,padx =(5 ,0 ))
        self .manual_file_rows .append ((row_frame ,name_entry ,size_entry ))

    def _remove_file_row (self ,row_frame :ctk .CTkFrame ):
        row_to_remove =None 
        for row_tuple in self .manual_file_rows :
            if row_tuple [0 ]==row_frame :
                row_to_remove =row_tuple 
                break 
        if row_to_remove :
            self .manual_file_rows .remove (row_to_remove )
        row_frame .destroy ()

    def _clear_file_rows (self ):
        while self .manual_file_rows :
            row_tuple =self .manual_file_rows .pop ()
            row_tuple [0 ].destroy ()

    def _import_files (self ):
        filepath =filedialog .askopenfilename (
        title ="Importar Archivos Manuales",
        filetypes =[("JSON/CSV","*.json *.csv"),("Todos","*.*")]
        )
        if not filepath :
            return 
        try :
            self ._clear_file_rows ()
            user_files =[]
            if filepath .endswith (".json"):
                with open (filepath ,"r",encoding ="utf-8")as f :
                    data =json .load (f )
                    if not isinstance (data ,list ):
                        raise ValueError ("El JSON debe ser una *lista* de objetos.")
                    for item in data :
                        user_files .append ({
                        "name":str (item ["name"]),
                        "size_blocks":int (item ["size_blocks"])
                        })
            elif filepath .endswith (".csv"):
                with open (filepath ,"r",encoding ="utf-8")as f :
                    reader =csv .DictReader (f )
                    for row in reader :
                        user_files .append ({
                        "name":str (row ["name"]),
                        "size_blocks":int (row ["size_blocks"])
                        })
            else :
                raise ValueError ("Archivo debe ser .json o .csv")
            for f in user_files :
                self ._add_file_row (f ["name"],f ["size_blocks"])
            self .status_label .configure (text =f"Éxito: Se importaron {len (user_files )} archivos.",text_color =self .palette ["text_light"])
        except Exception as e :
            print (f"Error al importar: {e }")
            self .status_label .configure (text =f"Error al importar: {e }",text_color ="#FF5555")

    def _collect_manual_files (self )->Optional [List [Dict [str ,Any ]]]:
        user_files =[]
        for i ,(row_frame ,name_entry ,size_entry )in enumerate (self .manual_file_rows ):
            name =name_entry .get ().strip ()
            size_str =size_entry .get ().strip ()
            if not name or not size_str :
                self .status_label .configure (text =f"Error: Fila {i +1 } está incompleta.",text_color ="#FF5555")
                return None 
            try :
                size =int (size_str )
                if size <=0 :
                    raise ValueError ()
                user_files .append ({"name":name ,"size_blocks":size })
            except ValueError :
                self .status_label .configure (text =f"Error: Fila {i +1 }, el tamaño '{size_str }' debe ser un número > 0.",text_color ="#FF5555")
                return None 
        return user_files 


    def _start_simulation (self ):
        self .run_button .configure (state ="disabled",text ="Ejecutando...")
        self .status_label .configure (text ="Iniciando simulación...",text_color =self .palette ["text_light"])
        if self .on_run_start :
            self .on_run_start ()
        strategy_display =self .strategy_var .get ()
        scenario_display =self .scenario_var .get ()
        strategy_key =STRATEGY_MAP_EN .get (strategy_display )
        scenario_key =SCENARIO_MAP_EN .get (scenario_display )
        if strategy_key is None or scenario_key is None :
            self .after (0 ,self ._simulation_error ,Exception (f"Clave no encontrada para '{strategy_display }' o '{scenario_display }'"))
            return 
        slowdown_val =5 if self .slow_mo_var .get ()else 0 
        mode =self .workload_mode_var .get ()
        user_files_list :Optional [List [Dict [str ,Any ]]]=None 
        respect_only_flag :bool =False 
        seed_val :Optional [int ]=None 
        if mode =="Manual (Lista)":
            user_files_list =self ._collect_manual_files ()
            if user_files_list is None :
                self .run_button .configure (state ="normal",text ="Ejecutar Simulación")
                return 
            respect_only_flag =self .respect_only_var .get ()
        else :
            seed_str =self .seed_entry .get ().strip ()
            if seed_str .isdigit ():
                seed_val =int (seed_str )
        thread =threading .Thread (
        target =self ._run_simulation_thread ,
        args =(
        strategy_key ,
        scenario_key ,
        slowdown_val ,
        user_files_list ,
        respect_only_flag ,
        seed_val 
        ),
        daemon =True 
        )
        thread .start ()

    def _run_simulation_thread (
    self ,
    strategy_key :str ,
    scenario_key :str ,
    slowdown_val :int ,
    user_files_list :Optional [List [Dict [str ,Any ]]],
    respect_only_flag :bool ,
    seed_val :Optional [int ]
    ):
        try :
            results ,bitmaps =run_simulation (
            strategy_name =strategy_key ,
            scenario =scenario_key ,
            scenarios_path ="data/scenarios.json",
            seed =seed_val ,
            overrides ={},
            out =None ,
            on_bitmap_update =self .on_live_update ,
            ui_slowdown_ms =slowdown_val ,
            user_files =user_files_list ,
            respect_user_files_only =respect_only_flag 
            )
            self .after (0 ,self ._simulation_complete ,results ,bitmaps )
        except Exception as e :
            print (f"Error en el hilo de simulación: {e }")
            self .after (0 ,self ._simulation_error ,e )

    def _simulation_complete (self ,results :Dict [str ,Any ],bitmaps :Optional [Dict [str ,List [int ]]]):
        strategy_display =self .strategy_var .get ()
        self .status_label .configure (text =f"Simulación completada. Resultados para '{strategy_display }'.",text_color =self .palette ["text_light"])
        self .run_button .configure (state ="normal",text ="Ejecutar Simulación")
        if self .on_run_complete :
            self .on_run_complete (results ,bitmaps )

    def _simulation_error (self ,error :Exception ):
        self .status_label .configure (text =f"Error: {error }",text_color ="#FF5555")
        self .run_button .configure (state ="normal",text ="Ejecutar Simulación")
        if self .on_run_complete :
            self .on_run_complete ({"error":str (error )},None )
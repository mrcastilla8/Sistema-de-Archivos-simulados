
import customtkinter as ctk 
from tkinter import ttk 
import tkinter as tk 
from customtkinter import filedialog 
import csv 
import json 
from typing import Dict ,Any ,List ,Optional 


METRIC_NAMES_ES ={
"avg_access_time_ms":"Tiempo Promedio de Acceso (ms)","space_usage_pct":"Uso de Espacio (%)",
"fragmentation_internal_pct":"Fragmentación Interna (%)","fragmentation_external_pct":"Fragmentación Externa (%)",
"throughput_ops_per_sec":"Operaciones por Segundo (OPS)","hit_miss_ratio":"Tasa de Aciertos (%)",
"cpu_usage_pct":"Uso de CPU (%)","fairness_index":"Índice de Equidad (Desv. Tiempos)",
"elapsed_ms_total":"Tiempo Total de Simulación (ms)","ops_count":"Total de Operaciones Ejecutadas",
"seeks_total_est":"Total de Saltos de Cabezal (Est.)","cpu_time_total_s":"Tiempo Total de CPU (s)"
}
METRIC_ORDER =[
"avg_access_time_ms","throughput_ops_per_sec","seeks_total_est","space_usage_pct",
"fragmentation_external_pct","fragmentation_internal_pct","hit_miss_ratio","fairness_index",
"cpu_usage_pct","elapsed_ms_total","ops_count","cpu_time_total_s",
]
KEYS_TO_IGNORE =["_basic","_scenario","_seed","files_manifest","op_traces"]
MANIFEST_COLUMNS ={"name":"Nombre Archivo","size_blocks":"Tamaño (Bloques)","alive":"Estado","read_ops":"Lecturas","write_ops":"Escrituras"}

class ResultsView (ctk .CTkFrame ):
    """
    Vista para mostrar los resultados de la simulación...
    """
    def __init__ (self ,master ,palette :Dict [str ,str ],**kwargs ):
        super ().__init__ (master ,**kwargs )
        self .palette =palette 
        self .configure (fg_color ="transparent")
        self .grid_columnconfigure (0 ,weight =1 )
        self .grid_rowconfigure (1 ,weight =1 );self .grid_rowconfigure (3 ,weight =2 )


        self .title_label =ctk .CTkLabel (self ,text ="Resultados de la Simulación",font =ctk .CTkFont (size =20 ,weight ="bold"),text_color =self .palette ["text_light"])
        self .title_label .grid (row =0 ,column =0 ,padx =20 ,pady =(0 ,10 ),sticky ="w")
        self .metrics_scroll_frame =ctk .CTkScrollableFrame (self ,fg_color ="transparent")
        self .metrics_scroll_frame .grid (row =1 ,column =0 ,sticky ="nsew",padx =0 ,pady =0 )
        self .metrics_scroll_frame .grid_columnconfigure (0 ,weight =1 )
        self .metrics_current_row =0 
        self .manifest_title_frame =ctk .CTkFrame (self ,fg_color ="transparent")
        self .manifest_title_frame .grid (row =2 ,column =0 ,sticky ="ew",padx =20 ,pady =(15 ,5 ))
        self .manifest_title_frame .grid_columnconfigure (0 ,weight =1 )
        self .manifest_label =ctk .CTkLabel (self .manifest_title_frame ,text ="Manifiesto de Archivos",font =ctk .CTkFont (size =18 ,weight ="bold"),text_color =self .palette ["text_light"])
        self .manifest_label .grid (row =0 ,column =0 ,sticky ="w")
        export_buttons_frame =ctk .CTkFrame (self .manifest_title_frame ,fg_color ="transparent")
        export_buttons_frame .grid (row =0 ,column =1 ,sticky ="e")


        button_style_export ={"fg_color":self .palette ["button"],"hover_color":self .palette ["button_hover"],"text_color":self .palette ["text_on_button"],"width":220 }



        self .export_json_button =ctk .CTkButton (export_buttons_frame ,text ="Exportar resultados (JSON)",command =self ._export_results_json ,state ="disabled",**button_style_export )
        self .export_json_button .pack (side ="right",padx =(5 ,0 ))



        self .export_csv_button =ctk .CTkButton (export_buttons_frame ,text ="Exportar manifiesto (CSV)",command =self ._export_manifest_csv ,state ="disabled",**button_style_export )
        self .export_csv_button .pack (side ="right")


        self .table_frame =ctk .CTkFrame (self ,fg_color =self .palette ["app_bg"])
        self .table_frame .grid (row =3 ,column =0 ,sticky ="nsew",padx =10 ,pady =10 )
        self .table_frame .grid_rowconfigure (0 ,weight =1 );self .table_frame .grid_columnconfigure (0 ,weight =1 )

        style =ttk .Style ();style .theme_use ("clam");style .configure ("Treeview",background =self .palette ["app_bg"],foreground =self .palette ["text_light"],fieldbackground =self .palette ["app_bg"],rowheight =25 ,bordercolor =self .palette ["button"],borderwidth =1 );style .map ('Treeview',background =[('selected',self .palette ["button"])],foreground =[('selected',self .palette ["text_on_button"])]);style .configure ("Treeview.Heading",background =self .palette ["button"],foreground =self .palette ["text_on_button"],relief ="flat",font =('Arial',10 ,'bold'));style .map ("Treeview.Heading",background =[('active',self .palette ["button_hover"])])
        self .tree =ttk .Treeview (self .table_frame ,columns =list (MANIFEST_COLUMNS .keys ()),show ="headings")
        for key ,header_text in MANIFEST_COLUMNS .items ():
            anchor =tk .W ;width =100 ;stretch =tk .NO 
            if key =="name":width =250 ;stretch =tk .YES 
            elif key =="size_blocks":width =120 ;anchor =tk .E 
            elif key =="alive":width =80 ;anchor =tk .CENTER 
            elif key =="read_ops"or key =="write_ops":width =80 ;anchor =tk .E 
            self .tree .heading (key ,text =header_text ,anchor =anchor )
            self .tree .column (key ,anchor =anchor ,width =width ,stretch =stretch )
        vsb =ttk .Scrollbar (self .table_frame ,orient ="vertical",command =self .tree .yview );hsb =ttk .Scrollbar (self .table_frame ,orient ="horizontal",command =self .tree .xview );self .tree .configure (yscrollcommand =vsb .set ,xscrollcommand =hsb .set );self .tree .grid (row =0 ,column =0 ,sticky ="nsew");vsb .grid (row =0 ,column =1 ,sticky ="ns");hsb .grid (row =1 ,column =0 ,sticky ="ew")

        self ._current_manifest_data :List [Dict [str ,Any ]]=[]
        self ._current_summaries_data :Optional [Dict [str ,Any ]]=None 
        self ._show_placeholder ()




    def _clear_results (self ):
        """Limpia métricas, tabla y deshabilita botones."""



        for widget in list (self .metrics_scroll_frame .winfo_children ()):
            widget .destroy ()
        self .metrics_current_row =0 



        for item in self .tree .get_children ():
            self .tree .delete (item )


        self ._current_manifest_data =[]
        self ._current_summaries_data =None 


        self .export_csv_button .configure (state ="disabled")
        self .export_json_button .configure (state ="disabled")


    def _show_placeholder (self ):
        """Muestra el mensaje inicial."""
        self ._clear_results ()
        label =ctk .CTkLabel (self .metrics_scroll_frame ,text ="Ejecuta una simulación...",text_color =self .palette ["text_light"])
        label .grid (row =self .metrics_current_row ,column =0 ,padx =20 ,pady =20 )
        self .metrics_current_row +=1 
        self .manifest_label .configure (text ="Manifiesto de Archivos")

    def _show_error (self ,error_msg :str ):
        """Muestra un mensaje de error estilizado."""
        self ._clear_results ()
        label =ctk .CTkLabel (self .metrics_scroll_frame ,text ="Error en la Simulación:",text_color ="#FF5555",font =ctk .CTkFont (size =16 ,weight ="bold"))
        label .grid (row =self .metrics_current_row ,column =0 ,padx =20 ,pady =(10 ,5 ),sticky ="w")
        self .metrics_current_row +=1 
        error_text =ctk .CTkTextbox (self .metrics_scroll_frame ,activate_scrollbars =False ,text_color =self .palette ["text_light"])
        error_text .insert ("0.0",error_msg )
        error_text .configure (state ="disabled",fg_color ="transparent",font =ctk .CTkFont (family ="monospace"))
        error_text .configure (height =len (error_msg .split ('\n'))*20 +20 )
        error_text .grid (row =self .metrics_current_row ,column =0 ,padx =20 ,pady =(0 ,20 ),sticky ="ew")
        self .metrics_current_row +=1 
        self .manifest_label .configure (text ="Manifiesto de Archivos (No disponible)")

    def _add_metric_row (self ,master_frame ,key :str ,value :Any ):
        """Añade una fila de métrica (Nombre: Valor) al frame de métricas."""

        display_name =METRIC_NAMES_ES .get (key ,key );
        if isinstance (value ,float ):display_value =f"{value :.3f}"
        else :display_value =str (value )
        row_frame =ctk .CTkFrame (master_frame ,fg_color ="transparent");row_frame .pack (fill ="x",padx =10 ,pady =1 );row_frame .grid_columnconfigure (0 ,weight =1 );row_frame .grid_columnconfigure (1 ,weight =1 )
        name_label =ctk .CTkLabel (row_frame ,text =f"{display_name }:",anchor ="w",text_color =self .palette ["text_light"]);name_label .grid (row =0 ,column =0 ,sticky ="w")
        value_label =ctk .CTkLabel (row_frame ,text =display_value ,anchor ="e",text_color =self .palette ["text_light"],font =ctk .CTkFont (weight ="bold"));value_label .grid (row =0 ,column =1 ,sticky ="e")


    def _add_strategy_card (self ,strategy_name :str ,metrics :Dict [str ,Any ]):
        """Añade una "tarjeta" de métricas agregadas."""

        title_label =ctk .CTkLabel (self .metrics_scroll_frame ,text =f"Estrategia: {strategy_name .upper ()}",font =ctk .CTkFont (size =18 ,weight ="bold"),text_color =self .palette ["text_light"]);title_label .grid (row =self .metrics_current_row ,column =0 ,padx =5 ,pady =(20 ,10 ),sticky ="w");self .metrics_current_row +=1 
        card_frame =ctk .CTkFrame (self .metrics_scroll_frame ,border_width =1 ,border_color =self .palette ["button_hover"],fg_color =self .palette ["app_bg"]);card_frame .grid (row =self .metrics_current_row ,column =0 ,sticky ="ew",padx =5 ,pady =5 );self .metrics_current_row +=1 
        for key in METRIC_ORDER :
            if key in metrics and key not in KEYS_TO_IGNORE :self ._add_metric_row (card_frame ,key ,metrics [key ])
        for key ,value in metrics .items ():
            if key not in METRIC_ORDER and key not in KEYS_TO_IGNORE :self ._add_metric_row (card_frame ,key ,value )
        ctk .CTkFrame (card_frame ,height =10 ,fg_color ="transparent").pack ()


    def _populate_manifest_table (self ,manifest_data :List [Dict [str ,Any ]]):
        """Llena la tabla Treeview con los datos del manifiesto."""


        for item in self .tree .get_children ():
            self .tree .delete (item )
        self ._current_manifest_data =manifest_data 

        for i ,file_info in enumerate (manifest_data ):
            values =[];tag ='even'if i %2 ==0 else 'odd'
            for key in MANIFEST_COLUMNS .keys ():
                value =file_info .get (key ,"-")
                if key =="alive":value ="Vivo"if value else "Borrado"
                values .append (value )
            self .tree .insert ("",tk .END ,values =values ,tags =(tag ,))

        self .export_csv_button .configure (state ="normal"if manifest_data else "disabled")

    def _export_manifest_csv (self ):
        """Exporta los datos del manifiesto actual a un archivo CSV."""

        if not self ._current_manifest_data :return 
        filepath =filedialog .asksaveasfilename (title ="Guardar Manifiesto como CSV",defaultextension =".csv",filetypes =[("CSV","*.csv"),("Todos","*.*")])
        if not filepath :return 
        try :
            headers =list (MANIFEST_COLUMNS .keys ())
            with open (filepath ,"w",newline ="",encoding ="utf-8")as f :
                writer =csv .DictWriter (f ,fieldnames =headers )
                writer .writerow (MANIFEST_COLUMNS )
                for file_info in self ._current_manifest_data :
                    row_to_write ={h :file_info .get (h ,"")for h in headers }
                    if 'alive'in row_to_write :row_to_write ['alive']="Vivo"if row_to_write ['alive']else "Borrado"
                    writer .writerow (row_to_write )
            print (f"Manifiesto exportado a {filepath }")
        except Exception as e :print (f"Error al exportar CSV: {e }")


    def _export_results_json (self ):
        """Exporta los datos de summaries (SOLO MÉTRICAS) a un archivo JSON."""
        if not self ._current_summaries_data :
            print ("No hay datos de resultados para exportar.")

            return 

        filepath =filedialog .asksaveasfilename (
        title ="Guardar Resumen de Métricas como JSON",
        defaultextension =".json",
        filetypes =[("JSON","*.json"),("Todos","*.*")]
        )
        if not filepath :
            return 

        try :

            filtered_summaries ={}


            for strategy ,metrics in self ._current_summaries_data .items ():

                filtered_metrics ={}

                for key ,value in metrics .items ():


                    if key not in KEYS_TO_IGNORE and not isinstance (value ,list ):
                        filtered_metrics [key ]=value 


                if filtered_metrics :
                    filtered_summaries [strategy ]=filtered_metrics 


            if not filtered_summaries :
                 print ("No hay métricas resumidas para exportar después del filtrado.")

                 return 


            with open (filepath ,"w",encoding ="utf-8")as f :
                json .dump (filtered_summaries ,f ,indent =2 )

            print (f"Resumen de métricas exportado exitosamente a {filepath }")


        except Exception as e :
            print (f"Error al exportar JSON: {e }")




    def show_results (self ,summaries :Optional [Dict [str ,Any ]]):
        """
        Punto de entrada principal. Muestra métricas, llena tabla y guarda summaries.
        """

        self ._clear_results ()
        self ._current_summaries_data =summaries 


        if summaries is None :
            self ._show_placeholder ()
            return 
        if "error"in summaries :
            self ._show_error (summaries ["error"])
            return 
        if not summaries :
            self ._show_placeholder ()
            return 


        first_manifest =None 
        found_valid_strategy =False 
        for strategy_name ,metrics in summaries .items ():

            if strategy_name .startswith ("_"):
                continue 


            self ._add_strategy_card (strategy_name ,metrics )
            found_valid_strategy =True 


            if first_manifest is None and "files_manifest"in metrics :
                 potential_manifest =metrics .get ("files_manifest")

                 if isinstance (potential_manifest ,list ):
                      first_manifest =potential_manifest 


        if isinstance (first_manifest ,list ):
            self ._populate_manifest_table (first_manifest )
            self .manifest_label .configure (text =f"Manifiesto de Archivos ({len (first_manifest )} total)")
        else :
            self ._populate_manifest_table ([])
            self .manifest_label .configure (text ="Manifiesto de Archivos (No disponible)")


        can_export_csv =bool (self ._current_manifest_data )
        can_export_json =found_valid_strategy 
        self .export_csv_button .configure (state ="normal"if can_export_csv else "disabled")
        self .export_json_button .configure (state ="normal"if can_export_json else "disabled")

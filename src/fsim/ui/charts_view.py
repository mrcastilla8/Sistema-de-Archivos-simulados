
import customtkinter as ctk 
from tkinter import ttk 
import tkinter as tk 
from typing import Dict ,Any ,List ,Optional 
import matplotlib .pyplot as plt 
from matplotlib .figure import Figure 
from matplotlib .backends .backend_tkagg import FigureCanvasTkAgg ,NavigationToolbar2Tk 
import numpy as np 

class SpanishNavigationToolbar (NavigationToolbar2Tk ):


    toolitems =(
    ('Home','Resetear vista original','home','home'),
    ('Back','Volver a vista previa','back','back'),
    ('Forward','Siguiente vista','forward','forward'),
    (None ,None ,None ,None ),
    ('Pan','Mover arrastrando','move','pan'),
    ('Zoom','Zoom a región','zoom_to_rect','zoom'),
    ('Subplots','Configurar subplots','subplots','configure_subplots'),
    (None ,None ,None ,None ),
    ('Save','Guardar figura','filesave','save_figure'),
    )

    def set_message (self ,msg ):

        translations ={
        'Mouse position: ':'Posición del mouse: ',
        'Navigation: ':'Navegación: ',
        'Left button: ':'Botón izquierdo: ',
        'Right button: ':'Botón derecho: ',
        'Middle button: ':'Botón central: ',
        'Pan axes':'Mover ejes',
        'Zoom to rectangle':'Zoom a rectángulo',
        'Press left button to zoom':'Click izquierdo para hacer zoom',
        'Reset original view':'Restaurar vista original',
        'Save the figure':'Guardar la figura',
        'Configure subplots':'Configurar subplots'
        }

        for en ,es in translations .items ():
            if msg .startswith (en ):
                msg =msg .replace (en ,es )
                break 

        super ().set_message (msg )

STRATEGY_NAMES_ES ={
"contiguous":"Asignación Contigua",
"linked":"Asignación Enlazada",
"indexed":"Asignación Indexada",

}


plt .style .use ('dark_background')


TIMESERIES_PLOTS ={
"access_time_ms":"Tiempo Acceso (ms)",
"external_frag_pct":"Frag. Externa (%)",
"space_usage_pct":"Uso Espacio (%)",

}


THROUGHPUT_WINDOWS =[20 ,50 ,100 ]

class ChartsView (ctk .CTkFrame ):
    def __init__ (self ,master ,palette :Dict [str ,str ],**kwargs ):
        super ().__init__ (master ,**kwargs )
        self .palette =palette 
        self .configure (fg_color ="transparent")

        self ._summaries_data :Optional [Dict [str ,Any ]]=None 
        self ._strategy_keys :List [str ]=[]
        self ._current_strategy :str =""
        self ._current_traces :List [Dict [str ,Any ]]=[]

        self .grid_columnconfigure (0 ,weight =1 )
        self .grid_rowconfigure (1 ,weight =1 )


        controls_frame =ctk .CTkFrame (self ,fg_color ="transparent")
        controls_frame .grid (row =0 ,column =0 ,sticky ="ew",padx =10 ,pady =(0 ,10 ))
        controls_frame .grid_columnconfigure (1 ,weight =1 )


        ctk .CTkLabel (controls_frame ,text ="Seleccionar Estrategia:",text_color =self .palette ["text_light"]).grid (row =0 ,column =0 ,padx =(0 ,10 ),sticky ="w")
        self .strategy_var =ctk .StringVar (value ="Ninguna")
        self .strategy_combo =ctk .CTkComboBox (
        controls_frame ,variable =self .strategy_var ,values =["Ninguna"],
        state ="disabled",command =self ._on_strategy_change ,
        text_color =self .palette ["text_on_button"],
        fg_color =self .palette ["button"],
        button_color =self .palette ["button"],
        border_color =self .palette ["button"],
        dropdown_fg_color =self .palette ["frame_bg"],
        dropdown_hover_color =self .palette ["button_hover"],
        dropdown_text_color =self .palette ["text_light"]
        )
        self .strategy_combo .grid (row =0 ,column =1 ,sticky ="ew")


        ctk .CTkLabel (controls_frame ,text ="Ventana Throughput (ops):",text_color =self .palette ["text_light"]).grid (row =0 ,column =2 ,padx =(20 ,10 ),sticky ="w")
        self .throughput_win_var =ctk .StringVar (value =str (THROUGHPUT_WINDOWS [1 ]))
        self .throughput_win_combo =ctk .CTkComboBox (
        controls_frame ,variable =self .throughput_win_var ,values =[str (w )for w in THROUGHPUT_WINDOWS ],
        state ="disabled",command =self ._redraw_charts ,width =80 ,
        text_color =self .palette ["text_on_button"],
        fg_color =self .palette ["button"],
        button_color =self .palette ["button"],
        border_color =self .palette ["button"],
        dropdown_fg_color =self .palette ["frame_bg"],
        dropdown_hover_color =self .palette ["button_hover"],
        dropdown_text_color =self .palette ["text_light"]
        )
        self .throughput_win_combo .grid (row =0 ,column =3 ,sticky ="w")


        self .tab_view =ctk .CTkTabview (self ,
        fg_color =self .palette ["frame_bg"],
        segmented_button_selected_color =self .palette ["button"],
        segmented_button_selected_hover_color =self .palette ["button_hover"],
        segmented_button_unselected_color =self .palette ["frame_bg"],
        text_color =self .palette ["text_light"]
        )
        self .tab_view .grid (row =1 ,column =0 ,sticky ="nsew",padx =10 ,pady =10 )



        self ._chart_widgets :Dict [str ,Any ]={}
        self ._create_placeholder_tab ("Esperando datos...")

    def _create_placeholder_tab (self ,text :str ):

        try :
            tab =self .tab_view .add ("Info")
            tab .grid_columnconfigure (0 ,weight =1 );tab .grid_rowconfigure (0 ,weight =1 )
            label =ctk .CTkLabel (tab ,text =text ,text_color =self .palette ["text_light"],font =ctk .CTkFont (size =16 ))
            label .grid (row =0 ,column =0 ,padx =20 ,pady =20 )
        except Exception as e :
            print (f"Error creating placeholder tab: {e }")

    def _clear_tabs (self ):


        tab_names =list (self .tab_view ._name_list )
        for name in tab_names :
            try :
                self .tab_view .delete (name )
            except Exception as e :
                print (f"Error deleting tab '{name }': {e }")

        for widget_set in self ._chart_widgets .values ():
            if widget_set .get ('canvas_widget'):
                widget_set ['canvas_widget'].destroy ()
            if widget_set .get ('toolbar_widget'):
                 widget_set ['toolbar_widget'].destroy ()
            if widget_set .get ('fig'):
                 plt .close (widget_set ['fig'])
        self ._chart_widgets ={}


    def _create_chart_tabs (self ):

        self ._clear_tabs ()
        if not self ._current_traces :
            self ._create_placeholder_tab ("No hay datos de traza para esta estrategia.")
            return 

        plot_keys =[
        "access_time_ms",
        "external_frag_pct",
        "space_usage_pct",
        "cumulative_seeks",
        "throughput",
        "latency_vs_throughput"
        ]

        for key in plot_keys :

            tab_name ={
            "access_time_ms":"Tiempo de Acceso",
            "external_frag_pct":"Fragmentación Externa",
            "space_usage_pct":"Uso de Espacio",
            "cumulative_seeks":"Búsquedas Acumuladas",
            "throughput":"Throughput",
            "latency_vs_throughput":"Latencia vs Throughput"
            }.get (key ,key .replace ("_"," ").title ())

            try :
                tab =self .tab_view .add (tab_name )
                tab .grid_columnconfigure (0 ,weight =1 );tab .grid_rowconfigure (0 ,weight =1 )

                fig =Figure (figsize =(8 ,4 ),dpi =100 ,facecolor =self .palette ["frame_bg"])
                ax =fig .add_subplot (111 )
                ax .set_facecolor (self .palette ["app_bg"])
                ax .tick_params (axis ='x',colors =self .palette ["text_light"])
                ax .tick_params (axis ='y',colors =self .palette ["text_light"])
                ax .spines ['bottom'].set_color (self .palette ["text_light"])
                ax .spines ['left'].set_color (self .palette ["text_light"])
                ax .spines ['top'].set_color (self .palette ["frame_bg"])
                ax .spines ['right'].set_color (self .palette ["frame_bg"])
                fig .subplots_adjust (left =0.1 ,right =0.95 ,top =0.9 ,bottom =0.15 )

                canvas =FigureCanvasTkAgg (fig ,master =tab )
                canvas_widget =canvas .get_tk_widget ()
                canvas_widget .pack (side =tk .TOP ,fill =tk .BOTH ,expand =True )

                toolbar_frame =ctk .CTkFrame (tab ,fg_color ="transparent")
                toolbar_frame .pack (side =tk .BOTTOM ,fill =tk .X )
                toolbar =SpanishNavigationToolbar (canvas ,toolbar_frame ,pack_toolbar =False )


                toolbar .configure (background =self .palette ["frame_bg"])

                try :
                    toolbar ._message_label .config (background =self .palette ["frame_bg"],fg =self .palette ["text_light"])
                except AttributeError :
                    pass 


                for item in toolbar .winfo_children ():
                    if isinstance (item ,(tk .Button ,tk .Checkbutton ,tk .Radiobutton )):
                         try :
                              item .config (
                              background =self .palette ["button"],
                              foreground =self .palette ["text_on_button"],
                              activebackground =self .palette ["button_hover"],
                              activeforeground =self .palette ["text_on_button"],
                              relief =tk .FLAT ,
                              bd =0 
                              )
                         except tk .TclError as e :


                              pass 
                    elif isinstance (item ,tk .Frame ):
                        item .config (background =self .palette ["frame_bg"])


                toolbar .pack (side =tk .LEFT ,padx =10 )

                self ._chart_widgets [key ]={'fig':fig ,'ax':ax ,'canvas':canvas ,'canvas_widget':canvas_widget ,'toolbar':toolbar ,'toolbar_frame':toolbar_frame }

            except Exception as e :
                print (f"Error creating tab/chart for '{key }': {e }")
                try :
                    error_tab =self .tab_view .add (f"{tab_name } Error")
                    ctk .CTkLabel (error_tab ,text =f"Error al crear gráfico:\n{e }",text_color ="red").pack (padx =10 ,pady =10 )
                except :pass 

        if self .tab_view ._name_list :
             self .tab_view .set (self .tab_view ._name_list [0 ])


    def _plot_timeseries (self ,key :str ,ax :plt .Axes ,canvas :FigureCanvasTkAgg ):
        y_label =TIMESERIES_PLOTS .get (key ,key )
        x_data =[t .get ("op_index",i )for i ,t in enumerate (self ._current_traces )]
        y_data =[t .get (key ,0 )for t in self ._current_traces ]


        step =1 
        if len (x_data )>2000 :
            step =len (x_data )//1000 

        ax .clear ()
        ax .plot (x_data [::step ],y_data [::step ],color =self .palette ["button_hover"],linewidth =1.5 )
        ax .set_title (y_label ,color =self .palette ["text_light"])
        ax .set_xlabel ("Índice de Operación",color =self .palette ["text_light"])
        ax .set_ylabel (y_label ,color =self .palette ["text_light"])
        ax .grid (True ,linestyle ='--',alpha =0.3 ,color =self .palette ["text_light"])
        canvas .draw ()

    def _plot_cumulative_seeks (self ,ax :plt .Axes ,canvas :FigureCanvasTkAgg ):
        x_data =[t .get ("op_index",i )for i ,t in enumerate (self ._current_traces )]
        y_data_raw =[t .get ("seeks_est",0 )for t in self ._current_traces ]
        y_data_cumulative =np .cumsum (y_data_raw )

        step =1 
        if len (x_data )>2000 :step =len (x_data )//1000 

        ax .clear ()
        ax .plot (x_data [::step ],y_data_cumulative [::step ],color =self .palette ["button_hover"],linewidth =1.5 )
        ax .set_title ("Seeks Estimados (Acumulado)",color =self .palette ["text_light"])
        ax .set_xlabel ("Índice de Operación",color =self .palette ["text_light"])
        ax .set_ylabel ("Total Seeks",color =self .palette ["text_light"])
        ax .grid (True ,linestyle ='--',alpha =0.3 ,color =self .palette ["text_light"])
        canvas .draw ()

    def _plot_throughput (self ,ax :plt .Axes ,canvas :FigureCanvasTkAgg ):
        try :
            window =int (self .throughput_win_var .get ())
        except :
            window =THROUGHPUT_WINDOWS [1 ]

        x_data =np .array ([t .get ("op_index",i )for i ,t in enumerate (self ._current_traces )])

        time_stamps =np .array ([t .get ("t_wall_from_start_s",0 )for t in self ._current_traces ])
        delta_times =np .diff (time_stamps ,prepend =0 )
        delta_times [delta_times <=0 ]=1e-6 


        instant_throughput =1.0 /delta_times 




        if len (instant_throughput )>=window :
             weights =np .ones (window )/window 
             moving_avg_throughput =np .convolve (instant_throughput ,weights ,mode ='valid')

             x_data_avg =x_data [window -1 :]
        else :
             moving_avg_throughput =[]
             x_data_avg =[]


        step =1 
        if len (x_data_avg )>2000 :step =len (x_data_avg )//1000 

        ax .clear ()
        if len (x_data_avg )>0 :
             ax .plot (x_data_avg [::step ],moving_avg_throughput [::step ],color =self .palette ["button_hover"],linewidth =1.5 )
        else :
             ax .text (0.5 ,0.5 ,"Datos insuficientes para la ventana",ha ='center',va ='center',color =self .palette ["text_light"])

        ax .set_title (f"Throughput (Ops/s, Ventana Móvil={window })",color =self .palette ["text_light"])
        ax .set_xlabel ("Índice de Operación",color =self .palette ["text_light"])
        ax .set_ylabel ("Ops / Segundo",color =self .palette ["text_light"])
        ax .grid (True ,linestyle ='--',alpha =0.3 ,color =self .palette ["text_light"])
        ax .set_ylim (bottom =0 )
        canvas .draw ()

    def _plot_latency_vs_throughput (self ,ax :plt .Axes ,canvas :FigureCanvasTkAgg ):
        try :
            window =int (self .throughput_win_var .get ())
        except :
            window =THROUGHPUT_WINDOWS [1 ]


        latencies =np .array ([t .get ("access_time_ms",0 )for t in self ._current_traces ])
        moving_avg_latency =[]
        if len (latencies )>=window :
            weights =np .ones (window )/window 
            moving_avg_latency =np .convolve (latencies ,weights ,mode ='valid')


        time_stamps =np .array ([t .get ("t_wall_from_start_s",0 )for t in self ._current_traces ])
        delta_times =np .diff (time_stamps ,prepend =0 )
        delta_times [delta_times <=0 ]=1e-6 
        instant_throughput =1.0 /delta_times 
        moving_avg_throughput =[]
        if len (instant_throughput )>=window :
             weights =np .ones (window )/window 
             moving_avg_throughput =np .convolve (instant_throughput ,weights ,mode ='valid')


        min_len =min (len (moving_avg_latency ),len (moving_avg_throughput ))
        scatter_latency =moving_avg_latency [:min_len ]
        scatter_throughput =moving_avg_throughput [:min_len ]

        ax .clear ()
        if min_len >0 :

            ax .scatter (scatter_latency ,scatter_throughput ,color =self .palette ["button_hover"],alpha =0.6 ,s =10 )
        else :
            ax .text (0.5 ,0.5 ,"Datos insuficientes para la ventana",ha ='center',va ='center',color =self .palette ["text_light"])

        ax .set_title (f"Latencia vs Throughput (Ventana={window })",color =self .palette ["text_light"])
        ax .set_xlabel ("Latencia Promedio (ms)",color =self .palette ["text_light"])
        ax .set_ylabel ("Throughput Promedio (Ops/s)",color =self .palette ["text_light"])
        ax .grid (True ,linestyle ='--',alpha =0.3 ,color =self .palette ["text_light"])
        ax .set_xlim (left =0 )
        ax .set_ylim (bottom =0 )
        canvas .draw ()


    def _redraw_charts (self ,*args ):
        if not self ._current_strategy or not self ._summaries_data or not self ._current_traces :

             return 




        for key ,widgets in self ._chart_widgets .items ():
            if key in TIMESERIES_PLOTS :
                self ._plot_timeseries (key ,widgets ['ax'],widgets ['canvas'])


        if "cumulative_seeks"in self ._chart_widgets :
             widgets =self ._chart_widgets ["cumulative_seeks"]
             self ._plot_cumulative_seeks (widgets ['ax'],widgets ['canvas'])


        if "throughput"in self ._chart_widgets :
            widgets =self ._chart_widgets ["throughput"]
            self ._plot_throughput (widgets ['ax'],widgets ['canvas'])


        if "latency_vs_throughput"in self ._chart_widgets :
            widgets =self ._chart_widgets ["latency_vs_throughput"]
            self ._plot_latency_vs_throughput (widgets ['ax'],widgets ['canvas'])


    def _on_strategy_change (self ,selected_strategy_display :str ):
        if not self ._summaries_data :return 


        strategy_key =""

        strategy_map_en ={STRATEGY_NAMES_ES .get (k ,k ):k for k in self ._strategy_keys }
        strategy_key =strategy_map_en .get (selected_strategy_display )

        if strategy_key and strategy_key in self ._summaries_data :
            self ._current_strategy =strategy_key 
            self ._current_traces =self ._summaries_data [strategy_key ].get ("op_traces",[])

            if not self ._chart_widgets :
                 self ._create_chart_tabs ()
            self ._redraw_charts ()
        else :

            self ._current_strategy =""
            self ._current_traces =[]
            self ._clear_tabs ()
            self ._create_placeholder_tab (f"No hay datos para '{selected_strategy_display }'.")


    def update_charts (self ,summaries :Optional [Dict [str ,Any ]]):
        self ._summaries_data =summaries 
        self ._strategy_keys =[]
        self ._current_strategy =""
        self ._current_traces =[]
        self ._clear_tabs ()

        if summaries is None or "error"in summaries or not summaries :
            self .strategy_combo .configure (state ="disabled",values =["Ninguna"])
            self .strategy_var .set ("Ninguna")
            self .throughput_win_combo .configure (state ="disabled")
            error_msg =summaries .get ("error","No se recibieron resultados.")if summaries else "No se recibieron resultados."
            self ._create_placeholder_tab (f"Error en la simulación:\n{error_msg }")
            return 


        valid_strategies =[]
        for strat_key ,data in summaries .items ():
            if not strat_key .startswith ("_")and "op_traces"in data and data ["op_traces"]:
                 self ._strategy_keys .append (strat_key )

                 display_name =STRATEGY_NAMES_ES .get (strat_key ,strat_key )
                 valid_strategies .append (display_name )


        if not valid_strategies :
            self .strategy_combo .configure (state ="disabled",values =["Sin Datos"])
            self .strategy_var .set ("Sin Datos")
            self .throughput_win_combo .configure (state ="disabled")
            self ._create_placeholder_tab ("La simulación no generó trazas de operaciones.")
            return 


        self .strategy_combo .configure (state ="normal",values =valid_strategies )
        self .throughput_win_combo .configure (state ="normal")

        first_strategy_display =valid_strategies [0 ]
        self .strategy_var .set (first_strategy_display )
        self ._on_strategy_change (first_strategy_display )
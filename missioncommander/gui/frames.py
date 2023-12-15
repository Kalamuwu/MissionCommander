import sys

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.scrolledtext

from typing import Dict, Union, Optional, Callable, Tuple, List

from .logger import ScrolledTextLogger

widget_spacing: Dict[str, Union[int, str]] = {
    'padx': 4,
    'pady': 4,
}

class SettingsEntry:
    def __init__(self, root_frame: ttk.Frame, label: str, callback: Callable):
        # internal vars
        self.__root = root_frame
        self.__text = tk.StringVar()
        self.__callback = callback
        # containers for dynamic spacing
        self.__container_frame_1 = ttk.Frame(self.__root,              relief='flat', border=0)
        self.__container_frame_2 = ttk.Frame(self.__container_frame_1, relief='flat', border=0)
        # inner widgets
        self.__label =  ttk.Label( self.__container_frame_1, text=label, width=14)
        self.__entry =  ttk.Entry( self.__container_frame_2, textvariable=self.__text)
        self.__button = ttk.Button(self.__container_frame_2, text="Set", command=self._set, width=6)
    
    def pack_inner(self):
        self.__label.pack( **widget_spacing, side='left',            fill='both')
        self.__button.pack(**widget_spacing, side='right',           fill='both')
        self.__entry.pack( **widget_spacing, side='left',  expand=1, fill='both')
        self.__container_frame_2.pack(       side='right', expand=1, fill='both')
        self.__container_frame_1.pack(                     expand=1, fill='both')
    
    def _set(self):
        self.__callback(self.__text.get())

    @property
    def label(self) -> ttk.Label:
        return self.__label

    @property
    def entry(self) -> ttk.Entry:
        return self.__entry

    @property
    def button(self) -> ttk.Button:
        return self.__button

def make_settings_frame(master: ttk.Frame, entries: Dict[str, Callable]) -> Tuple[ttk.Frame, List[SettingsEntry]]:
    settings_frame = ttk.Labelframe(master, labelwidget=ttk.Label(text="Settings"))
    entry_widgets = []
    for field_name,callback in entries.items():
        widget = SettingsEntry(settings_frame, field_name, callback)
        widget.pack_inner()
        entry_widgets.append(widget)
    return settings_frame, entry_widgets


def make_log_frame(master: tk.Frame) -> Tuple[ttk.Labelframe, ScrolledTextLogger]:
    log_frame = ttk.Labelframe(master, labelwidget=ttk.Label(text="Logbook"))
    log_text = tk.scrolledtext.ScrolledText(log_frame)
    log_text.pack(expand=1, fill='both')
    logger = ScrolledTextLogger(log_text)
    return (log_frame, logger)


class InputFrame:
    def __init__(self, root_frame: ttk.Frame, callback: Callable):
        # internal vars
        self.__root = root_frame
        self.__text = tk.StringVar()
        self.__callback = callback
        # inner widgets
        self.__entry =  ttk.Entry( self.__root, textvariable=self.__text)
        self.__button = ttk.Button(self.__root, text="Send", command=self._set, width=6)
    
    def _set(self):
        self.__callback(self.__text.get())

    @property
    def entry(self) -> ttk.Entry:
        return self.__entry

    @property
    def button(self) -> ttk.Button:
        return self.__button

def make_message_input_frame(master: tk.Frame, callback: Callable) -> ttk.Labelframe:
    msg_frame = ttk.Labelframe(master, labelwidget=ttk.Label(text="Message"))
    msger = InputFrame(msg_frame, callback)
    msger.button.pack(**widget_spacing, side='right',           fill='both')
    msger.entry.pack( **widget_spacing, side='left',  expand=1, fill='both')
    return msg_frame


def make_connection_frame(
    master: tk.Frame, status_var: tk.StringVar,
    add_connect_disconnect: bool,
    start_callback: Callable, stop_callback: Callable,
    connect_callback: Callable, disconnect_callback: Callable
) -> Tuple[ttk.Labelframe, ttk.Label]:
    """
    _______________________________connection_frame________________________________
    |                                                                             |
    |                        ____________________btn_frame_____________________   |
    |                       |                                                  |  |
    |   __status_label__    |   ___left_frame___    ______right_frame_______   |  |
    |  |                |   |  |                |  |                        |  |  |
    |  |  [status_var]  |   |  | [start] [stop] |  | [connect] [disconnect] |  |  |
    |  |________________|   |  |________________|  |________________________|  |  |
    |                       |                                                  |  |
    |                       |__________________________________________________|  |
    |                                                                             |
    |_____________________________________________________________________________|
    
    """
    
    # frames
    connection_frame = ttk.Labelframe(master, labelwidget=ttk.Label(text="Connection"))
    btn_frame =     ttk.Frame(connection_frame, relief='flat', border=0)
    right_frame =   ttk.Frame(btn_frame,        relief='flat', border=0)
    left_frame =    ttk.Frame(btn_frame,        relief='flat', border=0)
    # connection status label
    status_label = ttk.Label(connection_frame, textvariable=status_var)
    # buttons
    start_button =      ttk.Button(left_frame,  text='Start',      command=start_callback,      width=5)
    stop_button =       ttk.Button(left_frame,  text='Stop',       command=stop_callback,       width=5)
    connect_button =    ttk.Button(right_frame, text='Connect',    command=connect_callback,    width=8)  if add_connect_disconnect else None
    disconnect_button = ttk.Button(right_frame, text='Disconnect', command=disconnect_callback, width=10) if add_connect_disconnect else None
    # button packs
    start_button.pack(     **widget_spacing, fill='both', side='left')
    stop_button.pack(      **widget_spacing, fill='both', side='right')
    connect_button.pack(   **widget_spacing, fill='both', side='left')  if add_connect_disconnect else "no-op"
    disconnect_button.pack(**widget_spacing, fill='both', side='right') if add_connect_disconnect else "no-op"
    # frame packs
    left_frame.pack(                         fill='both', side='left')
    right_frame.pack(                        fill='both', side='right')
    # top level packs and return
    btn_frame.pack(                          fill='both', side='right')
    status_label.pack(     **widget_spacing, fill='both', side='left', expand=1)
    return (connection_frame, status_label)


def make_client_connection_frame(
    master: tk.Frame,
    status_var: tk.StringVar,
    server_address_var: tk.StringVar, server_port_var: tk.StringVar,
    client_interface_var: tk.StringVar, client_port_var: tk.StringVar,
    available_devices: List[str],
    connect_callback: Callable, disconnect_callback: Callable
) -> Tuple[ttk.Labelframe, ttk.Label]:
    """
     ___________________________connection_frame___________________________ 
    |                                                                      |
    |   _________________________settings_frame_________________________   |
    |  |                                                                |  |
    |  |  Server address:  [--server_address--]   Port:  [server_port]  |  |
    |  |                                                                |  |
    |  |  Use Interface:  [client_interface]  Use Port:  [client_port]  |  |
    |  |________________________________________________________________|  |
    |                                                                      |
    |   ___________________________conn_frame___________________________   |
    |  |                                                                |  |
    |  |   ________status_frame________    ________btn_frame_________   |  |
    |  |  |                            |  |                          |  |  |
    |  |  |  Status:   [status_label]  |  |  [connect] [disconnect]  |  |  |
    |  |  |____________________________|  |__________________________|  |  |
    |  |________________________________________________________________|  |
    |______________________________________________________________________|
    
    """
    
    # frames
    connection_frame = ttk.Labelframe(master, labelwidget=ttk.Label(text="Connection"))
    settings_frame =   ttk.Frame(connection_frame, relief='flat', border=0)
    conn_frame =       ttk.Frame(connection_frame, relief='flat', border=0)
    btn_frame =        ttk.Frame(conn_frame,       relief='flat', border=0)
    status_frame =     ttk.Frame(conn_frame,       relief='flat', border=0)
    # settings frames
    settings_top_frame =     ttk.Frame(settings_frame, relief='flat', border=0)
    settings_btm_frame =     ttk.Frame(settings_frame, relief='flat', border=0)
    server_address_frame =   ttk.Frame(settings_top_frame, relief='flat', border=0)
    server_port_frame =      ttk.Frame(settings_top_frame, relief='flat', border=0)
    client_interface_frame = ttk.Frame(settings_btm_frame, relief='flat', border=0)
    client_port_frame =      ttk.Frame(settings_btm_frame, relief='flat', border=0)
    # settings frame items
    server_address_label =   ttk.Label(     server_address_frame,   width=13, text='Server address: ')
    server_port_label =      ttk.Label(     server_port_frame,      width=5,  text='Port: ')
    client_interface_label = ttk.Label(     client_interface_frame, width=13, text='Use Interface: ')
    client_port_label =      ttk.Label(     client_port_frame,      width=5,  text='Port: ')
    server_address_input =   ttk.Entry(     server_address_frame,             textvariable=server_address_var)
    server_port_input =      ttk.Entry(     server_port_frame,      width=8,  textvariable=server_port_var)
    client_interface_input = ttk.OptionMenu(client_interface_frame,           client_interface_var, available_devices[0], *available_devices)
    client_port_input =      ttk.Entry(     client_port_frame,      width=8,  textvariable=client_port_var)
    # settings frame items packs
    server_address_label.pack(  **widget_spacing, fill='both', side='left')
    server_address_input.pack(  **widget_spacing, fill='both', side='right', expand=1)
    server_port_label.pack(     **widget_spacing, fill='both', side='left')
    server_port_input.pack(     **widget_spacing, fill='both', side='right')
    client_interface_label.pack(**widget_spacing, fill='both', side='left')
    client_interface_input.pack(**widget_spacing, fill='both', side='right', expand=1)
    client_port_label.pack(     **widget_spacing, fill='both', side='left')
    client_port_input.pack(     **widget_spacing, fill='both', side='right')
    # settings frames packs
    server_address_frame.pack(  fill='both', side='left', expand=1)
    server_port_frame.pack(     fill='both', side='right')
    client_interface_frame.pack(fill='both', side='left', expand=1)
    client_port_frame.pack(     fill='both', side='right')
    settings_top_frame.pack(    fill='both', side='top')
    settings_btm_frame.pack(    fill='both', side='bottom')
    # lower widgets
    status_label =       ttk.Label(status_frame, textvariable=status_var)
    status_label_label = ttk.Label(status_frame, text='Status: ')
    connect_button =    ttk.Button(btn_frame,    text='Connect',    command=connect_callback,    width=8)
    disconnect_button = ttk.Button(btn_frame,    text='Disconnect', command=disconnect_callback, width=10)
    # lower widget packs
    status_label_label.pack(**widget_spacing, fill='both', side='left')
    status_label.pack(      **widget_spacing, fill='both', side='right', expand=1)
    connect_button.pack(    **widget_spacing, fill='both', side='left')
    disconnect_button.pack( **widget_spacing, fill='both', side='right')
    # frame packs
    status_frame.pack(                        fill='both', side='left', expand=1)
    btn_frame.pack(                           fill='both', side='right')
    settings_frame.pack(                      fill='both')
    conn_frame.pack(                          fill='both')
    # done! return frame
    return connection_frame


def make_server_connection_frame(
    master: tk.Frame,
    status_var: tk.StringVar,
    interface_var: tk.StringVar, port_var: tk.StringVar,
    available_devices: List[str],
    start_callback: Callable, stop_callback: Callable
) -> Tuple[ttk.Labelframe, ttk.Label]:
    """
     _______________________connection_frame_______________________ 
    |                                                              |
    |   _____________________settings_frame_____________________   |
    |  |                                                        |  |
    |  |  Interface:  [-------interface-------]  Port:  [port]  |  |
    |  |________________________________________________________|  |
    |                                                              |
    |   _______________________conn_frame_______________________   |
    |  |                                                        |  |
    |  |   ________status_frame________    ____btn_frame_____   |  |
    |  |  |                            |  |                  |  |  |
    |  |  |  Status:   [status_label]  |  |  [start] [stop]  |  |  |
    |  |  |____________________________|  |__________________|  |  |
    |  |________________________________________________________|  |
    |______________________________________________________________|
    
    """
    
    # frames
    connection_frame = ttk.Labelframe(master, labelwidget=ttk.Label(text="Connection"))
    settings_frame =   ttk.Frame(connection_frame, relief='flat', border=0)
    conn_frame =       ttk.Frame(connection_frame, relief='flat', border=0)
    btn_frame =        ttk.Frame(conn_frame,       relief='flat', border=0)
    status_frame =     ttk.Frame(conn_frame,       relief='flat', border=0)
    # settings frames
    interface_frame = ttk.Frame(settings_frame, relief='flat', border=0)
    port_frame =      ttk.Frame(settings_frame, relief='flat', border=0)
    # settings frame items
    interface_label = ttk.Label(     interface_frame, width=13, text='Use Interface: ')
    port_label =      ttk.Label(     port_frame,      width=5,  text='Port: ')
    interface_input = ttk.OptionMenu(interface_frame,           interface_var, available_devices[0], *available_devices)
    port_input =      ttk.Entry(     port_frame,      width=8,  textvariable=port_var)
    # settings frame items packs
    interface_label.pack(**widget_spacing, fill='both', side='left')
    interface_input.pack(**widget_spacing, fill='both', side='right', expand=1)
    port_label.pack(     **widget_spacing, fill='both', side='left')
    port_input.pack(     **widget_spacing, fill='both', side='right')
    # settings frames packs
    interface_frame.pack(fill='both', side='left', expand=1)
    port_frame.pack(     fill='both', side='right')
    # lower widgets
    status_label =       ttk.Label(status_frame, textvariable=status_var)
    status_label_label = ttk.Label(status_frame, text='Status: ')
    connect_button =    ttk.Button(btn_frame,    text='Start', command=start_callback, width=6)
    disconnect_button = ttk.Button(btn_frame,    text='Stop',  command=stop_callback,  width=6)
    # lower widget packs
    status_label_label.pack(**widget_spacing, fill='both', side='left')
    status_label.pack(      **widget_spacing, fill='both', side='right', expand=1)
    connect_button.pack(    **widget_spacing, fill='both', side='left')
    disconnect_button.pack( **widget_spacing, fill='both', side='right')
    # frame packs
    status_frame.pack(                        fill='both', side='left', expand=1)
    btn_frame.pack(                           fill='both', side='right')
    settings_frame.pack(                      fill='both')
    conn_frame.pack(                          fill='both')
    # done! return frame
    return connection_frame

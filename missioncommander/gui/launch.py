import tkinter as tk
from tkinter import ttk
import socket

from typing import Dict, Any, Callable, Union

from .frames import make_settings_frame, SettingsEntry
from .frames import make_log_frame
from .frames import make_client_connection_frame, make_server_connection_frame
from .frames import make_message_input_frame

from missioncommander.client import Client, ClientState, ClientStateTransition
from missioncommander.server import Server

frame_spacing: Dict[str, Union[int, str]] = {
    'fill': 'both',
    'padx': 8,
    'pady': 6,
    'ipadx': 6,
    'ipady': 2
}

# make logger for this module
import logging
logging.getLogger('missioncommander.gui')

class NoOpLogger:
    def __init__(self):        self.buf  = ''
    def write(self, msg: str): self.buf += msg
    def flush(self): pass

class ControllerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.client = Client()
        self.server = Server()
        self.available_interfaces = ["(Don't bind to specific interface)"] + [name for ind,name in socket.if_nameindex()]
        # status vars
        self.client_status_var = tk.StringVar()
        self.server_status_var = tk.StringVar()
        # client settings vars
        self.client_server_address_var = tk.StringVar()
        self.client_server_port_var = tk.StringVar()
        self.client_client_interface_var = tk.StringVar()
        self.client_client_port_var = tk.StringVar()
        # server settings vars
        self.server_server_interface_var = tk.StringVar()
        self.server_server_port_var = tk.StringVar()
    
    # def _set_client_address(self, text: str):
    #     try:
    #         self.client.address = text
    #     except Exception as e:
    #         self.client.logger.error("Could not set client address, with error:")
    #         self.client.logger.exception(e)
    #     else:
    #         self.client.logger.info(f"Set client address to '{text}'")
    
    # def _set_client_port(self, text: str):
    #     try:
    #         self.client.port = text
    #     except Exception as e:
    #         self.client.logger.error("Could not set client port, with error:")
    #         self.client.logger.exception(e)
    #     else:
    #         self.client.logger.info(f"Set client port to '{text}'")
    
    # def _set_client_id(self, text: str):
    #     try:
    #         self.client.client_id = text
    #     except Exception as e:
    #         self.client.logger.error("Could not set client ID, with error:")
    #         self.client.logger.exception(e)
    #     else:
    #         self.client.logger.info(f"Set client ID to '{text}'")
    
    def _connect_client(self):
        try:
            self.client.address =  self.client_server_address_var.get()
            self.client.port = int(self.client_server_port_var.get())
            inter = self.client_client_interface_var.get()
            if inter == self.available_interfaces[0]: inter = ''
            port = self.client_client_port_var.get()
        except Exception as e:
            self.client.logger.error("Invalid configuration")
            self.client.logger.exception(e)
            self.client.logger.error('')
            return
        try:
            self.client.client_id = Client.generate_new_id()
            self.client.connect(interface=inter, use_port=(int(port) if port!='' else None))
        except Exception as e:
            self.client.logger.error("Could not connect client, with error:")
            self.client.logger.exception(e)
            self.client.logger.error('')
        else:
            self.client.logger.info("Connected client\n")
    
    def _disconnect_client(self):
        try:
            self.client.disconnect()
        except Exception as e:
            self.client.logger.error("Could not disconnect client, with error:")
            self.client.logger.exception(e)
            self.client.logger.error('')
        else:
            self.client.logger.info("Disconnected client\n")

    # def _set_server_interface(self, text: str):
    #     try:
    #         self.server.interface = text
    #     except Exception as e:
    #         self.server.logger.error("Could not set server interface, with error:")
    #         self.server.logger.exception(e)
    #     else:
    #         self.server.logger.info(f"Set server interface to '{text}'")

    # def _set_server_port(self, text: str):
    #     try:
    #         self.server.port = text
    #     except Exception as e:
    #         self.server.logger.error("Could not set server port, with error:")
    #         self.server.logger.exception(e)
    #     else:
    #         self.server.logger.info(f"Set server port to '{text}'")
    
    def _start_server(self):
        try:
            inter = self.server_server_interface_var.get()
            if inter == self.available_interfaces[0]: inter = ''
            self.server.interface = inter
            self.server.port = int(self.server_server_port_var.get())
        except Exception as e:
            self.server.logger.error("Invalid configuration")
            self.server.logger.exception(e)
            self.client.logger.error('')
            return
        try:
            self.server.start()
        except Exception as e:
            self.server.logger.error("Could not start server, with error:")
            self.server.logger.exception(e)
            self.client.logger.error('')
        else:
            self.server.logger.info("Started server\n")
    
    def _stop_server(self):
        try:
            self.server.stop()
        except Exception as e:
            self.server.logger.error("Could not stop server, with error:")
            self.server.logger.exception(e)
            self.client.logger.error('')
        else:
            self.server.logger.info("Stopped server\n")
    
    def _client_state_callback(self, transition: ClientStateTransition):
        self.client_status_var.set(ClientState.get_name(transition.get_to()))
    
    def _server_state_callback(self, from_state: bool, to_state: bool):
        self.server_status_var.set("Running" if to_state else "Stopped")
    
    def _server_send(self, message: str):
        self.server.logger.debug(f"Callback received '{message}'\n")
        self.server.send(message)
    
    def setup(self, args: Dict[str, Any]) -> None:
        # set up root window
        self.root.title(args.get('title', "MissionCommander"))
        self.root.geometry(args.get('dims', '640x480'))
        self.root.minsize(*args.get('minsize', (600, 400)))
        
        # set up tabs
        tab_container = ttk.Notebook(self.root)
        client_tab = ttk.Frame(tab_container, relief='flat',   borderwidth=4)
        server_tab = ttk.Frame(tab_container, relief='flat',   borderwidth=4)
        client_frame = ttk.Frame(client_tab,  relief='groove', borderwidth=2)
        server_frame = ttk.Frame(server_tab,  relief='groove', borderwidth=2)

        # set up StringVar handles
        
        # set up client frame
        client_log_frame, client_log_handler = make_log_frame(client_frame)
        client_connection_frame = make_client_connection_frame(
            client_frame,
            self.client_status_var,
            self.client_server_address_var, self.client_server_port_var,
            self.client_client_interface_var, self.client_client_port_var,
            self.available_interfaces,
            self._connect_client, self._disconnect_client
        )
        client_connection_frame.pack(**frame_spacing)
        
        # pack client frame
        client_log_frame.pack(       **frame_spacing, expand=1)
        self.client._subscribe_to_state_update(self._client_state_callback)
        
        # set up server frame
        server_log_frame, server_log_handler = make_log_frame(server_frame)
        server_connection_frame = make_server_connection_frame(
            server_frame,
            self.server_status_var,
            self.server_server_interface_var, self.server_server_port_var,
            self.available_interfaces,
            self._start_server, self._stop_server
        )
        server_connection_frame.pack(**frame_spacing)
        
        server_input_frame = make_message_input_frame(server_frame, self._server_send)
        
        # pack server frame
        #server_input_frame.pack(     **frame_spacing)
        server_log_frame.pack(       **frame_spacing, expand=1)
        self.server.subscribe_to_state_update(self._server_state_callback)
        
        # finalize and pack tabs
        client_frame.pack(expand=1, fill='both', padx=4, pady=4)
        server_frame.pack(expand=1, fill='both', padx=4, pady=4)
        tab_container.add(client_tab, text="Client")
        tab_container.add(server_tab, text="Server")
        tab_container.pack(expand=1, fill='both')

        # configure loggers
        self.client.logger.setLevel(logging.DEBUG)
        self.server.logger.setLevel(logging.DEBUG)
        self.client.logger.addHandler(client_log_handler)
        self.server.logger.addHandler(server_log_handler)
        client_log_handler.start()
        server_log_handler.start()
        self.client.logger.info("LogFrame inited")
        self.server.logger.info("LogFrame inited")


    def launch(self):
        self.root.mainloop()

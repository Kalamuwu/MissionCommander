#!/usr/bin/env python3

import threading
import socket
import collections
import json

from typing import List, SupportsInt, Callable, Dict

from . import networking_utils, connection

# make logger for this module
import logging
logging.getLogger('missioncommander.server')


class ClientHandler(connection.ConnectionHandler):
    def __init__(self, server, client_sock, client_addr):
        super().__init__(use_socket=client_sock)
        self.start()
        self.__addr = client_addr
        self.__server = server
        # parse negotiation message
        try:
            msg = self.wait_for_recv(timeout=5.0)       # client sent a valid negotiation header...
            if (msg is not None and                     #   and timeout did not expire...
                msg.subject == 'negotiation' and        #     and it matches the right subject...
                (id:=msg.payload['id'])                 #       and it has a valid payload...
            ): self.__client_id = id; return            #         then set that payload as client_id.
        except: pass
        self.__client_id = None  # some error occurred or check failed. mark this ClientHandler as failed.

    @property
    def client_id(self):
        return self.__client_id
    
    def reopen_with(self, sock: socket.socket, addr):
        self.__addr = addr
        self.sock = sock
        self.start()
    
    def __repr__(self) -> str:
        return f"<ClientHandler addr='{self.__addr}' id='{self.__client_id}'>"


class Server:
    def __init__(self):
        # init vars
        self.__interface = None
        self.__port = None
        self.__logger = logging.getLogger('missioncommander.server')
        # init socket
        self.__accept_socket: socket.socket = None
        # init server thread
        self.__accept_thread = threading.Thread(target=self.__accept_loop, name="ServerMainThread")
        self.__conns: Dict[str, ClientHandler] = {}
        # init status vars
        self.__status_callbacks: List[Callable] = []
        self.__should_run = False
        # announce
        self.__logger.info("Server inited")

    @property
    def logger(self):
        return self.__logger
    
    # [no setter for logger]
    
    @property
    def interface(self):
        return self.__interface
    
    @interface.setter
    def interface(self, interface):
        if self.__should_run:
            raise Exception("Server must be stopped before setting interface")
        if interface == '*':  interface = ''
        self.__interface = interface
    
    @property
    def port(self):
        return self.__port
    
    @port.setter
    def port(self, port):
        if self.__should_run:
            raise Exception("Server must be stopped before setting port")
        try:
            self.__port = int(port)
        except ValueError:
            raise ValueError("Port must be integer value")
    
    def status_str(self) -> str:
        return "Running" if self.__should_run else "Stopped"
    
    def subscribe_to_state_update(self, callback: Callable) -> None:
        self.__status_callbacks.append(callback)
    
    def __set_should_run(self, val: bool) -> None:
        # update state
        if self.__should_run == val:
            logging.error(f"Already in state running={val}")
            return
        self.__should_run = val
        # tick callbacks
        for cb in self.__status_callbacks:
            try: cb(not val, val)
            except: logging.error("Subscribed status update callback failed!")
    
    def start(self) -> bool:
        if self.__interface is None:  raise AttributeError("Interface not set")
        if self.__port      is None:  raise AttributeError("Port not set")
        # variables ok. make socket
        self.__accept_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__accept_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__accept_socket.settimeout(1.0)
        # bind to internal host
        self.__accept_socket.bind((self.__interface, self.__port))
        self.__accept_socket.listen(5)
        # start thread
        self.__set_should_run(True)
        self.__accept_thread.start()
        return True
    
    def stop(self) -> bool:
        # stop thread
        self.__set_should_run(False)
        self.__accept_thread.join()
        # stop internal socket
        self.__accept_socket.close()  # TODO check for `None`
        # close connections
        for conn in self.__conns.values():
            conn.send(connection.Message('shutdown', {}))
            conn.stop()
        # all is well!
        return True
    
    def send(self, to: str, msg: connection.Message) -> bool:
        # very basic right now. just send to all
        if to == '*':
            for conn in self.__conns.values():
                conn.send(msg)
        else:
            if to not in self.__conns:
                self.logger.error(f"Unknown client ID {to}")
                return False
            self.__conns[to].send(msg)
        return True
    
    def __negotiate_client_id(self, client_sock: socket.socket, client_addr):
        client_sock.settimeout(1.0)
        client = ClientHandler(self, client_sock, client_addr)
        # did negotiation fail?
        if client.client_id is None:
            self.__logger.error(f"Connection to {client_addr} failed. Client did not complete negotiation before timeout or negotiation was malformed.")
            client.stop(blocking=False)
        else:
            self.__logger.warn("new connection: " + repr(client))
            if client.client_id in self.__conns:
                self.__logger.warn("... seen this connection before!")
                client.stop(blocking=False)
                self.__conns[client.client_id].reopen_with(client_sock, client_addr)
            else:
                self.__logger.warn("... this is new connection.")
                self.__conns[client.client_id] = client
    
    def __accept_loop(self):
        while self.__should_run:
            try:
                # accept outside connection
                (client_sock, client_addr) = self.__accept_socket.accept()
                self.__negotiate_client_id(client_sock, client_addr)
            except socket.timeout: pass

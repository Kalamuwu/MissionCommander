#!/usr/bin/env python3

import threading
import socket
import time
import logging
import collections
import json
import enum
import random

from typing import List, SupportsInt, Union, Callable, Optional, Dict, Tuple

from . import networking_utils, connection

class ClientState:
    STATE_UNDEFINED  = 0x0000
    STATE_NEEDS_INIT = 0x0001
    STATE_OK         = 0x0002
    STATE_RUNNING    = 0x0004

    STATE_NOT_CONNECTED  = 0x0008
    STATE_CONNECTING     = 0x0010
    STATE_CONNECTED      = 0x0020
    STATE_CONNECT_FAILED = 0x0040

    STATE_RECONNECTING     = 0x0080
    STATE_RECONNECT_FAILED = 0x0100
    
    STATE_DISCONNECTING     = 0x0200
    STATE_DISCONNECT_FAILED = 0x0400
    STATE_UNEXP_CLOSED      = 0x0800
    
    @classmethod
    def get_name(cls, state: int) -> Union[str, None]:
        # look for exact matches
        for key,value in vars(cls).items():
            if isinstance(value, int) and value == state:
                return key
        # look for partial matches
        out = ""
        for key,value in vars(cls).items():
            if isinstance(value, int) and (value&state):
                out += ", " + cls.get_name(value)
        # no matches
        return None if (not out) else out[2:]


class ClientStateTransition:
    def __init__(self, frm: int, to: int):
        self.__from = frm or ClientState.STATE_UNDEFINED
        self.__to   = to  or ClientState.STATE_UNDEFINED
    
    def get_from(self) -> int: return self.__from
    def get_to(self)   -> int: return self.__to

    def __str__(self) -> str:
        return f"Changing client state from {ClientState.get_name(self.__from)} to {ClientState.get_name(self.__to)}"
    def __repr__(self) -> str:
        return f"<ClientStateTransition from={self.__from} to={self.__to}>"


class Client:
    def __init__(self, attempt_reconnect: Optional[bool] = True):
        # init vars
        self.attempt_reconnect = attempt_reconnect
        self.__client_id = None
        self.__address = None
        self.__port = None
        self.__interface = None
        self.__bind_port = None
        # init objects
        self.__logger = logging.getLogger('missioncommander.client')
        self.__conn: connection.ConnectionHandler = None
        # status information
        self.__state_lock = threading.Lock()
        self.__state: int = ClientState.STATE_NEEDS_INIT | ClientState.STATE_NOT_CONNECTED
        # callback stuff
        self.__callback_verbs: List[str] = ['connect', 'disconnect', 'reconnect', 'servershutdown', 'message', 'statechange']
        self.__callbacks: Dict[str, List[Callable]] = { verb:[] for verb in self.__callback_verbs }
        self.__callback_threads: List[threading.Thread] = []
        # message consumer stuff
        self.__recv_consumer_thread = None
        # announce
        self.__logger.info("Client inited\n")
    
    @staticmethod
    def generate_new_id() -> str:
        ID_LENGTH = 16
        return ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=ID_LENGTH))
    
    def __check_inited(self):
        if (
            self.__address   is not None and
            self.__port      is not None and
            self.__client_id is not None
        ):
            mask = ~ClientState.STATE_NEEDS_INIT
            self.__set_state(self.state & mask)
        else:
            self.__set_state(self.state | ClientState.STATE_NEEDS_INIT)

    @property
    def logger(self):
        return self.__logger
    
    # [no setter for logger]
    
    @property
    def address(self):
        return self.__address
    
    @address.setter
    def address(self, address):
        if self.state & ClientState.STATE_RUNNING:
            raise Exception("Client must be stopped before setting address")
        self.__address = address
        self.__check_inited()
    
    @property
    def interface(self):
        return self.__interface
    
    @interface.setter
    def interface(self, interface):
        if self.state & ClientState.STATE_RUNNING:
            raise Exception("Client must be stopped before setting interface")
        self.__interface = interface
        self.__check_inited()
    
    @property
    def client_id(self):
        return self.__address
    
    @client_id.setter
    def client_id(self, client_id):
        if self.state & ClientState.STATE_RUNNING:
            raise Exception("Client must be stopped before setting client_id")
        self.__client_id = client_id
        self.__check_inited()
    
    @property
    def port(self):
        return self.__port
    
    @port.setter
    def port(self, port):
        if self.state & ClientState.STATE_RUNNING:
            raise Exception("Client must be stopped before setting port")
        try:
            self.__port = int(port)
        except ValueError:
            raise ValueError("Port must be integer value")
        else:
            self.__check_inited()
    
    @property
    def bind_port(self):
        return self.__bind_port
    
    @bind_port.setter
    def bind_port(self, bind_port):
        if self.state & ClientState.STATE_RUNNING:
            raise Exception("Client must be stopped before setting bind port")
        try:
            self.__bind_port = int(bind_port)
        except ValueError:
            raise ValueError("Bind port must be integer value")
        else:
            self.__check_inited()
    
    def __trigger(self, event: str, **kwargs) -> None:
        for cb in self.__callbacks[event]:
            try:
                th = threading.Thread(target=cb, kwargs=kwargs)
                self.__callback_threads.append(th)
                th.start()
            except:
                print(f"Error launching callback for event {event}")
    
    def subscribe(self, verb: str, callback: Callable) -> bool:
        if not callable(callback): raise ValueError("Callback not a function")
        verb = verb.lower().replace('-', '').replace('_', '')  # strip on-xyz --> onxyz
        if verb.startswith('on'): verb = verb[2:]              # strip onxyz --> xyz
        if verb not in self.__callback_verbs: raise KeyError(f"Unknown verb {verb}")
        self.__callbacks[verb].append(callback)
    
    @property
    def state(self) -> int:
        with self.__state_lock: return self.__state
    
    def __set_state(self, state: int):
        # check noop
        with self.__state_lock:
            if self.__state == state: return
        # do transition
        transition = ClientStateTransition(self.state, state)
        self.__logger.debug(str(transition))
        with self.__state_lock:
            self.__state = state
        self.__trigger('statechange', transition=transition)
    
    def __recv_consumer_thread_func(self):
        msg = None
        while self.__recv_consumer_should_run:
            if not self.__conn.running:
                if not self.attempt_reconnect:
                    self.logger.error("Server connection closed unexpectedly")
                    return
                self.logger.warn("Server connection closed, reconnecting...")
                if not self.__reconnect_wrapper():  return
                self.logger.info("Reconnected.")
            msg: connection.Message = self.__conn.recv()
            if msg is not None:
                # look for shutdown command
                if msg.subject == 'shutdown':
                    self.logger.info("Server is shutting down. Closing connection")
                    self.__server_shut_down()
                # message received. callbacks, callbacks, callbacks!
                else:  self.__trigger('message', msg=msg)
            # clear out old threads
            for i,th in enumerate(self.__callback_threads):
                if not th.is_alive(): self.__callback_threads.pop(i)
    

    def connect(self) -> bool:
        # fail condition
        def __fail_connect(unexpected: bool = False) -> False:
            self.__set_state((ClientState.STATE_UNEXP_CLOSED*unexpected) | ClientState.STATE_CONNECT_FAILED | ClientState.STATE_NOT_CONNECTED)
            self.__conn = None
            return False
        # pre-exec variable checks
        if self.__address   is None:  raise AttributeError("Address not set")
        if self.__port      is None:  raise AttributeError("Port not set")
        if self.__client_id is None:  raise AttributeError("Client ID not set")
        # needs init?
        if (self.state & ClientState.STATE_NEEDS_INIT):
            self.__logger.error("Client has some un-initialized fields")
            return False
        # is already connected?
        if not (self.state & ClientState.STATE_NOT_CONNECTED):
            self.__logger.error("Client is already connected")
            return False
        # variables all set. try bind
        self.__set_state(ClientState.STATE_OK | ClientState.STATE_CONNECTING)
        self.__conn = connection.ConnectionHandler()
        try:
            if self.__bind_port is not None and self.__interface is not None:
                self.__logger.debug(f"Binding outbound socket to {self.__interface}:{self.__bind_port}")
                self.__conn.sock.bind((self.__interface, self.__bind_port))
            else:
                self.__logger.debug(f"Using any available interface+port pair")
        except socket.timeout:
            self.__logger.error("Socket connection timed out during interface bind")
            return __fail_connect(True)
            return False
        except Exception as e:
            self.__logger.error("socket.bind failed with error:")
            self.__logger.exception(e)
            return __fail_connect(False)
        # bind good (or skipped). attempt connect
        try:
            self.__conn.sock.connect((self.__address, self.__port))
        except socket.timeout:
            self.__logger.error("Socket connection timed out during initial connect")
            return __fail_connect(True)
            return False
        except ConnectionRefusedError:
            self.__logger.warn("Connection refused. Reconnecting...")
        except Exception as e:
            self.__logger.error("socket.connect failed with error:")
            self.__logger.exception(e)
            return __fail_connect(False)
        # connect successful. start ticking handler
        try:
            self.__conn.start()
        except Exception as e:
            self.__logger.error("ConnectionHandler.start failed with error:")
            self.__logger.exception(e)
            return __fail_connect(False)
        # start successful. do client_id negotiation
        try:
            self.__conn.send(connection.Message('negotiation', { 'id': self.__client_id }))
        except socket.timeout:
            self.__logger.error("Socket connection timed out during client ID negotiation")
            return __fail_connect(True)
        except Exception as e:
            self.__logger.error("Client ID negotiation failed with error:")
            self.__logger.exception(e)
            return __fail_connect(False)
        # handshake successful. connection is ready to use.
        self.__logger.info(f"Connected successfully. Client ID: {self.__client_id}")
        self.__set_state(ClientState.STATE_OK | ClientState.STATE_CONNECTED)
        # start recv consumer thread
        self.__recv_consumer_should_run = True
        self.__recv_consumer_thread = threading.Thread(target=self.__recv_consumer_thread_func)
        self.__recv_consumer_thread.start()
        self.__trigger('connect', client_id=self.__client_id)
        return True
    
    def __reconnect_wrapper(self):
        sleeptime = 0.1
        rec_again = self.attempt_reconnect
        if not rec_again: return False
        self.__set_state(ClientState.STATE_RECONNECTING | ClientState.STATE_CONNECTING | ClientState.STATE_OK)
        while rec_again:
            self.__logger.info(f"Attempting reconnect after {sleeptime} seconds...")
            # do wait loop
            start = time.perf_counter()
            while (time.perf_counter() - start < sleeptime):
                if not self.attempt_reconnect:
                    self.__logger.warn("No longer attempting reconnect.")
                    self.__set_state(ClientState.STATE_RECONNECT_FAILED | ClientState.STATE_NOT_CONNECTED)
                    return False
                time.sleep(0.1)
            # timer is expired, do reconnect step
            sleeptime = min(sleeptime*2, 15)
            rec_again = not self.__reconnect()
        self.__set_state(ClientState.STATE_OK | ClientState.STATE_CONNECTED)
        self.__trigger('reconnect', client_id=self.__client_id)
        self.__logger.info("Successfully reconnected")
        return True

    def __reconnect(self):
        self.__conn = connection.ConnectionHandler()
        # try re-bind
        try:
            if self.__bind_port is not None and self.__interface is not None:
                self.__logger.debug(f"Binding outbound socket to {self.__interface}:{self.__bind_port}")
                self.__conn.sock.bind((self.__interface, self.__bind_port))
            else:
                self.__logger.debug(f"Using any available interface+port pair")
        except socket.timeout:
            self.__logger.error("Socket connection timed out during interface bind")
            return False
        except ConnectionRefusedError: return False
        except Exception as e:
            self.__logger.error("socket.bind failed with error:")
            self.__logger.exception(e)
            return False
        # bind good (or not asked for). attempt connect
        try:
            self.__conn.sock.connect((self.__address, self.__port))
        except socket.timeout:
            self.__logger.error("Socket connection timed out during initial connect")
            return False
        except ConnectionRefusedError: return False
        except Exception as e:
            self.__logger.error("socket.connect failed with error:")
            self.__logger.exception(e)
            return False
        # connect successful. start ticking handler
        try:
            self.__conn.start()
        except Exception as e:
            self.__logger.error("ConnectionHandler.start failed with error:")
            self.__logger.exception(e)
            return False
        # start successful. do client_id negotiation
        try:
            self.__conn.send(connection.Message('negotiation', { 'id': self.__client_id }))
        except socket.timeout:
            self.__logger.error("Socket connection timed out during client ID negotiation")
            return False
        except Exception as e:
            self.__logger.error("Client ID negotiation failed with error:")
            self.__logger.exception(e)
            return False
        # handshake successful. connection is ready to use.
        self.__logger.info(f"Reconnected successfully. Client ID: {self.__client_id}")
        # resume recv consumer thread
        self.__recv_consumer_should_run = True
        return True
    
    def disconnect(self) -> bool:
        self.__trigger('disconnect')
        # pre-exec variable checks
        # is already disconnected?
        if not (self.state & ClientState.STATE_CONNECTED):
            self.__logger.error("Client is not connected")
            return False
        # variables all set. stop recv consumer
        self.attempt_reconnect = False
        if self.__recv_consumer_thread is not None:
            self.__recv_consumer_should_run = False
        # send shutdown message to server
        did_err = False
        did_time_out = False
        try:
            self.__conn.send(connection.Message('shutdown', {}))
        except socket.timeout:
            self.__logger.error("Socket connection timed out during sending of shutdown message")
            did_err = True
            did_time_out = True
        except Exception as e:
            self.__logger.error("Socket couldn't send shutdown signal, with error:")
            self.__logger.exception(e)
            did_err = True
        # close connection handler thread
        try:
            self.__conn.stop(blocking=True)
        except Exception as e:
            self.__logger.error("Couldn't stop ConnectionHandler thread, with error:")
            self.__logger.exception(e)
            did_err = True
        # clean up and leave
        self.__conn = None
        if did_err:
            self.__set_state(
                 ClientState.STATE_NOT_CONNECTED                     |
                (ClientState.STATE_UNEXP_CLOSED      * did_time_out) |
                 ClientState.STATE_DISCONNECT_FAILED                 )
        else:
            self.__set_state(ClientState.STATE_NOT_CONNECTED | ClientState.STATE_OK)
        # (make sure recv consumer stopped)
        if self.__recv_consumer_thread is not None and self.__recv_consumer_thread.is_alive():
            self.__recv_consumer_thread.join()
        return not did_err
    
    def __server_shut_down(self):
        self.__trigger('servershutdown')
        # stop recv consumer
        if self.__recv_consumer_thread is not None:
            self.__recv_consumer_should_run = False
        # close connection handler thread
        try:
            self.__conn.stop(blocking=True)
        except Exception as e:
            self.__logger.error("Couldn't stop ConnectionHandler thread, with error:")
            self.__logger.exception(e)
        # clean up and leave
        self.__conn = None
        self.__set_state(ClientState.STATE_NOT_CONNECTED | ClientState.STATE_OK)

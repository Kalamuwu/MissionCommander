import enum
import socket
import threading
import collections
import time
import json

from typing import Union, Dict, Optional, Callable, List

HEADER_LEN_BYTES = 64
CHUNK_SIZE_BYTES = 2048

class ConnectionStatus(enum.Flag):
    NONE = 0
    UNDEF = NONE
    # action statuses
    ACTION_TRYING = 1
    ACTION_FAILED = 2
    ACTION_SUCCESS = 4
    # connect
    ACTION_CONNECT = 8
    CONNECTING = ACTION_CONNECT | ACTION_TRYING
    CONNECTED = ACTION_CONNECT | ACTION_SUCCESS
    CONNECT_FAILED = ACTION_CONNECT | ACTION_FAILED
    # reconnect
    ACTION_RECONNECT = 16
    RECONNECTING = ACTION_RECONNECT | ACTION_TRYING
    RECONNECTED = ACTION_RECONNECT | ACTION_SUCCESS
    RECONNECT_FAILED = ACTION_RECONNECT | ACTION_FAILED
    # disconnect
    ACTION_DISCONNECT = 32
    DISCONNECTING = ACTION_DISCONNECT | ACTION_TRYING
    DISCONNECT_FAILED = ACTION_DISCONNECT | ACTION_FAILED
    DISCONNECTED = ACTION_DISCONNECT | ACTION_SUCCESS
    # # start
    # ACTION_START = 64
    # STARTING = ACTION_START | ACTION_TRYING
    # START_FAILED = ACTION_START | ACTION_FAILED
    # STARTED = ACTION_START | ACTION_SUCCESS
    # # stop
    # ACTION_STOP = 128
    # STOPPING = ACTION_STOP | ACTION_TRYING
    # STOP_FAILED = ACTION_STOP | ACTION_FAILED
    # STOPPED = ACTION_STOP | ACTION_SUCCESS
    
    def is_connect(self)    -> bool: return bool(self & self.__class__.ACTION_CONNECT)
    def is_reconnect(self)  -> bool: return bool(self & self.__class__.ACTION_RECONNECT)
    def is_disconnect(self) -> bool: return bool(self & self.__class__.ACTION_DISCONNECT)
    # def is_start(self)      -> bool: return bool(self & self.__class__.ACTION_START)
    # def is_stop(self)       -> bool: return bool(self & self.__class__.ACTION_STOP)

    def is_trying(self)  -> bool: return bool(self & self.__class__.ACTION_TRYING)
    def is_success(self) -> bool: return bool(self & self.__class__.ACTION_SUCCESS)
    def is_failed(self)  -> bool: return bool(self & self.__class__.ACTION_FAILED)


class Message:
    def __init__(self, subject: str, payload: Dict[str, Union[str,int,float,bool]]):
        self.__subject = subject
        self.__payload = payload

    @property
    def subject(self) -> str:
        return self.__subject
    
    @property
    def payload(self) -> str:
        return self.__payload
    
    def serialize(self) -> bytes:
        return json.dumps(self.payload, indent=None).encode('utf-8')
    
    @classmethod
    def deserialize(cls, subject: str, bytes_in: bytes):
        data = json.loads(bytes_in.decode('utf-8'))
        return cls(subject, data)


class ConnectionHandler:
    def __init__(self, use_socket=None):
        # thread stuff
        self.__thread = None
        self.__should_run = False
        self.__outbound_message_queue = collections.deque()
        self.__inbound_message_queue  = collections.deque()
        # socket stuff
        if use_socket is not None:
            self.sock = use_socket
        else:
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.__sock.settimeout(1.0)
    
    @property
    def sock(self) -> socket.socket:
        return self.__sock
    
    @sock.setter
    def sock(self, sock: socket.socket):
        if self.__should_run or self.running:
            raise AttributeError("Cannot be running")
        if not isinstance(sock, socket.socket):
            raise ValueError("Not a socket")
        self.__sock = sock
    
    @property
    def running(self):
        return self.__thread is not None and self.__thread.is_alive()
    
    def __recv_queue_tick(self) -> bool:
        # receive header
        bytes_recvd = 0
        chunks: List[bytes] = []
        while bytes_recvd < HEADER_LEN_BYTES:
            try:
                chunk = self.__sock.recv(HEADER_LEN_BYTES - bytes_recvd)
            except socket.timeout:  return True  # return True because False or None will stop connection
            if chunk == b'':  return False
            chunks.append(chunk)
            bytes_recvd += len(chunk)
        # assemble and parse header
        try:
            header = b''.join(chunks).decode('utf-8')
            header = header.replace(b'\x00'.decode(), '')  # remove null bytes
            header = json.loads(header)
            msglen, subj = header['length'], header['subject']
        except Exception as e:
            print("Failed to parse message header, with exception: ", e)
            print("Header:", header)
            return True  # return True because False or None will stop connection
        # receive message
        bytes_recvd = 0
        chunks: List[bytes] = []
        while bytes_recvd < msglen:
            chunk = self.__sock.recv(min(msglen - bytes_recvd, CHUNK_SIZE_BYTES))
            if chunk == b'':  return False
            chunks.append(chunk)
            bytes_recvd += len(chunk)
        # assemble and parse message
        try:
            body = b''.join(chunks)
            msg = Message.deserialize(subj, body)
        except Exception as e:
            print("Failed to parse message body, with exception: ", e)
            print("Body:", body)
            return True  # return True because False or None will stop connection
        self.__inbound_message_queue.append(msg)
        return True
    
    def __send_queue_tick(self) -> bool:
        # check for message
        try: _msg: Message = self.__outbound_message_queue.popleft()
        except IndexError: return True  # return True because False or None will stop connection
        bytes_out = _msg.serialize()
        # define header
        try:
            header = json.dumps({ 'length': len(bytes_out), 'subject': _msg.subject }, indent=None)
            header = header.encode('utf-8')
            if len(header) > HEADER_LEN_BYTES:
                raise OverflowError(f"Header length too big! Make HEADER_LEN_BYTES larger! (current: {HEADER_LEN_BYTES})")
            header = header.ljust(HEADER_LEN_BYTES, b'\x00')
        except Exception as e:
            print("Could not pack header, with exception: ", e)
            print("Header:", header)
            return True  # return True because False or None will stop connection
        # send header
        total = 0
        while total < len(header):
            sent = self.__sock.send(header[total:])
            if sent == 0:
                self.__outbound_message_queue.appendleft(_msg)  # put message back in queue
                return False
            total += sent
        # send message
        total = 0
        while total < len(bytes_out):
            try:
                sent = self.__sock.send(bytes_out[total:])
            except: sent = 0
            if sent == 0:  # either an error occurred, or nothing was sent
                self.__outbound_message_queue.appendleft(_msg)  # put message back in queue
                return False
            total += sent
        return True
    
    def __main_loop(self):
        while self.__should_run:
            # read any incoming
            if not self.__recv_queue_tick():
                print("Connection closed unexpectedly during recv queue tick")
                self.stop(blocking=False); continue
            # send any outgoing
            if not self.__send_queue_tick():
                print("Connection closed unexpectedly during send queue tick")
                self.stop(blocking=False); continue
        # socket might have been unexpectedly closed, so try/except/pass these
        try: self.__sock.shutdown(socket.SHUT_RDWR)
        except: pass
        try: self.__sock.close()
        except: pass
    
    def start(self):
        self.__should_run = True
        self.__thread = threading.Thread(target=self.__main_loop, name='ReconnectingStreamingSocket')
        self.__thread.start()
    
    def stop(self, blocking:bool=True):
        self.__should_run = False
        if blocking and self.__thread is not None: self.__thread.join()
    
    def send(self, message: Message):
        if not isinstance(message, Message):
            raise ValueError("Not of class Message")
        self.__outbound_message_queue.append(message)
    
    def recv(self) -> Union[Message, None]:
        try: return self.__inbound_message_queue.popleft()
        except IndexError: return None

    def wait_for_recv(self, timeout: float = 5.0) -> Union[Message, None]:
        """
        Blocks until a message is available from recv(). Pops and returns that
        message.

        If :attr:`timeout` is a positive float greater than 0.0, it will
        determine if there is a time limit to this function. If that time
        limit is met, this function returns :const:`None`.
        """
        msg = None
        start_time = time.perf_counter()
        while True:
            msg = self.recv()
            if msg is not None: return msg
            if (timeout>0) and (time.perf_counter() - start_time >= timeout): return None

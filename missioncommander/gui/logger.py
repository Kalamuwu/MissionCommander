import tkinter as tk
from tkinter import ttk
import logging
import threading
import collections
import time

class ScrolledTextLogger(logging.Handler):
    def __init__(self, textbox: tk.scrolledtext.ScrolledText):
        super().__init__()
        self.__textbox = textbox
        self.__thread = threading.Thread(name="ScrolledTextLogger", target=self.__mainloop, daemon=True)
        self.__message_queue = collections.deque()
    
    def start(self): self.__thread.start()

    def __mainloop(self):
        while True:
            try: msg = self.__message_queue.popleft()
            except IndexError: time.sleep(0.05)
            else:
                self.__textbox.configure(state="normal")      # make field editable
                self.__textbox.insert("end", msg)             # write text to textbox
                self.__textbox.see("end")                     # scroll to end
                self.__textbox.configure(state="disabled")    # make field readonly

    def emit(self, record: logging.LogRecord):
        message = self.format(record) + '\n'
        self.__message_queue.append(message)

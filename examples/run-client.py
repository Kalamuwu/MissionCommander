#!/usr/bin/env python3

import missioncommander

import time
import logging
logging.basicConfig(level=logging.DEBUG)

client = missioncommander.Client()
client.address = '127.0.0.1'
client.port = 30000
client.client_id = client.generate_new_id()
should_run = True

def on_msg(msg: missioncommander.Message):
    print("got message: ", msg.payload)

def on_shutdown():
    print("server shutting down")
    should_run = False

client.subscribe('message', on_msg)
client.subscribe('servershutdown', on_shutdown)
client.connect()

print("Ready")

while should_run:
    try: time.sleep(1)
    except KeyboardInterrupt:
        should_run = False

if client.state & missioncommander.ClientState.STATE_CONNECTED:
    client.disconnect()

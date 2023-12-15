#!/usr/bin/env python3

import missioncommander

server = missioncommander.Server()
server.interface = ''
server.port = 30000

server.start()

should_run = True
while should_run:
    try:
        server.send('*',
            missioncommander.Message('echo', {
                'message': input("message: ")
            }))
    except KeyboardInterrupt:
        should_run = False

server.stop()

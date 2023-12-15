# MissonCommander

A pure-python, basic client/server connection manager with support for callbacks. Contains simple CLI and GUI interfaces for easy deployment.

## Sections
1. [**MissionCommander python API**](#missioncommander-api)
2. [**MissionCommander CLI interface**](#missioncommander-cli)
3. [**MissionCommander GUI interface**](#missioncommander-gui)

<br>

---
---

<br>

# MissionCommander API

MissionCommander is a simple server/client library, readily configurable yet simple and lightweight.
To get started, import `missioncommander`, configure your parameters, and start the client or server connection.

The `examples/` directory is a good place to start, albeit the two examples are very simple. MissionCommander handles the lower-level connection and socket things, and you can focus on just building your project.

<br>

## Using the `Message` class

This class used both by the server and client, for sending messages back and forth. The constructor has two arguments, `(str) subject` and `(dict) payload`:
```python
my_message = missioncommander.Message('echo', { 'message': 'hello!' })
```
Once instantiated, `Message`s are read-only. Their attributes can be accessed with `Message.subject` and `Message.payload`.

<br>

## Using the `Client` class
The `missioncommander.Client` class is, well, the client half of the connection. Multiple clients can connect to one server, and the server will track them all. Configuration is done by simply setting instance variables. Note that these setters may raise exceptions if the given value is not of the proper type (e.x. `client.port` isn't an `int`) or if the client state is such that setting the instance variable isn't possible (e.x. client is currently connected).

---

### Configuring

First, instantiate an instance of `missioncommander.Client` and configure your parameters:
```python
import missioncommander

client = missioncommander.Client()

client.address = '127.0.0.1'
client.port = 30_000
client.client_id = client.generate_new_id()
```

The following parameters are required for configuration:
- `client.address` - The address of the server to connect to.
- `client.port` - The port to connect to on the server.
- `client.client_id` - The identifier of this `Client`. Don't reuse identifiers unless you specifically know what you're doing, as things will probably break. To randomize the ID of a new client, call `missioncommander.Client.generate_id()`.

The following parameters are optional, but might be useful to some people:
- `client.interface` - The client interface for the outbound connection to bind to. By default, the outbound connection is bound to any available interface (and can be reset to this state by setting `client.interface` to `''` or `'*'`.)
- `client.bind_port` - **This is different from `client.port`.** This is the port on the **client machine** to bind to, not the server port to connect to. This field is required if `client.interface` is not `''` or `'*`.

---

### Connecting

Once you configure your client connection, call `client.connect()` to start the socket and associated thread. Note that `client.disconnect()` must be called before/upon exiting the program:

```python
client.connect()

should_run = True
while should_run:
    try: input("ctrl+c to exit")
    except KeyboardInterrupt: should_run = False

client.disconnect()
```

---

### Client state

Client state is stored in a bitfield, which can be AND-ed against `missioncommander.ClientState` to check for certain states. These available states are as follows:
```
STATE_UNDEFINED  = 0
STATE_NEEDS_INIT = 1
STATE_OK         = 2
STATE_RUNNING    = 4

STATE_NOT_CONNECTED  = 8
STATE_CONNECTING     = 16
STATE_CONNECTED      = 32
STATE_CONNECT_FAILED = 64

STATE_RECONNECTING     = 128
STATE_RECONNECT_FAILED = 256

STATE_DISCONNECTING     = 512
STATE_DISCONNECT_FAILED = 1024
STATE_UNEXP_CLOSED      = 2048
```

Multiple states can be OR'ed together to form a compound state, e.x. `STATE_OK | STATE_RUNNING | STATE_CONNECTED`. To get the string name(s) of these states, use `missioncommander.ClientState.get_name( <state> )`.

---

### Callbacks and events

Events can be subscribed to with callbacks. *Note that callbacks will be run in their own, separate thread.*

```python
def on_message_callback(msg: missioncommander.Message):
    print(f"Message received!  Subject: '{msg.subject}'  Body:")
    print(msg.body)

client.subscribe('message', on_message_callback)
```

The first argument to `client.subscribe` is the verb event to subscribe to. The currently recognized events are as follows:
- `'connect'` - Called just after a connection to the server is established. This callback should take no arguments.
- `'disconnect'` - Called just before the connection to the server is destroyed. This is triggered by a manual disconnect, but NOT by a broken connection. If the connection is broken, MissionCommander will do its best to re-establish it. This callback should take no arguments.
- `'reconnect'` - Called just after a broken server connection is re-established. This callback takes one argument, the client identifier (string).
- `'message'` - As shown, this callback is triggered whenever a new message is received from the server. It should have one argument, that is of type `missioncommander.Message`.
- `servershutdown` - This callback is triggered JUST AFTER the server tells this client that it (the server) is shutting down. The client will be stopped after this callback returns.
- `'statechange'` - Called when the client state changes. This should take one argument, which is of type `missioncommander.ClientStateTransition`.

These verbs can take multiple forms -- they can start with `on`, are case-insensitive, and can contain dashes and underscores. For example, `on_connect`, `ConNEct`, and `onCon-nect` are all valid verbs for the `connect` event. (This is for compatibility with `onConnect`, `on-connect`, `connect`, etc etc. Use what you want.)

<br>

## Using the `Server` class

The `missioncommander.Server` class is, well, the *server* half of the connection. One server can host multiple unique clients. Again, configuration is done via setting instance variables.

---

### Configuring

First, instantiate an instance of `missioncommander.Server` and configure your parameters:
```python
import missioncommander

server = missioncommander.Servre()

server.interface = ''
server.port = 30_000
```

These are the only two available configuration options, and both are required. Not much else is needed. Interface can be an interface device name, or `''` or `'*'` for any.

---

### Starting

Server starting and stopping is equally as simple:

```python
server.start()

should_run = True
while should_run:
    try: input("ctrl+c to exit")
    except KeyboardInterrupt: should_run = False

server.stop()
```

---

### Messaging

Servers are the main hub connection to clients. Messages can be sent to an individual client, or `'*'` to broadcast to all. The message argument should be an instance of `missioncommander.Message`.

```python
server.send(
    '*',
    missioncommander.Message(
        'echo', { 'message': "Hello, world!" }
    )
)
```

---

### The `Server` class is a work in progress!
More features will be added in future releases.


<br>

---
---

<br>

# MissionCommander CLI

MissionCommander comes bundled with a simple CLI interface, for both the server and client classes. The CLI interface can be started with the command:

```bash
python3 -m missioncommander cli
```

### Interface

The CLI interface is a basic REPL, with a simple command syntax, following

For example, a quickstart could look like the following set of commands:

```
> server set interface ''
> server set port 30000
> server start
> 
> client set address 127.0.0.1
> client set port 30000
> client set client_id 'abcXYZ'
> client connect
> 
> server send 'echo' '{ "message": "hello" }'
```

---

### Client

The CLI commands for the client are as follows:
- `client set <key> <value>` - where `key` is one of `address`, `port`, `client_id`, `interface`, or `bind_port`
- `client get <key>` - same keys as above
- `client connect` - starts the connection
- `client disconnect` - stops the connection
- `client status` - the current status of the client
- `client help` - show these commands

---

### Server

The CLI commands for the server are as follows:
- `server set <key> <value>` - where `key` is one of `interface` or `port`
- `server get <key>` - same keys as above
- `server start` - starts the server
- `server stop` - stops the server
- `server status` - the current status of the server
- `server send <subj> <msg>` - broadcasts a message to all clients, where `subj` is the subject and `msg` is a stringified JSON dictionary
- `server help` - show these commands


<br>

---
---

<br>

# MissionCommander GUI

MissionCommander comes bundled with a simple GUI interface as well, for both the server and client classes. The GUI interface can be started with the command:

```bash
python3 -m missioncommander gui
```

---

### Interface

The interface comes with two tabs, one for the client and one for the server. It should be pretty self-explanatory.

---

### Client
TODO

---

### Server
TODO


<br>

---
---

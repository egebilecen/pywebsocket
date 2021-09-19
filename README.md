# pywebsocket
Simple websocket server library written in Python.
<br><br>
Example Server Code: <br>
<b>main.py</b>
```python
from pywebsocket import WebsocketServer

def on_client_connect(server : WebsocketServer, 
                      client : WebsocketServer.ClientSocket) -> None:
    # do stuff
    pass

def on_client_disconnect(server : WebsocketServer, 
                         client : WebsocketServer.ClientSocket) -> None:
    # do more stuff
    pass

def on_client_data(server : WebsocketServer, 
                   client : WebsocketServer.ClientSocket,
                   data) -> None:
    # echo client's message
    print("Received from client:", data)
    server.send_string(client.get_id(), data)

server = WebsocketServer("192.168.1.2", 3630,
                         client_buffer_size  = 1024,
                         pass_data_as_string = True,
                         debug               = True)

server.set_special_handler("client_connect",    on_client_connect)
server.set_special_handler("client_disconnect", on_client_disconnect)
server.set_special_handler("client_data",       on_client_data)

server.start()

# prevent main from exiting
while 1: pass
```

# Documentation
Please refer to <a href="https://egebilecen.github.io/pywebsocket/classpywebsocket_1_1_websocket_server.html">here</a> for class documentation.
<hr>

<b>Notes:</b>
* Doesn't support <b>HTTPS</b> connection.

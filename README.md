# pywebsocket
Simple websocket server library written in Python.

Example Server Code: <br>
**main.py**

from pywebsocket.server import WebsocketServer, WebsocketClient

```python
def on_client_connect(server : WebsocketServer, 
                    client : WebsocketClient) -> None:
    # Add this client's socket id to a channel's user list.
    server.default_channel["users"].append(client.get_id())
    client.data["current_channel"] = server.default_channel

    print(server.channel_list)

def on_client_disconnect(server : WebsocketServer, 
                        client : WebsocketClient) -> None:
    # Remove the client from the channel it is currently in.
    client.data["current_channel"]["users"].remove(client.get_id())

    print(server.channel_list)

def on_client_data(server : WebsocketServer, 
                client : WebsocketClient,
                data) -> None:
    # Echo client's message.
    print("Received from client:", data)
    server.send_string(client.get_id(), data)

server = WebsocketServer("192.168.1.2", 3630,
                        client_buffer_size  = 1024,
                        pass_data_as_string = True,
                        debug               = True)

# You can set your own variables to server like below:
server.channel_list = {
    "general" : {
        "users" : []
    },
    "news" : {
        "users" : []
    }
}
server.default_channel = server.channel_list["general"]

server.set_special_handler("client_connect",    on_client_connect)
server.set_special_handler("client_disconnect", on_client_disconnect)
server.set_special_handler("client_data",       on_client_data)

server.start()
```

# Installation
Install via `pip`:

```
pip install pywebsocket
```

Or you can install manually by cloning this repo and running this command:

```
python3 setup.py install
```

# Documentation
Please refer to [here](https://egebilecen.github.io/pywebsocket/namespaces.html) for documentation.

---

**Notes:**
* Doesn't support **HTTPS** connection.
* Server does support receiving fragmented messages but it doesn't support sending fragmented messages.

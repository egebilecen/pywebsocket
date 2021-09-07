from pywebsocket import WebsocketServer

server = WebsocketServer(debug=True)
server.start()

while 1:
    try:
        pass
    except KeyboardInterrupt:
        server.stop()

from pywebsocket import WebsocketServer

server = WebsocketServer(debug=True)
server.start()

while 1:
    try:
        print(eval(input(">> ")))
    except Exception as ex:
        print("EXCEPTION - "+str(ex))
    except KeyboardInterrupt:
        server.stop()

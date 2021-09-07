"""
    Author: Ege Bilecen
    Date  : 06.09.2021
"""

from typing import Callable
from random import randint
from sys    import maxsize as MAX_UINT_VALUE
import socket
import base64
import hashlib
import threading

class WebsocketServer:
    MAGIC_NUMBER = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self,
                 ip                 : str  = "",
                 port               : int  = 3630,
                 debug              : bool = False,
                 client_buffer_size : int = 2048) -> None:
        # Server Variables
        self._server             = None
        self._ip                 = ip
        self._port               = port
        self._addr               = (self._ip, self._port)
        self._thread_list        = {}
        self._is_running         = False
        self._debug              = debug

        # Client Variables
        self._client_socket_list = {}
        self._client_thread_list = {}
        self._client_buffer_size = client_buffer_size

        # Handler Variables
        self._special_handler_list = {
            "loop"              : None,
            "client_connect"    : None,
            "client_disconnect" : None
        }

    """
        Private Method(s)
    """
    @staticmethod
    def _client_handler(cls       : "WebsocketServer",
                        socket_id : int) -> None:
        cls._print_log("_client_handler()", "A new thread has been started for socket id {}.".format(socket_id))
        client_socket = cls._client_socket_list[socket_id]["socket"]

        while cls._is_running \
        and   cls._client_thread_list[socket_id]["status"] == 1:
            data = client_socket.recv(cls._client_buffer_size)

            if not data:
                cls._print_log("_client_handler()", "Socket id {} has left from server.".format(socket_id))
                
                client_socket.close()
                cls._client_socket_list.pop(socket_id)
                
                if cls._special_handler_list["client_disconnect"] is not None:
                    cls._print_log("_client_handler()", "Calling client_disconnect special handler for socket id {}.".format(socket_id))
                    cls._special_handler_list["client_disconnect"](socket_id)

                break

        cls._print_log("_client_handler()", "Thread of socket id {} has been terminated.".format(socket_id))
        cls._client_thread_list.pop(socket_id)

    @staticmethod
    def _create_handshake(http_request : bytes) -> bytes:
        http_data = WebsocketServer._parse_http_request(http_request.decode("ascii"))

        # ----| HTTP Request Validity Checks |----
        # (https://datatracker.ietf.org/doc/html/rfc6455#section-4.1)
        # HTTP request must be GET request
        if http_data["Method"] != "GET":                       return b""

        # HTTP version must be at least 1.1
        if float(http_data["Version"].split("/")[1]) < 1.1:    return b""

        # HTTP request must contain "Host" field
        if "Host" not in http_data:                            return b""

        # HTTP request must contain "Upgrade" field with the "websocket" keyword included
        # in it's value
        if "Upgrade" not in http_data:                         return b""
        elif "websocket" not in http_data["Upgrade"].lower():  return b""

        # HTTP request must include "Connection" field
        if "Connection" not in http_data:                      return b""
        elif "upgrade" not in http_data["Connection"].lower(): return b""

        # HTTP request must include "Sec-WebSocket-Key" field
        if "Sec-WebSocket-Key" not in http_data:               return b""

        # HTTP request must include "Sec-WebSocket-Version" field and it's value must be 13
        if "Sec-WebSocket-Version" not in http_data:           return b""
        elif http_data["Sec-WebSocket-Version"] != "13":       return b""

        # Sec-WebSocket-Key field's value must be 16 bytes when decoded
        websocket_key         = http_data["Sec-WebSocket-Key"]
        websocket_key_decoded = base64.b64decode(websocket_key)

        if len(websocket_key_decoded) != 16:                   return b""

        sha_1 = hashlib.sha1()
        sha_1.update((websocket_key + WebsocketServer.MAGIC_NUMBER).encode("ascii"))
        handshake_key = sha_1.hexdigest()

        handshake_response  = "HTTP/1.1 101 Switching Protocols\r\n"
        handshake_response += "Upgrade: websocket\r\n"
        handshake_response += "Connection: Upgrade\r\n"
        handshake_response += "Sec-WebSocket-Accept: {}\r\n".format(handshake_key)

        return handshake_response.encode("ascii")

    @staticmethod
    def _parse_http_request(http_request : str) -> dict[str, str]:
        request_split = [elem for elem in http_request.split("\r\n") if elem]
        method_url_version_split = request_split[0].split(" ")

        ret_val = {
            "Method"  : method_url_version_split[0],
            "Path"    : method_url_version_split[1],
            "Version" : method_url_version_split[2]
        }

        for line in request_split[1:]:
            key_val_split = line.split(":")
            ret_val[key_val_split[0]] = key_val_split[1].strip()

        return ret_val

    def _print_log(self, title, msg) -> None:
        if self._debug:
            print("pywebsocket - {} - {}".format(title, msg))

    def _generate_socket_id(self) -> int:
        rand_int = randint(0, MAX_UINT_VALUE)

        if rand_int in self._client_socket_list:
            return self._generate_socket_id()

        return rand_int

    """
        Public Method(s)
    """
    def set_special_handler(self, 
                            handler_name : str, 
                            func         : Callable) -> None:
        if handler_name not in self._special_handler_list:
            raise KeyError("\"{}\" not in special handlers list.".format(handler_name))

        if not callable(func):
            raise TypeError("Param func is not callable.")

        self._special_handler_list[handler_name] = func

    def stop(self) -> None:
        self._is_running = False

    def start(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind(self._addr)

        self._print_log("start()", "Socket binded.")

        self._server.listen()

        self._print_log("start()", "Server listening for connection(s).")

        if self._special_handler_list["loop"] is not None:
            self._print_log("start()", "Starting special handler \"loop\".")
            self._special_handler_list["loop"](self._socket_list)

        self._is_running = True

        def impl() -> None:
            self._print_log("start() - impl()", "Thread for handling handshakes is running.")

            while self._is_running \
            and   self._thread_list["handshake"]["status"] == 1:
                conn, addr = self._server.accept()

                self._print_log("start()", "New connection: {}:{}.".format(addr[0], addr[1]))

                handshake_request = conn.recv(2048)
                handshake = WebsocketServer._create_handshake(handshake_request)

                # Not a valid request since method to generate websocket handshake returned nothing
                if handshake == b"":
                    conn.close()
                    continue

                conn.send(handshake)

                client_socket_id = self._generate_socket_id()
                client_thread    = threading.Thread(target=WebsocketServer._client_handler, args=(self, client_socket_id))
                
                self._client_socket_list[client_socket_id] = {
                    "socket" : conn,
                    "addr"   : addr,
                    "data"   : {}
                }

                self._client_thread_list[client_socket_id] = {
                    "status" : 1,
                    "thread" : client_thread
                }

                client_thread.daemon = False
                client_thread.start()
        
            self._print_log("start() - impl()", "Closing the server.")
            self._server.close()

        handshake_thread = threading.Thread(target=impl, args=())

        self._thread_list["handshake"] = {
            "status" : 1,
            "thread" : handshake_thread
        }

        handshake_thread.daemon = False
        handshake_thread.start()

"""
    Author: Ege Bilecen
    Date  : 06.09.2021
"""

from array import array
from typing import Callable, Type
import socket
import threading

class WebsocketServer:
    def __init__(self,
                 ip    : str  = "",
                 port  : int  = 3630,
                 debug : bool = False) -> None:
        # Server Variables
        self._server      = None
        self._ip          = ip
        self._port        = port
        self._addr        = (self._ip, self._port)
        self._thread_list = {}
        self._is_running  = False
        self._debug       = debug

        # Socket Variables
        self._socket_list        = {}
        self._socket_thread_list = {}

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
    def _client_handler(cls : "WebsocketServer") -> None:
        pass

    @staticmethod
    def _create_handshake(http_request : bytes) -> bytes:
        http_data = WebsocketServer._parse_http_request(http_request.decode("ascii"))

        print(http_data)

    @staticmethod
    def _parse_http_request(http_request : str) -> dict[str, str]:
        request_split = [elem for elem in http_request.split("\r\n") if elem]
        method_url_version_split = request_split[0].split(" ")

        ret_val = {
            "method"  : method_url_version_split[0],
            "path"    : method_url_version_split[1],
            "version" : method_url_version_split[2]
        }

        for line in request_split[1:]:
            key_val_split = line.split(":")

            ret_val[key_val_split[0].lower()] = key_val_split[1].strip()

        return ret_val

    def _print_log(self, title, msg) -> None:
        if self._debug:
            print("pywebsocket - {} - {}".format(title, msg))

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

    def run(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind(self._addr)

        self._print_log("run()", "Socket binded.")

        self._server.listen()

        self._print_log("run()", "Server listening for connection(s).")

        if self._special_handler_list["loop"] is not None:
            self._print_log("run()", "Starting special handler \"loop\".")
            self._special_handler_list["loop"](self._socket_list)

        while 1:
            conn, addr = self._server.accept()

            self._print_log("run()", "New connection: {}:{}.".format(addr[0], addr[1]))

            handshake_request = conn.recv(1024)
            handshake = WebsocketServer._create_handshake(handshake_request)

            # Not a valid request since method to generate websocket handshake returned nothing
            if handshake == b"":
                conn.close()
                continue

            client_thread = threading.Thread(target=WebsocketServer._client_handler, args=(self,))
            client_thread.daemon = False
            client_thread.start()

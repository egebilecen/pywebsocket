"""
    Author: Ege Bilecen
    Date  : 06.09.2021
"""

from typing import type_check_only


class WebsocketServer:
    def __init__(self,
                 ip    : str  = "",
                 port  : int  = 3630,
                 debug : bool = False):
        # Server Variables
        self._ip          = ip
        self._port        = port
        self._addr        = (self.IP, self.PORT)
        self._thread_list = {}
        self._is_running  = False
        self._debug       = debug

        # Socket Variables
        self._socket_list        = {}
        self._socket_thread_list = {}

        # Handler Variables
        self._special_handler_list = {
            "client_connect"    : None,
            "client_disconnect" : None
        }

    def set_special_handler(self, handler_name, func):
        if handler_name not in self._special_handler_list:
            raise KeyError("\"{}\" not in special handlers list.".format(handler_name))

        if not callable(func):
            raise TypeError("Param func is not callable.")

        self._special_handler_list[handler_name] = func

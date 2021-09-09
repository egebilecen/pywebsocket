"""
    Author: Ege Bilecen
    Date  : 06.09.2021
    TODO  : Section 5.4, Section 5.5.2, Section 5.5.3, Section 7
"""

from typing import Callable, Any
from random import randint
from sys    import maxsize as MAX_UINT_VALUE
import socket
import base64
import hashlib
import struct
import threading

class WebsocketServer:
    MAGIC_NUMBER = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self,
                 ip                 : str  = "",
                 port               : int  = 3630,
                 debug              : bool = False,
                 client_buffer_size : int  = 2048) -> None:
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
        LOG_TITLE = "_client_handler() - [Socket ID: {}]".format(socket_id)

        cls._print_log(LOG_TITLE, "A new thread has been started for the socket.")
        socket_dict   = cls._client_socket_list[socket_id]
        client_socket = socket_dict["socket"]

        if cls._special_handler_list["client_connect"] is not None:
            cls._print_log(LOG_TITLE, "Calling \"client_connect\" special handler for the socket.")
            cls._special_handler_list["client_connect"](socket_dict)

        while cls._is_running \
        and   cls._client_thread_list[socket_id]["status"] == 1:
            data = client_socket.recv(cls._client_buffer_size)

            if not data:
                cls._print_log(LOG_TITLE, "The socket has left from server.")
                cls._close_client_socket(socket_id)
                break
            else:
                try:
                    client_data = WebsocketServer._decode_packet(data)
                    cls._print_log(LOG_TITLE, "The socket has sent {} bytes long packet.".format(len(client_data)))
                except ValueError as ex:
                    if str(ex) != "Closing connection":
                        cls._print_log(LOG_TITLE, "The socket has sent an inappropriate packet. Closing connection. ({})".format(str(ex)))
                    else:
                        cls._print_log(LOG_TITLE, "The socket has left from server. (PACKET RELATED: {})".format(str(ex)))
                    
                    cls._close_client_socket(socket_id)
                    break

        cls._print_log(LOG_TITLE, "The socket's thread has been terminated.")
        cls._client_thread_list.pop(socket_id)

    @staticmethod
    def _create_handshake(http_request : bytes) -> bytes:
        http_data = WebsocketServer._parse_http_request(http_request.decode())

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

        sha1 = hashlib.sha1()
        sha1.update((websocket_key + WebsocketServer.MAGIC_NUMBER).encode())
        sha1_bytes = sha1.digest()
        handshake_key = base64.b64encode(sha1_bytes).decode()

        handshake_response  = "HTTP/1.1 101 Switching Protocols\r\n"
        handshake_response += "Upgrade: websocket\r\n"
        handshake_response += "Connection: Upgrade\r\n"
        handshake_response += "Sec-WebSocket-Accept: {}\r\n".format(handshake_key)
        handshake_response += "\r\n"

        return handshake_response.encode()

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

    @staticmethod
    def _encode_data(data : bytes) -> bytes:
        packet   = b""
        data_len = len(data)

        FIN    = 0b10000000
        RSV1   = 0b00000000
        RSV2   = 0b00000000
        RSV3   = 0b00000000
        OPCODE = 0b00000010
        EXT_16 = 0x7E
        EXT_64 = 0x7F
        HEADER = FIN | RSV1 | RSV2 | RSV3 | OPCODE

        packet += HEADER

        if   data_len <= 125:
            packet += data_len
        elif data_len <= 0xFFFF:
            packet += EXT_16
            packet += struct.pack("!H", data_len)
        elif data_len <= 0xFFFFFFFFFFFFFFFF:
            packet += EXT_64
            packet += struct.pack("!Q", data_len)
        else:
            raise ValueError("Data length can't be bigger than 0xFFFFFFFFFFFFFFFF.")

        packet.append(data)

        return bytes(packet)
        
    @staticmethod
    def _decode_packet(packet : bytes) -> bytes:
        header = struct.unpack("!H", packet[:2])[0]
        packet = packet[2:]

        FIN    = (header >> 15) & 0x01
        RSV1   = (header >> 14) & 0x01
        RSV2   = (header >> 13) & 0x01
        RSV3   = (header >> 12) & 0x01
        OPCODE = (header >> 8)  & 0x0F
        MASK   = (header >> 7)  & 0x01
        LEN    = (header >> 0)  & 0x7F

        # Received unknown OPCODE
        if   OPCODE < 0x01 and OPCODE > 0x0F:
            raise ValueError("Unknown OPCODE 0x{:02x}".format(OPCODE))
        elif OPCODE == 0x08:
            raise ValueError("Closing connection")

        # Client must send masked frame
        if MASK != 1:
            raise ValueError("Client must send masked frames (MASK != 1)")

        if   LEN == 126: 
            LEN = struct.unpack("!H", packet[:2])[0]
            packet = packet[2:]
        elif LEN == 127:
            LEN = struct.unpack("!Q", packet[:8])[0]
            packet = packet[8:]

        MASK_KEY = packet[:4]
        packet   = packet[4:]

        payload      = packet[:LEN]
        payload_data = []

        for i, byte in enumerate(payload):
            payload_data.append(byte ^ MASK_KEY[i % 4])

        return payload_data

    def _print_log(self, title, msg) -> None:
        if self._debug:
            print("pywebsocket - {} - {}".format(title, msg))

    def _generate_socket_id(self) -> int:
        rand_int = randint(0, MAX_UINT_VALUE)

        if rand_int in self._client_socket_list:
            return self._generate_socket_id()

        return rand_int

    
    def _close_client_socket(self, 
                            socket_id            : int,
                            call_special_handler : bool = True):
        socket_dict   = self._client_socket_list[socket_id]
        client_socket = self._client_socket_list[socket_id]["socket"]

        client_socket.close()
        self._client_socket_list.pop(socket_id)
        self._client_thread_list[socket_id]["status"] = 0
        
        if  call_special_handler \
        and self._special_handler_list["client_disconnect"] is not None:
            self._print_log("_close_client_socket()", "Calling \"client_disconnect\" special handler for socket id {}.".format(socket_id))
            self._special_handler_list["client_disconnect"](socket_dict)

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

        self._print_log("set_special_handler()", "Special handler for \"{}\" has been set.".format(handler_name))
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
                    self._print_log("start()", "Connection {}:{} didn't send a valid handshake request. Closing connection.".format(addr[0], addr[1]))
                    conn.close()
                    continue

                conn.send(handshake)

                client_socket_id = self._generate_socket_id()
                client_thread    = threading.Thread(target=WebsocketServer._client_handler, args=(self, client_socket_id))
                
                self._client_socket_list[client_socket_id] = {
                    "id"     : client_socket_id,
                    "socket" : conn,
                    "addr"   : addr,
                    "data"   : {}
                }

                self._client_thread_list[client_socket_id] = {
                    "id"     : client_socket_id,
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

"""
    Author: Ege Bilecen
    Available Special Handlers:
    * loop
    * client_connect
    * client_disconnect
    * client_data
    TODO  : RFC6455
            * Section 5.4
              Section 5.5.2
              Section 5.5.3
              Section 7
"""

from typing import Callable, Union, Optional
from random import randint
from sys    import maxsize as MAX_UINT_VALUE
import socket
import base64
import hashlib
import struct
import json
import threading

import custom_types

## WebsocketServer
# Simple Websocket Server.
class WebsocketServer:
    MAGIC_NUMBER  = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    ENCODING_TYPE = "utf-8" 

    ## ClientSocket
    # Contains the variables for a client socket.
    class ClientSocket:
        def __init__(self, 
                     id     : int,
                     socket : socket.socket,
                     addr   : tuple):
            # Socket ID of client
            self._id     = id

            # Socket object of client
            self._socket = socket

            # Address tuple of client
            self._addr   = addr

            # Dictionary object to hold data in client.
            self.data    = {}

        ## Gets the socket ID of client.
        def get_id(self) -> int:
            return self._id

        ## Gets the socket object of client.
        def get_socket(self) -> socket.socket:
            return self._socket

        ## Gets the address pair of client.
        def get_addr(self) -> tuple:
            return self._addr

    ## Constructor of WebsocketServer.
    # @param ip IP address of the server.
    # @param port Port number that will be used for communication.
    # @param client_buffer_size Buffer size for the data sent from client.
    # @param pass_data_as_string Data sent from client will be passed as UTF-8 string to "client_data" special handler's data param if set to True. Otherwise a byte array will be passed.
    # @param debug Enable/disable debug messages.
    def __init__(self,
                 ip                  : str  = "",
                 port                : int  = 3630,
                 client_buffer_size  : int  = 2048,
                 pass_data_as_string : bool = False,
                 debug               : bool = False) -> None:
        # Server Variables
        self._server              = None
        self._ip                  = ip
        self._port                = port
        self._addr                = (self._ip, self._port)
        self._thread_list         = {}
        self._is_running          = False
        self._pass_data_as_string = pass_data_as_string
        self._debug               = debug

        # Client Variables
        self._client_socket_list = {}
        self._client_thread_list = {}
        self._client_buffer_size = client_buffer_size

        # Handler Variables
        self._special_handler_list = {
            "loop"              : None,
            "client_connect"    : None,
            "client_disconnect" : None,
            "client_data"       : None
        }

    """
        --- Private Method(s)
    """
    ## Function that will handle data sent from client.
    # @param socket_id Client's given socket ID after sucessful handshake.
    @staticmethod
    def _client_handler(cls       : "WebsocketServer",
                        socket_id : int) -> None:
        LOG_TITLE = "_client_handler() - [Socket ID: {}]".format(socket_id)

        cls._print_log(LOG_TITLE, "A new thread has been started for the socket.")
        client        = cls._client_socket_list[socket_id]
        client_socket = client.get_socket()

        if cls._special_handler_list["client_connect"] is not None:
            cls._print_log(LOG_TITLE, "Calling \"client_connect\" special handler for the socket.")
            cls._special_handler_list["client_connect"](cls, client)

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

                    if cls._pass_data_as_string: client_data = client_data.decode(WebsocketServer.ENCODING_TYPE)

                    if cls._special_handler_list["client_data"] is not None:
                        cls._print_log(LOG_TITLE, "Calling \"client_data\" special handler for the socket.")
                        cls._special_handler_list["client_data"](cls, client, client_data)
                except ValueError as ex:
                    if str(ex) != "Closing connection":
                        cls._print_log(LOG_TITLE, "The socket has sent an inappropriate packet. Closing connection. ({})".format(str(ex)))
                    else:
                        cls._print_log(LOG_TITLE, "The socket has left from server. (PACKET RELATED: {})".format(str(ex)))
                    
                    cls._close_client_socket(socket_id)
                    break

        cls._print_log(LOG_TITLE, "The socket's thread has been terminated.")
        cls._client_thread_list.pop(socket_id)

    ## Creates handshake from HTTP request of client.
    # @param http_request HTTP request sent from client.
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

    ## Parses HTTP request into key/value (dict) pair.
    # @param http_request HTTP request string.
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

    ## Encodes the data that will be sent to client according to websocket packet structure and rules.
    # @param data Data that will be sent to client.
    # @param frame_type Type of frame. It can only be FrameType.TEXT_FRAME or FrameType.BINARY_FRAME. If data sent as a FrameType.TEXT_FRAME, client will receive data as UTF-8 string. If data sent as a FrameType.BINARY_FRAME, client will receive data as byte array.
    # @param opcode_ovr OPCODE override. OPCODE will be set to this value if value is not None.
    @staticmethod
    def _encode_data(data       : bytes, 
                     frame_type : custom_types.FrameType = custom_types.FrameType.TEXT_FRAME,
                     opcode_ovr : Optional[int]          = None) -> bytes:
        packet   = bytearray()
        data_len = len(data)

        FIN    = 0b10000000
        RSV1   = 0b00000000
        RSV2   = 0b00000000
        RSV3   = 0b00000000
        OPCODE = 0b00000001 if frame_type == custom_types.FrameType.TEXT_FRAME else 0b00000010
        EXT_16 = 0x7E
        EXT_64 = 0x7F

        if opcode_ovr is not None: OPCODE = opcode_ovr

        HEADER = FIN | RSV1 | RSV2 | RSV3 | OPCODE

        packet.append(HEADER)

        if   data_len <= 125:
            packet.append(data_len)
        elif data_len <= 0xFFFF:
            packet.append(EXT_16)
            packet.extend(struct.pack("!H", data_len))
        elif data_len <= 0xFFFFFFFFFFFFFFFF:
            packet.append(EXT_64)
            packet.extend(struct.pack("!Q", data_len))
        else:
            raise ValueError("Data length can't be bigger than 0xFFFFFFFFFFFFFFFF.")

        packet.extend(data)

        return bytes(packet)
    
    ## Decodes the packet sent from client.
    # @param packet Packet sent from client.
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
        payload_data = bytearray()

        for i, byte in enumerate(payload):
            payload_data.append(byte ^ MASK_KEY[i % 4])

        return bytes(payload_data)
    
    ## prints log to console if debug is enabled.
    # @param title Title.
    # @param msg Message.
    def _print_log(self, 
                   title : str, 
                   msg   : str) -> None:
        if self._debug:
            print("pywebsocket - {} - {}".format(title, msg))

    ## generates random number between 0 and max UINT value of the running system.
    # @warning This method will cause endless loop if there are no available numbers left.
    def _generate_socket_id(self) -> int:
        rand_int = randint(0, MAX_UINT_VALUE)

        if rand_int in self._client_socket_list:
            return self._generate_socket_id()

        return rand_int

    ## Closes the connection with client.
    # @param socket_id Client's given socket ID after sucessful handshake.
    # @param call_special_handler If set to True, "client_disconnect" special handler will be called. If set to False, no special handler will be called.
    def _close_client_socket(self, 
                             socket_id            : int,
                             call_special_handler : bool = True):
        client        = self._client_socket_list[socket_id]
        client_socket = client.get_socket()

        client_socket.send(WebsocketServer._encode_data(b"", opcode_ovr = 0x08))
        client_socket.close()
        self._client_socket_list.pop(socket_id)
        self._client_thread_list[socket_id]["status"] = 0
        
        if  call_special_handler \
        and self._special_handler_list["client_disconnect"] is not None:
            self._print_log("_close_client_socket()", "Calling \"client_disconnect\" special handler for socket id {}.".format(socket_id))
            self._special_handler_list["client_disconnect"](self, client)

    ## Checkes if socket_id is a valid socket ID. If not, it throws a KeyError exception.
    # @param socket_id Client's given socket ID after sucessful handshake.
    def _check_socket_id(self, 
                         socket_id : int) -> None:
        if socket_id not in self._client_socket_list:
            raise KeyError("Socket id {} not in client socket list.".format(socket_id))

    """
        --- Public Method(s)
    """
    ## Sets the callback function for special handlers.
    # @param handler_name Special handler's name.
    # @param func Callback function that will be called upon special cases. (Such as client connect etc.)
    def set_special_handler(self, 
                            handler_name : str, 
                            func         : Callable) -> None:
        if handler_name not in self._special_handler_list:
            raise KeyError("\"{}\" not in special handlers list.".format(handler_name))

        if not callable(func):
            raise TypeError("Param func is not callable.")

        self._print_log("set_special_handler()", "Special handler for \"{}\" has been set.".format(handler_name))
        self._special_handler_list[handler_name] = func

    ## Stops the server.
    def stop(self) -> None:
        self._is_running = False

    ## Starts the server.
    def start(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind(self._addr)

        self._print_log("start()", "Socket binded.")

        self._server.listen()

        self._print_log("start()", "Server listening for connection(s).")

        if self._special_handler_list["loop"] is not None:
            self._print_log("start()", "Starting special handler \"loop\".")
            self._special_handler_list["loop"](self)

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
                    conn.send("HTTP/1.1 400 Bad Request".encode())
                    conn.close()
                    continue

                conn.send(handshake)

                client_socket_id = self._generate_socket_id()
                client_thread    = threading.Thread(target=WebsocketServer._client_handler, args=(self, client_socket_id))
                
                self._client_socket_list[client_socket_id] = WebsocketServer.ClientSocket(client_socket_id, conn, addr)

                self._client_thread_list[client_socket_id] = {
                    "id"     : client_socket_id,
                    "status" : 1,
                    "thread" : client_thread
                }

                client_thread.daemon = True
                client_thread.start()
        
            self._print_log("start() - impl()", "Closing the server.")
            self._server.close()

        handshake_thread = threading.Thread(target=impl, args=())

        self._thread_list["handshake"] = {
            "status" : 1,
            "thread" : handshake_thread
        }

        handshake_thread.daemon = True
        handshake_thread.start()

    ## Sends the data to socket.
    # @param socket_id Socket ID of the client that will receive the data.
    # @param data Data that will be sent.
    # @param frame_type Type of frame. See WebsocketServer._encode_data for more information.
    def send_data(self, 
                  socket_id  : int,
                  data       : bytes,
                  frame_type : custom_types.FrameType = custom_types.FrameType.BINARY_FRAME) -> None:
        self._check_socket_id(socket_id)

        socket = self._client_socket_list[socket_id].get_socket()
        socket.send(WebsocketServer._encode_data(data, frame_type))

    ## Sends the data as string to socket.
    # @param socket_id Socket ID of the client that will receive the data.
    # @param str String that will be sent.
    def send_string(self,
                    socket_id : int,
                    str       : str) -> None:
        self.send_data(socket_id, str.encode(WebsocketServer.ENCODING_TYPE), custom_types.FrameType.TEXT_FRAME)

    ## Sends the data as JSON encoded string to socket.
    # @param socket_id Socket ID of the client that will receive the data.
    # @param dict Dictionary object that will be encoded as JSON string and sent to client.
    def send_json(self,
                  socket_id : int,
                  dict      : dict) -> None:
        self.send_string(socket_id, json.dumps(dict))

    ## Sends the data to all sockets.
    # @param send_func Method reference to call for sending the data. It can only be reference to WebsocketServer.send_data, WebsocketServer.send_string or WebsocketServer.send_json. Otherwise method will raise ValueError exception.
    # @param data Data that will be sent. It's type must match with the send_func reference method's.
    def send_to_all(self,
                    send_func : Callable,
                    data      : Union[bytes, str, dict]) -> None:
        if  send_func != self.send_data   \
        and send_func != self.send_string \
        and send_func != self.send_json:
            raise ValueError("Unknown function given")

        for socket_id in self._client_socket_list:
            send_func(socket_id, data)

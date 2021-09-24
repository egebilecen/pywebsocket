"""
    Author: Ege Bilecen
    Available Special Handlers:
    * loop
    * client_connect
    * client_disconnect
    * client_data
"""

from typing import Callable, Union
from random import randint
from sys    import maxsize as MAX_UINT_VALUE
import socket
import base64
import hashlib
import struct
import json
import threading

from . import custom_types
from . import exceptions

## WebsocketClient
# Contains the variables for a client that connected to the server.
class WebsocketClient:
    def __init__(self, 
                 id     : int,
                 socket : socket.socket,
                 addr   : tuple):
        ## Socket ID of client
        self._id     = id

        ## Socket object of client
        self._socket = socket

        ## Address tuple of client
        self._addr   = addr

        ## Is sending fragmented message?
        self._is_sending_fragmented_message = False

        ## Buffer for fragmented message
        self._fragmented_message_buffer     = bytearray()

        ## Dictionary object to hold data in client.
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

    ## Get is client sending fragmented message.
    def get_is_sending_fragmented_message(self) -> bool:
        return self._is_sending_fragmented_message

    ## Get fragmented message.
    def get_fragmented_message(self) -> bytes:
        return bytes(self._fragmented_message_buffer)

## WebsocketServer
# Simple Websocket Server.
class WebsocketServer:
    ## Globally Unique Identifier specified in RFC6455 The Websocket Protocol.
    MAGIC_NUMBER      = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    ## Encoding type for all string messages.
    ENCODING_TYPE     = "utf-8"

    ## Supported websocket version by server.
    WEBSOCKET_VERSION = 13

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
                break
            else:
                try:
                    decoded_packet = WebsocketServer._decode_packet(data)
                    client_data    = decoded_packet["data"]
                except exceptions.CLOSE_CONNECTION:
                    cls._print_log(LOG_TITLE, "The socket has left from server. (Sent close connection)")
                    break
                except exceptions.UNKNOWN_OPCODE:
                    cls._print_log(LOG_TITLE, "The socket has left from server. (Received unknown OPCODE)")
                    break
                except exceptions.MASK_ERROR:
                    cls._print_log(LOG_TITLE, "The socket has left from server. (Received unmasked frame)")
                    break
                except Exception as ex:
                    cls._print_log(LOG_TITLE, "The socket has left from server. (UNKNOWN EXCEPTION: {})".format(str(ex)))
                    break

                if decoded_packet["OPCODE"] == custom_types.ControlFrame.PING_FRAME:
                    cls._print_log(LOG_TITLE, "The socket has sent ping frame. Sending pong frame in response.")
                    client_socket.send(WebsocketServer._encode_data(client_data, custom_types.ControlFrame.PONG_FRAME))
                    continue

                # check if it is fragmented message
                if  decoded_packet["FIN"]    == 0x00 \
                and decoded_packet["OPCODE"] != custom_types.FrameType.CONTINUATION_FRAME:
                    client._is_sending_fragmented_message = True
                    client._fragmented_message_buffer.extend(client_data)
                    cls._print_log(LOG_TITLE, "The socket has initiated a fragmented message.")
                    continue
                elif decoded_packet["FIN"]    == 0x00 \
                and  decoded_packet["OPCODE"] == custom_types.FrameType.CONTINUATION_FRAME \
                and  client.get_is_sending_fragmented_message():
                    client._fragmented_message_buffer.extend(client_data)
                    cls._print_log(LOG_TITLE, "The socket has sent another fragmented message.")
                    continue
                elif decoded_packet["FIN"]    == 0x01 \
                and  decoded_packet["OPCODE"] == custom_types.FrameType.CONTINUATION_FRAME \
                and  client.get_is_sending_fragmented_message():
                    client._is_sending_fragmented_message = False
                    client._fragmented_message_buffer.extend(client_data)
                    cls._print_log(LOG_TITLE, "The socket has completed the fragmented message.")

                    client_data = client.get_fragmented_message()
                    client._fragmented_message_buffer = bytearray() # clear the buffer

                if client_data == b"": continue

                cls._print_log(LOG_TITLE, "The socket has sent {} bytes long data.".format(len(client_data)))

                if cls._pass_data_as_string: client_data = client_data.decode(WebsocketServer.ENCODING_TYPE)

                if cls._special_handler_list["client_data"] is not None:
                    cls._print_log(LOG_TITLE, "Calling \"client_data\" special handler for the socket.")
                    cls._special_handler_list["client_data"](cls, client, client_data)
        
        cls._close_client_socket(socket_id)
        cls._print_log(LOG_TITLE, "The socket's thread has been terminated.")

    ## Creates handshake from HTTP request of client.
    # @param http_request HTTP request sent from client.
    @staticmethod
    def _create_handshake(http_request : bytes) -> bytes:
        http_data = WebsocketServer._parse_http_request(http_request.decode(WebsocketServer.ENCODING_TYPE))

        # HTTP Request Validity Checks
        # (https://datatracker.ietf.org/doc/html/rfc6455#section-4.1)
        # HTTP request must be GET request
        if http_data["Method"] != "GET":                       raise exceptions.HANDSHAKE.INVALID_METHOD("HTTP request must be GET request. Received {} request.".format(http_data["Method"]))

        # HTTP version must be at least 1.1
        if float(http_data["Version"].split("/")[1]) < 1.1:    raise exceptions.HANDSHAKE.HTTP_VERSION_ERROR("HTTP version must be at least 1.1. Client's HTTP version: {}.".format(http_data["Version"]))

        # HTTP request must contain "Host" field
        if "Host" not in http_data:                            raise exceptions.HANDSHAKE.REQUIRED_FIELD_MISSING("Host field is missing.")

        # HTTP request must contain "Upgrade" field with the "websocket" keyword included
        # in it's value
        if "Upgrade" not in http_data:                         raise exceptions.HANDSHAKE.REQUIRED_FIELD_MISSING("Upgrade field is missing.")
        elif "websocket" not in http_data["Upgrade"].lower():  raise exceptions.HANDSHAKE.FIELD_VALUE_MISMATCH("Upgrade field's value must be \"websocket\".")

        # HTTP request must include "Connection" field
        if "Connection" not in http_data:                      raise exceptions.HANDSHAKE.REQUIRED_FIELD_MISSING("Connection field is missing.")
        elif "upgrade" not in http_data["Connection"].lower(): raise exceptions.HANDSHAKE.FIELD_VALUE_MISMATCH("Connection field's value include \"upgrade\".")

        # HTTP request must include "Sec-WebSocket-Key" field
        if "Sec-WebSocket-Key" not in http_data:               raise exceptions.HANDSHAKE.REQUIRED_FIELD_MISSING("Sec-WebSocket-Key field is missing.")

        # HTTP request must include "Sec-WebSocket-Version" field and it's value must match
        # with server's.
        version_error_str = "Client's websocket version doesn't match with server's. (Server's version: {}, Client's version: {})".format(WebsocketServer.WEBSOCKET_VERSION, http_data["Sec-WebSocket-Version"])
        try:
            websocket_version_list = [int(elem.strip()) for elem in http_data["Sec-WebSocket-Version"].split(",") if elem]
        except:
            raise exceptions.HANDSHAKE.WEBSOCKET_VERSION_ERROR(version_error_str)

        if "Sec-WebSocket-Version" not in http_data:                          raise exceptions.HANDSHAKE.REQUIRED_FIELD_MISSING("Sec-WebSocket-Version field is missing.")
        elif WebsocketServer.WEBSOCKET_VERSION not in websocket_version_list: raise exceptions.HANDSHAKE.WEBSOCKET_VERSION_ERROR(version_error_str)

        # Sec-WebSocket-Key field's value must be 16 bytes when decoded
        websocket_key         = http_data["Sec-WebSocket-Key"]
        websocket_key_decoded = base64.b64decode(websocket_key)

        if len(websocket_key_decoded) != 16: raise ValueError("Sec-WebSocket-Key field's value must be 16 bytes when decoded.")

        sha1 = hashlib.sha1()
        sha1.update((websocket_key + WebsocketServer.MAGIC_NUMBER).encode(WebsocketServer.ENCODING_TYPE))
        sha1_bytes = sha1.digest()

        handshake_key = base64.b64encode(sha1_bytes).decode(WebsocketServer.ENCODING_TYPE)

        handshake_response  = "HTTP/1.1 101 Switching Protocols\r\n"
        handshake_response += "Upgrade: websocket\r\n"
        handshake_response += "Connection: Upgrade\r\n"
        handshake_response += "Sec-WebSocket-Accept: {}\r\n".format(handshake_key)
        handshake_response += "\r\n"

        return handshake_response.encode(WebsocketServer.ENCODING_TYPE)

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
    # @param opcode OPCODE of frame.
    # @note If OPCODE set to FrameType.TEXT_FRAME, client will receive data as UTF-8 string. If OPCODE set to FrameType.BINARY_FRAME, client will receive data as byte array.
    # @warning - Raises exceptions.DATA_LENGTH_ERROR exception if data's length is bigger than 0xFFFFFFFFFFFFFFFF.
    # @warning - Do not forget that all control frames MUST have a payload length of 125 bytes or less and MUST NOT be fragmented.
    @staticmethod
    def _encode_data(data   : bytes, 
                     opcode : int) -> bytes:
        packet   = bytearray()
        data_len = len(data)

        FIN    = 0b10000000
        RSV1   = 0b00000000
        RSV2   = 0b00000000
        RSV3   = 0b00000000
        OPCODE = opcode
        EXT_16 = 0x7E
        EXT_64 = 0x7F

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
            raise exceptions.DATA_LENGTH_ERROR("Data length can't be bigger than 0xFFFFFFFFFFFFFFFF.")

        packet.extend(data)

        return bytes(packet)
    
    ## Decodes the packet sent from client.
    # @param packet Packet sent from client.
    # @warning Raises exceptions.UNKNOWN_OPCODE exception if an unknown OPCODE is detected. Raises exceptions.CLOSE_CONNECTION exception if close connection OPCODE is detected. Raises exceptions.MASK_ERROR exception if unmasked frame is detected.
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
            raise exceptions.UNKNOWN_OPCODE("Unknown OPCODE 0x{:02x}.".format(OPCODE))
        elif OPCODE == 0x08:
            raise exceptions.CLOSE_CONNECTION

        # Client must send masked frame
        if MASK != 1:
            raise exceptions.MASK_ERROR

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

        return {
            "FIN"    : FIN,
            "OPCODE" : OPCODE,
            "data"   : bytes(payload_data)
        }
    
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
    # @param status_code Status code for close frame. Pre-defined codes can be found in [here](https://datatracker.ietf.org/doc/html/rfc6455#section-7.4.1).
    # @param call_special_handler If set to True, "client_disconnect" special handler will be called. If set to False, no special handler will be called.
    def _close_client_socket(self, 
                             socket_id            : int,
                             status_code          : int  = 1000,
                             call_special_handler : bool = True):
        client        = self._client_socket_list[socket_id]
        client_socket = client.get_socket()

        client_socket.send(WebsocketServer._encode_data(struct.pack("!H", status_code), custom_types.ControlFrame.CLOSE_FRAME))
        
        client_socket.close()
        self._client_socket_list.pop(socket_id)
        
        self._client_thread_list[socket_id]["status"] = 0
        self._client_thread_list.pop(socket_id)
        
        if  call_special_handler \
        and self._special_handler_list["client_disconnect"] is not None:
            self._print_log("_close_client_socket()", "Calling \"client_disconnect\" special handler for socket id {}.".format(socket_id))
            self._special_handler_list["client_disconnect"](self, client)

    ## Checks if socket_id is a valid socket ID. If not, raises exceptions.INVALID_SOCKET_ID exception.
    # @param socket_id Client's given socket ID after sucessful handshake.
    def _check_socket_id(self, 
                         socket_id : int) -> None:
        if socket_id not in self._client_socket_list:
            raise exceptions.INVALID_SOCKET_ID("Socket id {} not in client socket list.".format(socket_id))

    """
        --- Public Method(s)
    """
    ## Sets the callback function for special handlers.
    # @param handler_name Special handler's name.
    # @param func Callback function that will be called upon special cases. (Such as client connect etc.)
    # @warning Raises KeyError exception if handler_name not in special handlers list. Raises exceptions.INVALID_METHOD exception if func paramater is not a callable.
    def set_special_handler(self, 
                            handler_name : str, 
                            func         : Callable) -> None:
        if handler_name not in self._special_handler_list:
            raise KeyError("\"{}\" not in special handlers list.".format(handler_name))

        if not callable(func):
            raise exceptions.INVALID_METHOD("Param func is not callable.")

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

                try:
                    handshake = WebsocketServer._create_handshake(handshake_request)
                except exceptions.HANDSHAKE.WEBSOCKET_VERSION_ERROR:
                    self._print_log("start()", "Connection {}:{}'s websocket version doesn't match with server's. Closing connection.".format(addr[0], addr[1]))
                    conn.send(("HTTP/1.1 400 Bad Request\r\nSec-WebSocket-Version: {}\r\n\r\n".format(WebsocketServer.WEBSOCKET_VERSION)).encode(WebsocketServer.ENCODING_TYPE))
                    conn.close()
                    continue
                except Exception as ex:
                    self._print_log("start()", "Connection {}:{} didn't send a valid handshake request. Closing connection. ({})".format(addr[0], addr[1], str(ex)))
                    conn.send("HTTP/1.1 400 Bad Request\r\n\r\n".encode(WebsocketServer.ENCODING_TYPE))
                    conn.close()
                    continue

                conn.send(handshake)

                client_socket_id = self._generate_socket_id()
                client_thread    = threading.Thread(target=WebsocketServer._client_handler, args=(self, client_socket_id))
                
                self._client_socket_list[client_socket_id] = WebsocketClient(client_socket_id, conn, addr)

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

        handshake_thread.daemon = False
        handshake_thread.start()

    ## Sends the data to socket.
    # @param socket_id Socket ID of the client that will receive the data.
    # @param data Data that will be sent.
    # @param frame_type Type of frame. See WebsocketServer._encode_data for more information.
    def send_data(self, 
                  socket_id  : int,
                  data       : bytes,
                  frame_type : custom_types.FrameType = custom_types.FrameType.BINARY_FRAME) -> None:
        if frame_type == custom_types.FrameType.CONTINUATION_FRAME:
            raise exceptions.INVALID_OPCODE("OPCODE cannot be continuation frame.")
        
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
    # @param send_func Method reference to call for sending the data. It can only be reference to WebsocketServer.send_data, WebsocketServer.send_string or WebsocketServer.send_json. Otherwise method will raise exceptions.INVALID_SEND_METHOD exception.
    # @param data Data that will be sent. It's type must match with the send_func reference method's.
    def send_to_all(self,
                    send_func : Callable,
                    data      : Union[bytes, str, dict]) -> None:
        if  send_func != self.send_data   \
        and send_func != self.send_string \
        and send_func != self.send_json:
            raise exceptions.INVALID_SEND_METHOD("Unknown send method given.")

        for socket_id in self._client_socket_list:
            send_func(socket_id, data)

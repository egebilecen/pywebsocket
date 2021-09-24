"""
    Author: Ege Bilecen
"""

## Raised when invalid method detected.
class INVALID_METHOD(Exception):
    pass

## Raised when WebsocketServer.send_to_all receives an invalid send method as parameter.
class INVALID_SEND_METHOD(Exception):
    pass

## Raised when length of data passed to WebsocketServer._encode_data is bigger than 0xFFFFFFFFFFFFFFFF.
class DATA_LENGTH_ERROR(Exception):
    pass

## Raised when an unknown OPCODE detected.
class UNKNOWN_OPCODE(Exception):
    pass

## Raised when an invalid OPCODE detected.
class INVALID_OPCODE(Exception):
    pass

## Raised when closing OPCODE detected.
class CLOSE_CONNECTION(Exception):
    pass

## Raised when unmasked frame detected.
class MASK_ERROR(Exception):
    pass

## Raised when socket id is not in client socket list.
class INVALID_SOCKET_ID(Exception):
    pass

## Exceptions related with opening handshake.
class HANDSHAKE:
    ## Raised when invalid HTTP method detected.
    class INVALID_METHOD(Exception):
        pass
    
    ## Raised when HTTP version doesn't match with requirements.
    class HTTP_VERSION_ERROR(Exception):
        pass
    
    ## Raised when client's websocket version doesn't supported by server.
    class WEBSOCKET_VERSION_ERROR(Exception):
        pass

    ## Raised when request doesn't have required field.
    class REQUIRED_FIELD_MISSING(Exception):
        pass
    
    ## Raised when a field's value doesn't match with expected value.
    class FIELD_VALUE_MISMATCH(Exception):
        pass

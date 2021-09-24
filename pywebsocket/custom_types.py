"""
    Author: Ege Bilecen
"""

## FrameType
# Contains the constants that specifies the frame type. Can be used as OPCODE.
class FrameType:
    CONTINUATION_FRAME = 0x00
    TEXT_FRAME         = 0x01
    BINARY_FRAME       = 0x02

## ControlFrame
# Contains the constants that specifies the control frames. Can be used as OPCODE.
class ControlFrame:
    CLOSE_FRAME = 0x08
    PING_FRAME  = 0x09
    PONG_FRAME  = 0x0A

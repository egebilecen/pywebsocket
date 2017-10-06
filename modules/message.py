import struct
import json

def decode(data):
    HEADER, = struct.unpack("!H",data[:2])
    data   = data[2:]

    FIN    = (HEADER >> 15) & 0x01
    RSV1   = (HEADER >> 14) & 0x01
    RSV2   = (HEADER >> 13) & 0x01
    RSV3   = (HEADER >> 12) & 0x01
    OPCODE = (HEADER >>  8) & 0x0F
    MASKED = (HEADER >>  7) & 0x01
    LEN    = (HEADER >>  0) & 0x7F

    if LEN == 126:
        LEN, = struct.unpack("!H",data[:2])
        data = data[2:]
    elif LEN == 127:
        LEN, = struct.unpack("!4H",data[:8])
        data = data[8:]

    print("[?] Message from client.\n","FIN: {}, RSV1: {}, RSV2: {}, RSV3: {}, OPCODE: {}, MASKED: {}, LEN: {}"
          .format(FIN, RSV1, RSV2, RSV3, OPCODE, MASKED, LEN), sep="",end="\n\n")

    if MASKED:
        MASK = struct.unpack("4B", data[:4])
        data = data[4:]
    else:
        MASK = (0, 0, 0, 0)

    payload = ""
    for i,c in enumerate(data):
        payload += chr(c ^ MASK[i%4])

    try:
        _data = json.loads(payload)
    except:
        _data = {"where":"null","data":{}}
        
    return (_data["where"], _data["data"])

def encode(data):
    data_length = len(data)

    FIN     = "1"
    RSV1    = "0"
    RSV2    = "0"
    RSV3    = "0"
    OPCODE  = "1"
    MASK    = "0001"
    LEN     = "0"
    LOOP    = 0

    # Set Length
    if data_length < 125:
        LEN  = str(bin(len(data))[2:].rjust(7, "0"))
        LOOP = 2
    elif data_length == 126:
        LEN  = str(bin(len(data))[2:].rjust(7+16, "0"))
        LOOP = 4
    elif data_length == 127:
        LEN  = str(bin(len(data))[2:].rjust(7+64, "0"))
        LOOP = 10

    ALL     = FIN+RSV1+RSV2+RSV3+OPCODE+MASK+LEN
    ENCODED = b"".join([struct.pack("B",int(ALL[i*8:i*8+8],2)) for i in range(LOOP)])

    print("[?] Message from server.\n","LEN: {}, ENCODED: {}".format(LEN,ENCODED),sep="",end="\n\n")
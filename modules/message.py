import struct

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
        LEN, = struct.unpack("!4H",data[:4])
        data = data[4:]

    print("FIN: {}, RSV1: {}, RSV2: {}, RSV3: {}, OPCODE: {}, MASKED: {}, LEN: {}".format(FIN, RSV1, RSV2, RSV3, OPCODE,
                                                                                          MASKED, LEN))

    if MASKED:
        MASK = struct.unpack("4B", data[:4])
        data = data[4:]
    else:
        MASK = (0, 0, 0, 0)

    payload = ""
    for i,c in enumerate(data):
        payload += chr(c ^ MASK[i%4])

    return payload.split(",")
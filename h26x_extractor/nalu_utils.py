from bitstring import BitStream, Bits


def more_rbsp_data(s: BitStream):
    if s.pos >= len(s):
        return False
    last_one_pos, = BitStream(s).rfind(Bits('0b1'))
    if last_one_pos is None or s.pos >= last_one_pos:
        return False

    return True

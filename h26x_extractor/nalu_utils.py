import numpy as np
from bitstring import BitStream, Bits


def more_rbsp_data(s: BitStream):
    if s.pos >= len(s):
        return False
    last_one_pos, = BitStream(s).rfind(Bits('0b1'))
    if last_one_pos is None or s.pos >= last_one_pos:
        return False

    return True


def _get_slice_type(slice_type):
    """
    Returns the clear name of the slice type
    """
    return {
        0: "P",
        1: "B",
        2: "I",
        3: "SP",
        4: "SI",
        5: "P",
        6: "B",
        7: "I",
        8: "SP",
        9: "SI",
    }.get(slice_type, "unknown")


def create_matrix(*dimensions, default_value=0, default_type=int):
    """
    create multiple v matrix
    """
    return np.full(tuple(dimensions), default_value, default_type)

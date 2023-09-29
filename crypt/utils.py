import hashlib

import rust_utils


def nalu_decode(nalu_data):
    """
    Get the Rbsp from the NAL unit.
    """
    return rust_utils.nalu_decode(nalu_data)
    rbsp_enc = nalu_data
    rbsp_dec = bytearray()
    i = 0
    i_max = len(rbsp_enc)
    while i < i_max:
        if (i + 2 < i_max) and (rbsp_enc[i] == 0 and rbsp_enc[i + 1] == 0 and rbsp_enc[i + 2] == 3):
            rbsp_dec.append(rbsp_enc[i])
            rbsp_dec.append(rbsp_enc[i + 1])
            i += 2
        else:
            rbsp_dec.append(rbsp_enc[i])
        i += 1
    return rbsp_dec


PREVENTION_THREE_BYTE = {b"\x00\x00\x00", b"\x00\x00\x01", b"\x00\x00\x02", b"\x00\x00\x03"}


def nalu_encode(data):
    return rust_utils.nalu_encode(data)
    data_raw = data
    data_enc = bytearray()

    i = 0
    i_max = len(data_raw)
    while i < i_max:
        if (i + 2 < i_max) and (data_raw[i] == 0 and data_raw[i + 1] == 0 and data_raw[i + 2] < 4):
            data_enc.append(data_raw[i])
            data_enc.append(data_raw[i + 1])
            data_enc.append(3)
            data_enc.append(data_raw[i + 2])
            i += 2
        else:
            data_enc.append(data_raw[i])
        i += 1
    return data_enc


def read_file(filename):
    with open(filename, "rb") as f:
        return bytearray(f.read())


def write_file(filename, data):
    with open(filename, "wb") as f:
        return f.write(data)


def is_same_file(*files):
    pre_hash = None
    for file in files:
        sha256 = hashlib.sha256()
        with open(file, "rb") as f:
            data = f.read(65536)  # 一次读取 64 KB 数据
            if not data:
                break
            sha256.update(data)

        curr_hash = sha256.hexdigest()
        if pre_hash is not None and curr_hash != pre_hash:
            return False
        pre_hash = curr_hash
    return True

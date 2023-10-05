import hashlib

import rust_utils


def nalu_decode(nalu_data: bytes) -> bytes:
    """
    Get the Rbsp from the NAL unit.
    """
    return rust_utils.nalu_decode(nalu_data)


def nalu_encode(data: bytes) -> bytes:
    return rust_utils.nalu_encode(data)


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

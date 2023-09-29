from h26x_extractor import h26x_parser
from crypt import utils


def decrypt(in_file, out_file, decrypt_func):
    process_file(in_file, out_file, decrypt_func)


def encrypt(in_file, out_file, encrypt_func):
    process_file(in_file, out_file, encrypt_func)


def process_file(in_file, out_file, func):
    ex = h26x_parser.H26xParser(in_file, verbose=True)

    # nals.append((pos, is4bytes, fb, nri, type))
    # (start, end, is4bytes, fb, nri, type)

    res = bytearray()
    data = utils.read_file(in_file)

    pre_start, pre_end = -1, -1

    for i, (start, end, is4bytes, fb, nri, nalu_type) in enumerate(ex.nalu_pos):
        if start != pre_end + 1:
            res.extend(data[pre_end + 1: start])

        processed_nalu = func(bytes(data[start: end + 1]), fb, nri, nalu_type)
        res.extend(processed_nalu)

        pre_start, pre_end = start, end

    if pre_end != len(data) - 1:
        res.extend(data[pre_end + 1:])

    utils.write_file(out_file, res)
import re
from pathlib import Path

from bitstring import BitStream

CoeffTokenTableLength_0_2 = [
    [1, 6, 8, 9, 10, 11, 13, 13, 13, 14, 14, 15, 15, 16, 16, 16, 16],
    [0, 2, 6, 8, 9, 10, 11, 13, 13, 14, 14, 15, 15, 15, 16, 16, 16],
    [0, 0, 3, 7, 8, 9, 10, 11, 13, 13, 14, 14, 15, 15, 16, 16, 16],
    [0, 0, 0, 5, 6, 7, 8, 9, 10, 11, 13, 14, 14, 15, 15, 16, 16]
]

CoeffTokenTableCode_0_2 = [
    [1, 5, 7, 7, 7, 7, 15, 11, 8, 15, 11, 15, 11, 15, 11, 7, 4],
    [0, 1, 4, 6, 6, 6, 6, 14, 10, 14, 10, 14, 10, 1, 14, 10, 6],
    [0, 0, 1, 5, 5, 5, 5, 5, 13, 9, 13, 9, 13, 9, 13, 9, 5],
    [0, 0, 0, 3, 3, 4, 4, 4, 4, 4, 12, 12, 8, 12, 8, 12, 8]
]

CoeffTokenTableLength_2_4 = [
    [2, 6, 6, 7, 8, 8, 9, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14],
    [0, 2, 5, 6, 6, 7, 8, 9, 11, 11, 12, 12, 13, 13, 14, 14, 14],
    [0, 0, 3, 6, 6, 7, 8, 9, 11, 11, 12, 12, 13, 13, 13, 14, 14],
    [0, 0, 0, 4, 4, 5, 6, 6, 7, 9, 11, 11, 12, 13, 13, 13, 14]
]

CoeffTokenTableCode_2_4 = [
    [3, 11, 7, 7, 7, 4, 7, 15, 11, 15, 11, 8, 15, 11, 7, 9, 7],
    [0, 2, 7, 10, 6, 6, 6, 6, 14, 10, 14, 10, 14, 10, 11, 8, 6],
    [0, 0, 3, 9, 5, 5, 5, 5, 13, 9, 13, 9, 13, 9, 6, 10, 5],
    [0, 0, 0, 5, 4, 6, 8, 4, 4, 4, 12, 8, 12, 12, 8, 1, 4]
]

CoeffTokenTableLength_4_8 = [
    [4, 6, 6, 6, 7, 7, 7, 7, 8, 8, 9, 9, 9, 10, 10, 10, 10],
    [0, 4, 5, 5, 5, 5, 6, 6, 7, 8, 8, 9, 9, 9, 10, 10, 10],
    [0, 0, 4, 5, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 10],
    [0, 0, 0, 4, 4, 4, 4, 4, 5, 6, 7, 8, 8, 9, 10, 10, 10]
]

CoeffTokenTableCode_4_8 = [
    [15, 15, 11, 8, 15, 11, 9, 8, 15, 11, 15, 11, 8, 13, 9, 5, 1],
    [0, 14, 15, 12, 10, 8, 14, 10, 14, 14, 10, 14, 10, 7, 12, 8, 4],
    [0, 0, 13, 14, 11, 9, 13, 9, 13, 10, 13, 9, 13, 9, 11, 7, 3],
    [0, 0, 0, 12, 11, 10, 9, 8, 13, 12, 12, 12, 8, 12, 10, 6, 2]
]

tableHeight = 4
tableWidth = 17


def coeff_token_8_quick(stream):
    if stream.len < 6:
        raise ValueError("stream.len < 6 and nC >= 8")
    code = stream.read(6).uint
    if code == 3:
        return 0, 0
    elif code == 0:
        return 1, 0
    elif code == 1:
        return 1, 1
    TrailingOnes = code % 4  # 取输入数除以4的余数
    TotalCoeff = code // 4 + 1  # 16减去输入数除以4的整数部分
    return TotalCoeff, TrailingOnes


def coeff_token1(stream: BitStream, nC):
    if nC >= 8:
        return coeff_token_8_quick(stream)
    if nC < 0:
        raise NotImplementedError("nC < 0, nC = %d" % nC)
    if 0 <= nC < 2:
        CoeffTokenTableLength = CoeffTokenTableLength_0_2
        CoeffTokenTableCode = CoeffTokenTableCode_0_2
    elif 2 <= nC < 4:
        CoeffTokenTableLength = CoeffTokenTableLength_2_4
        CoeffTokenTableCode = CoeffTokenTableCode_2_4
    elif 4 <= nC < 8:
        CoeffTokenTableLength = CoeffTokenTableLength_4_8
        CoeffTokenTableCode = CoeffTokenTableCode_4_8
    pos = stream.pos
    stream_len = stream.len
    for yIdx in range(tableHeight):
        for xIdx in range(tableWidth):
            codeLen = CoeffTokenTableLength[yIdx][xIdx]
            if codeLen > stream_len - pos or codeLen == 0:
                continue
            code = stream.read(codeLen).uint
            if code == CoeffTokenTableCode[yIdx][xIdx]:
                TotalCoeff = xIdx
                TrailingOnes = yIdx
                return TotalCoeff, TrailingOnes
            stream.pos = pos
    stream.pos = pos
    return None, None



def init_coeff_token_table():
    def init_table(file):
        lines = file.read_text().splitlines()
        table = [{} for _ in range(6)]
        for line in lines[1:]:
            nums = parse_nums(line)
            trailing_ones, total_coeff, num_bits = int(nums[0]), int(nums[1]), nums[2:]
            for i, v in enumerate(num_bits):
                if v == '-':
                    continue
                table[i][(len(v), int(v, 2))] = (total_coeff, trailing_ones)
        return table
    def parse_nums(s):
        return re.findall(r'(\d+|-)', s)
    table_coeff_token_file = Path(__file__).parent / 'coeff_token.txt'
    return init_table(table_coeff_token_file)


coeff_token_table = init_coeff_token_table()

def coeff_token(stream: BitStream, nC):
    if 0 <= nC < 2:
        table = coeff_token_table[0]
    elif 2 <= nC < 4:
        table = coeff_token_table[1]
    elif 4 <= nC < 8:
        table = coeff_token_table[2]
    elif 8 <= nC:
        table = coeff_token_table[3]
    elif nC == -1:
        table = coeff_token_table[4]
    elif nC == -2:
        table = coeff_token_table[5]

    pos = stream.pos
    curr_len, curr_val = 0, 0
    while curr_len <= 16:
        curr_val = curr_val * 2 + stream.read('uint:1')
        curr_len += 1

        if (curr_len, curr_val) in table:
            return table[(curr_len, curr_val)]
    stream.pos = pos
    raise ValueError("coeff_token failed")

def parse_level_prefix(s: BitStream):
    leadingZeroBits = 0
    b = s.read("uint:1")
    while not b:
        leadingZeroBits += 1
        b = s.read("uint:1")
    return leadingZeroBits


def init_total_zeros_table():
    def init_dic(file):
        lines = file.read_text().splitlines()

        index = list(map(int, parse_nums(lines[0])))
        dic = {}  # (length, value, index) => origin_value
        for line in lines[1:]:
            nums = parse_nums(line)
            value, vlc_bits = int(nums[0]), nums[1:]
            for i, v in enumerate(vlc_bits):
                dic[(len(v), int(v, 2), index[i])] = value
        return dic

    def parse_nums(s):
        return re.findall(r'(\d+)', s)

    table_4_8_file = Path(__file__).parent / 'total_zeros_4_8.txt'
    table_other_file = Path(__file__).parent / 'total_zeros_other.txt'

    return init_dic(table_4_8_file), init_dic(table_other_file)


# (length, value, index) => origin_value
total_zeros_table_4_8, total_zeros_table_other = init_total_zeros_table()

def parse_total_zeros(s, maxNumCoeff, tzVlcIndex):
    if maxNumCoeff == 4:
        table = total_zeros_table_4_8
        max_len = 3
    elif maxNumCoeff == 8:
        raise NotImplementedError("4:2:2 sampling format is not supported")
    else:
        table = total_zeros_table_other
        max_len = 9

    pos = s.pos

    curr_len, curr_val = 0, 0
    while curr_len <= max_len:
        curr_val = curr_val * 2 + s.read('uint:1')
        curr_len += 1

        if (curr_len, curr_val, tzVlcIndex) in table:
            return table[(curr_len, curr_val, tzVlcIndex)]

    s.pos = pos
    raise ValueError("parse_total_zeros failed")


def init_run_before_table():
    def init_table(file):
        lines = file.read_text().splitlines()

        dic_list = [{} for _ in range(8)]
        for line in lines[1:]:
            nums = parse_nums(line)
            value, vlc_bits = int(nums[0]), nums[1:]
            for bs, index in zip(reversed(vlc_bits), range(-1, -8, -1)):
                dic_list[index][(len(bs), int(bs, 2))] = value
        return dic_list

    def parse_nums(s):
        return re.findall(r'(\d+)', s)

    table_run_before_file = Path(__file__).parent / 'run_before.txt'
    return init_table(table_run_before_file)


run_before_table = init_run_before_table()
def parse_run_before(s, zerosLeft):
    if zerosLeft > 6:
        dic = run_before_table[-1]
        max_len = 11
    else:
        dic = run_before_table[zerosLeft]
        max_len = 2 if zerosLeft <= 3 else 3

    pos = s.pos
    curr_len, curr_val = 0, 0
    while curr_len <= max_len:
        curr_val = curr_val * 2 + s.read('uint:1')
        curr_len += 1

        if (curr_len, curr_val) in dic:
            return dic[(curr_len, curr_val)]

    s.pos = pos
    raise ValueError("parse_run_before failed")


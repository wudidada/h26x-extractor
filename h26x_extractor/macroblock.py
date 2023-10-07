# Name of mb_type
# I slice, 0-25
from bitstring import BitStream

from h26x_extractor.nalu_utils import create_matrix

I_NxN = 0
I_16x16_0_0_0 = 1
I_16x16_1_0_0 = 2
I_16x16_2_0_0 = 3
I_16x16_3_0_0 = 4
I_16x16_0_1_0 = 5
I_16x16_1_1_0 = 6
I_16x16_2_1_0 = 7
I_16x16_3_1_0 = 8
I_16x16_0_2_0 = 9
I_16x16_1_2_0 = 10
I_16x16_2_2_0 = 11
I_16x16_3_2_0 = 12
I_16x16_0_0_1 = 13
I_16x16_1_0_1 = 14
I_16x16_2_0_1 = 15
I_16x16_3_0_1 = 16
I_16x16_0_1_1 = 17
I_16x16_1_1_1 = 18
I_16x16_2_1_1 = 19
I_16x16_3_1_1 = 20
I_16x16_0_2_1 = 21
I_16x16_1_2_1 = 22
I_16x16_2_2_1 = 23
I_16x16_3_2_1 = 24
I_PCM = 25

# SI slice, 0, SI + I
SI_LEN = 1
SI_START = 26

SI = 26

# P/SP slice, 0-4, P/SP + I
P_SP_LEN = 5
P_SP_START = 27

P_L0_16x16 = 27
P_L0_L0_16x8 = 28
P_L0_L0_8x16 = 39
P_8x8 = 30
P_8x8ref0 = 31
P_Skip = 32  # inferred

# B slice, 0-22, B + I
B_LEN = 23
B_START = 33

B_Direct_16x16 = 33
B_L0_16x16 = 34
B_L1_16x16 = 35
B_Bi_16x16 = 36
B_L0_L0_16x8 = 37
B_L0_L0_8x16 = 38
B_L1_L1_16x8 = 39
B_L1_L1_8x16 = 40
B_L0_L1_16x8 = 41
B_L0_L1_8x16 = 42
B_L1_L0_16x8 = 43
B_L1_L0_8x16 = 44
B_L0_Bi_16x8 = 45
B_L0_Bi_8x16 = 46
B_L1_Bi_16x8 = 47
B_L1_Bi_8x16 = 48
B_Bi_L0_16x8 = 49
B_Bi_L0_8x16 = 50
B_Bi_L1_16x8 = 51
B_Bi_L1_8x16 = 52
B_Bi_Bi_16x8 = 53
B_Bi_Bi_8x16 = 54
B_8x8 = 55
B_Skip = 56  # inferred

# MbPartPredMode
# I/SI slice
Intra_4x4 = 0
Intra_8x8 = 1
Intra_16x16 = 2

# P/SP slice
Pred_L0 = 3

# B slice
Direct = 4
Pred_L1 = 5
BiPred = 6

# sub-macroblock types
# in P macroblock
P_L0_8x8 = 0
P_L0_8x4 = 1
P_L0_4x8 = 2
P_L0_4x4 = 3

# in B macroblock
B_Direct_8x8 = 0
B_L0_8x8 = 1
B_L1_8x8 = 2
B_Bi_8x8 = 3
B_L0_8x4 = 4
B_L0_4x8 = 5
B_L1_8x4 = 6
B_L1_4x8 = 7
B_L0_4x4 = 8
B_L1_4x4 = 9
B_Bi_8x4 = 10
B_Bi_4x8 = 11
B_Bi_4x4 = 12

MB_TYPE_TABLE_I = {
    I_16x16_0_0_0: (Intra_16x16, None, 0, 0),
    I_16x16_1_0_0: (Intra_16x16, None, 0, 0),
    I_16x16_2_0_0: (Intra_16x16, None, 0, 0),
    I_16x16_3_0_0: (Intra_16x16, None, 0, 0),
    I_16x16_0_1_0: (Intra_16x16, None, 1, 0),
    I_16x16_1_1_0: (Intra_16x16, None, 1, 0),
    I_16x16_2_1_0: (Intra_16x16, None, 1, 0),
    I_16x16_3_1_0: (Intra_16x16, None, 1, 0),
    I_16x16_0_2_0: (Intra_16x16, None, 2, 0),
    I_16x16_1_2_0: (Intra_16x16, None, 2, 0),
    I_16x16_2_2_0: (Intra_16x16, None, 2, 0),
    I_16x16_3_2_0: (Intra_16x16, None, 2, 0),
    I_16x16_0_0_1: (Intra_16x16, None, 0, 15),
    I_16x16_1_0_1: (Intra_16x16, None, 0, 15),
    I_16x16_2_0_1: (Intra_16x16, None, 0, 15),
    I_16x16_3_0_1: (Intra_16x16, None, 0, 15),
    I_16x16_0_1_1: (Intra_16x16, None, 1, 15),
    I_16x16_1_1_1: (Intra_16x16, None, 1, 15),
    I_16x16_2_1_1: (Intra_16x16, None, 1, 15),
    I_16x16_3_1_1: (Intra_16x16, None, 1, 15),
    I_16x16_0_2_1: (Intra_16x16, None, 2, 15),
    I_16x16_1_2_1: (Intra_16x16, None, 2, 15),
    I_16x16_2_2_1: (Intra_16x16, None, 2, 15),
    I_16x16_3_2_1: (Intra_16x16, None, 2, 15),
}

# MbPartPredMode(mb_type, 0), MbPartPredMode(mb_type, 0), MbPartWidth(mb_type), MbPartHeight(mb_type), NumMbPart
MB_TYPE_TABLE_P = {
    P_L0_16x16: (Pred_L0, None, 16, 16, 1),
    P_L0_L0_16x8: (Pred_L0, Pred_L0, 16, 8, 2),
    P_L0_L0_8x16: (Pred_L0, Pred_L0, 8, 16, 2),
    P_8x8: (None, None, 8, 8, 4),
    P_8x8ref0: (None, None, 8, 8, 4),
    P_Skip: (Pred_L0, Pred_L0, 16, 16, 1),
}

# MbPartPredMode(mb_type, 0), MbPartPredMode(mb_type, 0), MbPartWidth(mb_type), MbPartHeight(mb_type), NumMbPart
MB_TYPE_TABLE_B = {
    B_Direct_16x16: (Direct, None, 8, 8, None),
    B_L0_16x16: (Pred_L0, None, 16, 16, 1),
    B_L1_16x16: (Pred_L1, None, 16, 16, 1),
    B_Bi_16x16: (BiPred, None, 16, 16, 1),
    B_L0_L0_16x8: (Pred_L0, Pred_L0, 16, 8, 2),
    B_L0_L0_8x16: (Pred_L0, Pred_L0, 8, 16, 2),
    B_L1_L1_16x8: (Pred_L1, Pred_L1, 16, 8, 2),
    B_L1_L1_8x16: (Pred_L1, Pred_L1, 8, 16, 2),
    B_L0_L1_16x8: (Pred_L0, Pred_L1, 16, 8, 2),
    B_L0_L1_8x16: (Pred_L0, Pred_L1, 8, 16, 2),
    B_L1_L0_16x8: (Pred_L1, Pred_L0, 16, 8, 2),
    B_L1_L0_8x16: (Pred_L1, Pred_L0, 8, 16, 2),
    B_L0_Bi_16x8: (Pred_L0, BiPred, 16, 8, 2),
    B_L0_Bi_8x16: (Pred_L0, BiPred, 8, 16, 2),
    B_L1_Bi_16x8: (Pred_L1, BiPred, 16, 8, 2),
    B_L1_Bi_8x16: (Pred_L1, BiPred, 8, 16, 2),
    B_Bi_L0_16x8: (BiPred, Pred_L0, 16, 8, 2),
    B_Bi_L0_8x16: (BiPred, Pred_L0, 8, 16, 2),
    B_Bi_L1_16x8: (BiPred, Pred_L1, 16, 8, 2),
    B_Bi_L1_8x16: (BiPred, Pred_L1, 8, 16, 2),
    B_Bi_Bi_16x8: (BiPred, BiPred, 16, 8, 2),
    B_Bi_Bi_8x16: (BiPred, BiPred, 8, 16, 2),
    B_8x8: (None, None, 8, 8, 4),
    B_Skip: (Direct, None, 8, 8, None),
}

# NumSubMbPart, SubMbPredMode, SubMbPartWidth, SubMbPartHeight
SUB_MB_TYPE_TABLE_P = {
    P_L0_8x8: (1, Pred_L0, 8, 8),
    P_L0_8x4: (2, Pred_L0, 8, 4),
    P_L0_4x8: (2, Pred_L0, 4, 8),
    P_L0_4x4: (4, Pred_L0, 4, 4),
}

# NumSubMbPart, SubMbPredMode, SubMbPartWidth, SubMbPartHeight
SUB_MB_TYPE_TABLE_B = {
    B_Direct_8x8: (4, Direct, 4, 4),
    B_L0_8x8: (1, Pred_L0, 8, 8),
    B_L1_8x8: (1, Pred_L1, 8, 8),
    B_Bi_8x8: (1, BiPred, 8, 8),
    B_L0_8x4: (2, Pred_L0, 8, 4),
    B_L0_4x8: (2, Pred_L0, 4, 8),
    B_L1_8x4: (2, Pred_L1, 8, 4),
    B_L1_4x8: (2, Pred_L1, 4, 8),
    B_L0_4x4: (4, Pred_L0, 4, 4),
    B_L1_4x4: (4, Pred_L1, 4, 4),
    B_Bi_8x4: (2, BiPred, 8, 4),
    B_Bi_4x8: (2, BiPred, 4, 8),
    B_Bi_4x4: (4, BiPred, 4, 4),
}

# ChromaArrayType 1-2, index 0 for intra, index 1 for inter
CODE_NUM_MAP_TYPE_1_2 = {
    0: (47, 0),
    1: (31, 16),
    2: (15, 1),
    3: (0, 2),
    4: (23, 4),
    5: (27, 8),
    6: (29, 32),
    7: (30, 3),
    8: (7, 5),
    9: (11, 10),
    10: (13, 12),
    11: (14, 15),
    12: (39, 47),
    13: (43, 7),
    14: (45, 11),
    15: (46, 13),
    16: (16, 14),
    17: (3, 6),
    18: (5, 9),
    19: (10, 31),
    20: (12, 35),
    21: (19, 37),
    22: (21, 42),
    23: (26, 44),
    24: (28, 33),
    25: (35, 34),
    26: (37, 36),
    27: (42, 40),
    28: (44, 39),
    29: (1, 43),
    30: (2, 45),
    31: (4, 46),
    32: (8, 17),
    33: (17, 18),
    34: (18, 20),
    35: (20, 24),
    36: (24, 19),
    37: (6, 21),
    38: (9, 26),
    39: (22, 28),
    40: (25, 23),
    41: (32, 27),
    42: (33, 29),
    43: (34, 30),
    44: (36, 22),
    45: (40, 25),
    46: (38, 38),
    47: (41, 41),
}

# ChromaArrayType 0 3, index 0 for intra, index 1 for inter
CODE_NUM_MAP_TYPE_0_3 = {
    0: (15, 0),
    1: (0, 1),
    2: (7, 2),
    3: (11, 4),
    4: (13, 8),
    5: (14, 3),
    6: (3, 5),
    7: (5, 10),
    8: (10, 12),
    9: (12, 15),
    10: (1, 7),
    11: (2, 11),
    12: (4, 13),
    13: (8, 14),
    14: (6, 6),
    15: (9, 9),
}


class MacroBlock:

    def __init__(self, mb_type=None, slice_type=None, start_pos=None, end_pos=None, real_mb_type=None):
        self.slice_type = slice_type
        self.mb_type_clear = None
        if real_mb_type is not None:
            self.mb_type = real_mb_type
            self.mb_type_clear = self.get_mb_type_clear()
        else:
            self.mb_type = self.get_real_mb_type(mb_type) if mb_type is not None else None
            if self.mb_type:
                self.mb_type_clear = self.get_mb_type_clear()

        self.start_pos = start_pos
        self.end_pos = end_pos

        # I_PCM
        self.pcm_alignment_zero_bit = None
        self.pcm_sample_luma = None
        self.pcm_sample_chroma = None

        self.transform_size_8x8_flag = 0

        self.coded_block_pattern = None
        self.mb_qp_delta = None

        self.CodedBlockPatternLuma = None
        self.CodedBlockPatternChroma = None

        # from sub_mb_pred
        self.sub_mb_type = None
        self.ref_idx_l0 = create_matrix(4)
        self.ref_idx_l1 = create_matrix(4)
        self.mvd_l0 = create_matrix(4, 4, 2)
        self.mvd_l1 = create_matrix(4, 4, 2)

        # from mb_pred
        self.prev_intra4x4_pred_mode_flag = create_matrix(16)
        self.rem_intra4x4_pred_mode = create_matrix(16)
        self.prev_intra8x8_pred_mode_flag = create_matrix(4)
        self.rem_intra8x8_pred_mode = create_matrix(4)
        self.intra_chroma_pred_mode = None

        self.ChromaArrayType = 0

        self.i16x16DClevel = create_matrix(16)              # DCT变换后的直流系数
        self.i16x16AClevel = create_matrix(16, 16)          # DCT变换后的交流系数
        self.level4x4 = create_matrix(16, 16)               # 存储亮度的残差数据
        self.level8x8 = create_matrix(4, 64)                # 存储亮度的残差数据
        self.ChromaDCLevel = create_matrix(2, 16)           # 存储DC色度u和v的残差数据
        self.ChromaACLevel = create_matrix(2, 16, 15)       # 存储AC色度u和v的残差数据

    def MbPartPredMode(self, mode):
        return self.macroblock_table()[mode]

    def macroblock_table(self):
        """
        return sequence:
            MbPartPredMode(mb_type, 0), MbPartPredMode(mb_type, 1), ...
        """
        if not self.slice_type:
            raise Exception('slice_type is None')
        # I slice
        if self.slice_type == 'I':
            if self.mb_type in MB_TYPE_TABLE_I:
                return MB_TYPE_TABLE_I[self.mb_type]
            # Equation 7-35
            CodedBlockPatternChroma, CodedBlockPatternLuma = self.get_coded_block_pattern()
            if self.mb_type == 0 and self.transform_size_8x8_flag == 0:
                return Intra_4x4, None, CodedBlockPatternLuma, CodedBlockPatternChroma
            elif self.mb_type == 0 and self.transform_size_8x8_flag == 1:
                return Intra_8x8, None, CodedBlockPatternLuma, CodedBlockPatternChroma
        elif self.slice_type == 'SI':
            # Equation 7-35
            CodedBlockPatternChroma, CodedBlockPatternLuma = self.get_coded_block_pattern()
            return Intra_4x4, None, CodedBlockPatternLuma, CodedBlockPatternChroma
        elif self.slice_type in ['P', 'SP']:
            return MB_TYPE_TABLE_P[self.mb_type]
        elif self.slice_type == 'B':
            return MB_TYPE_TABLE_B[self.mb_type]

    def get_coded_block_pattern(self):
        if not self.coded_block_pattern:
            return 0, 0
        CodedBlockPatternLuma = self.coded_block_pattern % 16
        CodedBlockPatternChroma = self.coded_block_pattern // 16
        self.CodedBlockPatternLuma, self.CodedBlockPatternChroma = CodedBlockPatternLuma, CodedBlockPatternChroma
        return CodedBlockPatternChroma, CodedBlockPatternLuma

    def NumMbPart(self, mb_type=None):
        if mb_type is not None and mb_type != self.mb_type:
            raise Exception('mb_type not match')
        return self.macroblock_table()[-1]

    def SubMbPredMode(self, sub_mb_type):
        return self.sub_macroblock_table(sub_mb_type)[1]

    def NumSubMbPart(self, sub_mb_type):
        return self.sub_macroblock_table(sub_mb_type)[0]

    def sub_macroblock_table(self, sub_mb_type):
        if self.mb_type_clear == 'P':
            return SUB_MB_TYPE_TABLE_P[sub_mb_type]
        if self.mb_type_clear == 'B':
            return SUB_MB_TYPE_TABLE_B[sub_mb_type]

    def get_real_mb_type(self, mb_type):
        if not self.slice_type:
            raise ValueError('slice_type is None')

        if self.slice_type == 'I':
            return mb_type
        elif self.slice_type == 'SI':
            return mb_type + SI_START if mb_type < SI_LEN else mb_type - SI_LEN
        elif self.slice_type == 'P' or self.slice_type == 'SP':
            return mb_type + P_SP_START if mb_type < P_SP_LEN else mb_type - P_SP_LEN
        elif self.slice_type == 'B':
            return mb_type + B_START if mb_type < B_LEN else mb_type - B_LEN

    def get_mb_type_clear(self):
        if not self.mb_type:
            raise ValueError('mb_type is None')

        if self.slice_type == 'I':
            return 'I'
        elif self.slice_type == 'SI':
            return 'SI' if self.mb_type < SI_LEN else 'I'
        elif self.slice_type == 'P' or self.slice_type == 'SP':
            return 'P' if self.mb_type < P_SP_LEN else 'I'
        elif self.slice_type == 'B':
            return 'B' if self.mb_type < B_LEN else 'I'

    def me(self, s: BitStream, ChromaArrayType=None, coded_block_pattern=None):
        if ChromaArrayType is None:
            ChromaArrayType = self.ChromaArrayType
        if coded_block_pattern is None:
            coded_block_pattern = 0 if self.MbPartPredMode(0) < 2 else 1

        code_num = s.read("ue")
        if ChromaArrayType in [1, 2]:
            return CODE_NUM_MAP_TYPE_1_2[code_num][coded_block_pattern]
        elif ChromaArrayType in [0, 3]:
            return CODE_NUM_MAP_TYPE_0_3[code_num][coded_block_pattern]

    def te(self, s: BitStream, value_range):
        if value_range <= 0:
            return 0
        elif range == 1:
            return 1 if s.read("uint:1") == 0 else 0
        else:
            return s.read("ue")


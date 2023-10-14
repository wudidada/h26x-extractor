# nalutypes.py
#
# The MIT License (MIT)
#
# Copyright (c) 2017 Werner Robitza
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.>
import math
from enum import Enum, auto

import numpy as np
from loguru import logger
from tabulate import tabulate

from h26x_extractor import nalu_utils, cavlc
from h26x_extractor.macroblock import *
from h26x_extractor.macroblock import InverseRasterScan
from h26x_extractor.nalu_utils import _get_slice_type, create_matrix

# NAL REF IDC codes
NAL_REF_IDC_PRIORITY_HIGHEST = 3
NAL_REF_IDC_PRIORITY_HIGH = 2
NAL_REF_IDC_PRIORITY_LOW = 1
NAL_REF_IDC_PRIORITY_DISPOSABLE = 0

# NAL unit type codes
NAL_UNIT_TYPE_UNSPECIFIED = 0  # Unspecified
NAL_UNIT_TYPE_CODED_SLICE_NON_IDR = 1  # Coded slice of a non-IDR picture
NAL_UNIT_TYPE_CODED_SLICE_DATA_PARTITION_A = 2  # Coded slice data partition A
NAL_UNIT_TYPE_CODED_SLICE_DATA_PARTITION_B = 3  # Coded slice data partition B
NAL_UNIT_TYPE_CODED_SLICE_DATA_PARTITION_C = 4  # Coded slice data partition C
NAL_UNIT_TYPE_CODED_SLICE_IDR = 5  # Coded slice of an IDR picture
NAL_UNIT_TYPE_SEI = 6  # Supplemental enhancement information (SEI)
NAL_UNIT_TYPE_SPS = 7  # Sequence parameter set
NAL_UNIT_TYPE_PPS = 8  # Picture parameter set
NAL_UNIT_TYPE_AUD = 9  # Access unit delimiter
NAL_UNIT_TYPE_END_OF_SEQUENCE = 10  # End of sequence
NAL_UNIT_TYPE_END_OF_STREAM = 11  # End of stream
NAL_UNIT_TYPE_FILLER = 12  # Filler data
NAL_UNIT_TYPE_SPS_EXT = 13  # Sequence parameter set extension
# 14..18                                          # Reserved
NAL_UNIT_TYPE_CODED_SLICE_AUX = (
    19  # Coded slice of an auxiliary coded picture without partitioning
)


# 20..23                                          # Reserved
# 24..31                                          # Unspecified
def get_description(nal_unit_type):
    """
    Returns a clear text description of a NALU type given as an integer
    """
    return {
        NAL_UNIT_TYPE_UNSPECIFIED: "Unspecified",
        NAL_UNIT_TYPE_CODED_SLICE_NON_IDR: "Coded slice of a non-IDR picture",
        NAL_UNIT_TYPE_CODED_SLICE_DATA_PARTITION_A: "Coded slice data partition A",
        NAL_UNIT_TYPE_CODED_SLICE_DATA_PARTITION_B: "Coded slice data partition B",
        NAL_UNIT_TYPE_CODED_SLICE_DATA_PARTITION_C: "Coded slice data partition C",
        NAL_UNIT_TYPE_CODED_SLICE_IDR: "Coded slice of an IDR picture",
        NAL_UNIT_TYPE_SEI: "Supplemental enhancement information (SEI)",
        NAL_UNIT_TYPE_SPS: "Sequence parameter set",
        NAL_UNIT_TYPE_PPS: "Picture parameter set",
        NAL_UNIT_TYPE_AUD: "Access unit delimiter",
        NAL_UNIT_TYPE_END_OF_SEQUENCE: "End of sequence",
        NAL_UNIT_TYPE_END_OF_STREAM: "End of stream",
        NAL_UNIT_TYPE_FILLER: "Filler data",
        NAL_UNIT_TYPE_SPS_EXT: "Sequence parameter set extension",
        NAL_UNIT_TYPE_CODED_SLICE_AUX: "Coded slice of an auxiliary coded picture without partitioning",
    }.get(nal_unit_type, "unknown")


class Invoker(Enum):
    """
    Enum for the invoker of CAVLC parsing
    """
    LumaLevel4x4 = auto()
    LumaLevel8x8 = auto()
    ChromaDCLevel = auto()
    ChromaACLevel = auto()
    ChromaACLevelCb = auto()
    ChromaACLevelCr = auto()
    Intra16x16DCLevel = auto()
    Intra16x16ACLevel = auto()
    CbIntra16x16DCLevel = auto()
    CbIntra16x16ACLevel = auto()
    CbLevel4x4 = auto()
    CrLevel4x4 = auto()
    CbLevel8x8 = auto()
    CrLevel8x8 = auto()
    CrIntra16x16DCLevel = auto()
    CrIntra16x16ACLevel = auto()


class MbAddrN(Enum):
    mbAddrA = auto()
    mbAddrB = auto()
    mbAddrC = auto()
    mbAddrD = auto()


class NALU(object):
    """
    Class representing a NAL unit, to be initialized with its payload only.
    The type must be inferred from the NALU header, before initializing the NALU by its subclass.
    """

    def __init__(self, rbsp_bytes, verbose, order=None, include_header=False):
        self.s = rbsp_bytes if isinstance(rbsp_bytes, BitStream) else BitStream(rbsp_bytes)
        self.verbose = verbose
        self.order = order

        self.forbidden_zero_bit = None
        self.nal_ref_idc = None
        self.nal_unit_type = None
        if include_header:
            self.forbidden_zero_bit = self.f(1, "forbidden_zero_bit")
            self.nal_ref_idc = self.u(2, "nal_ref_idc")
            self.nal_unit_type = self.u(5, "nal_unit_type")

    def print_verbose(self):
        if self.verbose:
            print(
                self.__class__.__name__
                + " (payload size: "
                + str(len(self.s) / 8)
                + " Bytes)"
            )
            to_print = []
            if self.order is not None:
                for key in self.order:
                    if key in vars(self):
                        value = vars(self)[key]
                        if type(value) != list and not isinstance(value, np.ndarray):
                            to_print.append([key, value])
            for key, value in sorted(vars(self).items()):
                if key == "verbose" or key == "s" or key == "order":
                    continue
                if self.order and key in self.order:
                    continue
                if type(value) != list and not isinstance(value, np.ndarray):
                    to_print.append([key, value])
            print(tabulate(to_print, headers=["field", "value"], tablefmt="grid"))

    def u(self, length, info=None):
        return self.read_bits(f"uint:{length}", info)

    def i(self, length, info=None):
        return self.read_bits(f"int:{length}", info)

    def f(self, length, info=None):
        return self.u(length, info)

    def b(self, length, info=None):
        return self.u(length, info)

    def te(self, value_range, info=None):
        if value_range <= 0:
            return 0
        elif range == 1:
            return 1 if self.u(1, info) == 0 else 0
        else:
            return self.ue(info)

    def ue(self, info=None):
        return self.read_bits("ue", info)

    def se(self, info=None):
        return self.read_bits("se", info)

    def read_bits(self, fmt, info=None):
        pos = self.s.pos
        val = self.s.read(fmt)

        if info is not None:
            logger.debug(f"{info}={val}, pos={pos}")
        return val

    def rbsp_trailing_bits(self):
        rbsp_stop_one_bit = self.u(1, "rbsp_stop_one_bit")
        if rbsp_stop_one_bit != 1:
            raise ValueError("rbsp_stop_one_bit not equal to 1")
        if nalu_utils.more_rbsp_data(self.s):
            raise ValueError("more_rbsp_data is True")
class AUD(NALU):
    """
    Access Unit Delimiter
    """

    def __init__(self, rbsp_bytes, verbose):
        super(AUD, self).__init__(rbsp_bytes, verbose)

        self.primary_pic_type = self.u(3, "primary_pic_type")

        self.print_verbose()


class SPS(NALU):
    """
    Sequence Parameter Set class
    """

    def __init__(self, rbsp_bytes, verbose):
        order = [
            "profile_idc",
            "constraint_set0_flag",
            "constraint_set1_flag",
            "constraint_set2_flag",
            "constraint_set3_flag",
            "constraint_set4_flag",
            "constraint_set5_flag",
            "reserved_zero_2bits",
            "level_idc",
            "seq_parameter_set_id",
            "chroma_format_idc",
            "separate_colour_plane_flag",
            "bit_depth_luma_minus8",
            "bit_depth_chroma_minus8",
            "qpprime_y_zero_transform_bypass_flag",
            "seq_scaling_matrix_present_flag",
            "log2_max_frame_num_minus4",
            "pic_order_cnt_type",
            "log2_max_pic_order_cnt_lsb_minus4",
            "delta_pic_order_always_zero_flag",
            "offset_for_non_ref_pic",
            "offset_for_top_to_bottom_filed",
            "num_ref_frames_in_pic_order_cnt_cycle",
            "offset_for_ref_frame",
            "num_ref_frames",
            "gaps_in_frame_num_value_allowed_flag",
            "pic_width_in_mbs_minus1",
            "pic_height_in_map_units_minus1",
            "frame_mbs_only_flag",
            "mb_adaptive_frame_field_flag",
            "direct_8x8_inference_flag",
            "frame_cropping_flag",
            "frame_crop_left_offset",
            "frame_crop_right_offset",
            "frame_crop_top_offset",
            "frame_crop_bottom_offset",
            "vui_parameters_present_flag",
        ]
        super(SPS, self).__init__(rbsp_bytes, verbose, order)

        self.offset_for_ref_frame = []
        self.seq_scaling_list_present_flag = []
        self.profile_idc = None
        self.constraint_set0_flag = None
        self.constraint_set1_flag = None
        self.constraint_set2_flag = None
        self.constraint_set3_flag = None
        self.constraint_set4_flag = None
        self.constraint_set5_flag = None
        self.reserved_zero_2bits = None
        self.level_idc = None
        self.seq_parameter_set_id = None
        self.chroma_format_idc = 1
        self.separate_colour_plane_flag = 0
        self.bit_depth_luma_minus8 = 0
        self.bit_depth_chroma_minus8 = 0
        self.qpprime_y_zero_transform_bypass_flag = None
        self.seq_scaling_matrix_present_flag = None
        self.log2_max_frame_num_minus4 = None
        self.pic_order_cnt_type = None
        self.log2_max_pic_order_cnt_lsb_minus4 = None
        self.delta_pic_order_always_zero_flag = None
        self.offset_for_non_ref_pic = None
        self.offset_for_top_to_bottom_filed = None
        self.num_ref_frames_in_pic_order_cnt_cycle = None
        self.num_ref_frames = None
        self.gaps_in_frame_num_value_allowed_flag = None
        self.pic_width_in_mbs_minus1 = None
        self.pic_height_in_map_units_minus1 = None
        self.frame_mbs_only_flag = None
        self.mb_adaptive_frame_field_flag = None
        self.direct_8x8_inference_flag = None
        self.frame_cropping_flag = None
        self.frame_crop_left_offset = None
        self.frame_crop_right_offset = None
        self.frame_crop_top_offset = None
        self.frame_crop_bottom_offset = None
        self.vui_parameters_present_flag = None

        self.seq_parameter_set_data()

        self.print_verbose()

    def seq_parameter_set_data(self):
        self.profile_idc = self.s.read("uint:8")
        self.constraint_set0_flag = self.s.read("uint:1")
        self.constraint_set1_flag = self.s.read("uint:1")
        self.constraint_set2_flag = self.s.read("uint:1")
        self.constraint_set3_flag = self.s.read("uint:1")
        self.constraint_set4_flag = self.s.read("uint:1")
        self.constraint_set5_flag = self.s.read("uint:1")
        self.reserved_zero_2bits = self.s.read("uint:2")
        self.level_idc = self.s.read("uint:8")
        self.seq_parameter_set_id = self.s.read("ue")

        if self.profile_idc in [
            100,
            110,
            122,
            244,
            44,
            83,
            86,
            118,
            128,
            138,
            139,
            134,
            135,
        ]:
            self.chroma_format_idc = self.s.read("ue")
            if self.chroma_format_idc == 3:
                self.separate_colour_plane_flag = self.s.read("uint:1")

            self.bit_depth_luma_minus8 = self.s.read("ue")
            self.bit_depth_chroma_minus8 = self.s.read("ue")
            self.qpprime_y_zero_transform_bypass_flag = self.s.read("uint:1")
            self.seq_scaling_matrix_present_flag = self.s.read("uint:1")

            if self.seq_scaling_matrix_present_flag:
                # TODO: have to implement this, otherwise it will fail
                raise NotImplementedError("Scaling matrix decoding is not implemented.")

        self.log2_max_frame_num_minus4 = self.s.read("ue")
        self.pic_order_cnt_type = self.s.read("ue")

        if self.pic_order_cnt_type == 0:
            self.log2_max_pic_order_cnt_lsb_minus4 = self.s.read("ue")
        elif self.pic_order_cnt_type == 1:
            self.delta_pic_order_always_zero_flag = self.s.read("uint:1")
            self.offset_for_non_ref_pic = self.s.read("se")
            self.offset_for_top_to_bottom_filed = self.s.read("se")
            self.num_ref_frames_in_pic_order_cnt_cycle = self.s.read("ue")
            for i in range(self.num_ref_frames_in_pic_order_cnt_cycle):
                self.offset_for_ref_frame.append(self.s.read("se"))

        self.num_ref_frames = self.s.read("ue")
        self.gaps_in_frame_num_value_allowed_flag = self.s.read("uint:1")
        self.pic_width_in_mbs_minus1 = self.s.read("ue")
        self.pic_height_in_map_units_minus1 = self.s.read("ue")
        self.frame_mbs_only_flag = self.s.read("uint:1")
        if not self.frame_mbs_only_flag:
            self.mb_adaptive_frame_field_flag = self.s.read("uint:1")
        self.direct_8x8_inference_flag = self.s.read("uint:1")
        self.frame_cropping_flag = self.s.read("uint:1")
        if self.frame_cropping_flag:
            self.frame_crop_left_offset = self.s.read("ue")
            self.frame_crop_right_offset = self.s.read("ue")
            self.frame_crop_top_offset = self.s.read("ue")
            self.frame_crop_bottom_offset = self.s.read("ue")
        self.vui_parameters_present_flag = self.s.read("uint:1")

        # TODO: parse VUI
        # self.rbsp_stop_one_bit         = self.s.read('uint:1')


class PPS(NALU):
    def __init__(self, rbsp_bytes, verbose, sps=None):
        order = [
            "pic_parameter_set_id",
            "seq_parameter_set_id",
            "entropy_coding_mode_flag",
            "bottom_field_pic_order_in_frame_present_flag",
            "num_slice_groups_minus1",
            "slice_group_map_type",
            "run_length_minus1",
            "top_left",
            "bottom_right",
            "slice_group_change_direction_flag",
            "slice_group_change_rate_minus1",
            "pic_size_in_map_units_minus1",
            "slice_group_id",
            "num_ref_idx_l0_active_minus1",
            "num_ref_idx_l1_active_minus1",
            "weighted_pred_flag",
            "weighted_bipred_idc",
            "pic_init_qp_minus26",
            "pic_init_qs_minus26",
            "chroma_qp_index_offset",
            "deblocking_filter_control_present_flag",
            "constrained_intra_pred_flag",
            "redundant_pic_cnt_present_flag",
        ]
        super(PPS, self).__init__(rbsp_bytes, verbose, order)

        self.pic_parameter_set_id = None
        self.seq_parameter_set_id = None
        self.entropy_coding_mode_flag = None
        self.bottom_field_pic_order_in_frame_present_flag = None
        self.num_slice_groups_minus1 = None
        self.slice_group_map_type = 0
        self.run_length_minus1 = create_matrix(8)
        self.top_left = None
        self.bottom_right = None
        self.slice_group_change_direction_flag = None
        self.slice_group_change_rate_minus1 = None
        self.pic_size_in_map_units_minus1 = None
        self.slice_group_id = None
        self.num_ref_idx_l0_active_minus1 = None
        self.num_ref_idx_l1_active_minus1 = None
        self.weighted_pred_flag = None
        self.weighted_bipred_idc = None
        self.pic_init_qp_minus26 = None
        self.pic_init_qs_minus26 = None
        self.chroma_qp_index_offset = None
        self.deblocking_filter_control_present_flag = None
        self.constrained_intra_pred_flag = None
        self.redundant_pic_cnt_present_flag = None
        self.transform_8x8_mode_flag = 0                    # inferred to 0
        self.pic_scaling_matrix_present_flag = None
        self.second_chroma_qp_index_offset = None

        self.pic_parameter_set_rbsp(sps)

        self.rbsp_trailing_bits()

        self.print_verbose()

    def pic_parameter_set_rbsp(self, sps: SPS):
        self.pic_parameter_set_id = self.ue("pic_parameter_set_id")
        self.seq_parameter_set_id = self.ue("seq_parameter_set_id")
        self.entropy_coding_mode_flag = self.u(1, "entropy_coding_mode_flag")
        self.bottom_field_pic_order_in_frame_present_flag = self.u(1, "bottom_field_pic_order_in_frame_present_flag")
        self.num_slice_groups_minus1 = self.ue("num_slice_groups_minus1")
        if self.num_slice_groups_minus1 > 0:
            self.slice_group_map_type = self.ue("slice_group_map_type")
            if self.slice_group_map_type == 0:
                for i_group in range(self.num_slice_groups_minus1 + 1):
                    self.run_length_minus1[i_group] = self.ue("run_length_minus1")
            elif self.slice_group_map_type == 2:
                self.top_left = []
                self.bottom_right = []
                for i_group in range(self.num_slice_groups_minus1 + 1):
                    self.top_left.append(self.ue("top_left"))
                    self.bottom_right.append(self.ue("bottom_right"))
            elif self.slice_group_map_type in [3, 4, 5]:
                self.slice_group_change_direction_flag = self.u(1, "slice_group_change_direction_flag")
                self.slice_group_change_rate_minus1 = self.ue("slice_group_change_rate_minus1")
            elif self.slice_group_map_type == 6:
                self.pic_size_in_map_units_minus1 = self.ue("pic_size_in_map_units_minus1")
                self.slice_group_id = []
                for i in range(self.pic_size_in_map_units_minus1 + 1):
                    self.slice_group_id.append(self.u(1, "slice_group_id"))
        self.num_ref_idx_l0_active_minus1 = self.ue("num_ref_idx_l0_active_minus1")
        self.num_ref_idx_l1_active_minus1 = self.ue("num_ref_idx_l1_active_minus1")
        self.weighted_pred_flag = self.u(1, "weighted_pred_flag")
        self.weighted_bipred_idc = self.u(2, "weighted_bipred_idc")
        self.pic_init_qp_minus26 = self.se("pic_init_qp_minus26")
        self.pic_init_qs_minus26 = self.se("pic_init_qs_minus26")
        self.chroma_qp_index_offset = self.se("chroma_qp_index_offset")
        self.deblocking_filter_control_present_flag = self.u(1, "deblocking_filter_control_present_flag")
        self.constrained_intra_pred_flag = self.u(1, "constrained_intra_pred_flag")
        self.redundant_pic_cnt_present_flag = self.u(1, "redundant_pic_cnt_present_flag")

        if nalu_utils.more_rbsp_data(self.s):
            self.transform_8x8_mode_flag = self.u(1, "transform_8x8_mode_flag")
            self.pic_scaling_matrix_present_flag = self.u(1, "pic_scaling_matrix_present_flag")
            if self.pic_scaling_matrix_present_flag:
                # not fully implemented
                raise NotImplementedError("Scaling matrix decoding is not implemented.")
            self.second_chroma_qp_index_offset = self.se("second_chroma_qp_index_offset")


def derive_4x4_luma_blkIdx(xP, yP):
    """
    6.4.13.1 Derivation process for 4x4 luma block indices
    """
    return int(2 * (yP // 4) + (xP // 4))


def inverse_4x4_luma_block_scanning(blkIdx):
    """
    6.4.3 Inverse 4x4 luma block scanning process
    """
    x = InverseRasterScan(blkIdx // 4, 8, 8, 16, 0) + InverseRasterScan(blkIdx % 4, 4, 4, 8, 0)
    y = InverseRasterScan(blkIdx // 4, 8, 8, 16, 1) + InverseRasterScan(blkIdx % 4, 4, 4, 8, 1)
    return x, y


def inverse_4x4_chroma_block_scanning(blkIdx):
    """
    6.4.7 Inverse 4x4 chroma block scanning process
    """
    x = InverseRasterScan(blkIdx, 4, 4, 8, 0)
    y = InverseRasterScan(blkIdx, 4, 4, 8, 1)
    return x, y


def derive_4x4_chroma_blkIdx(xP, yP):
    """
    6.4.13.2 Derivation process for 4x4 chroma block indices
    """
    return int(2 * (yP // 4) + (xP // 4))


class VCLSlice(NALU):
    def __init__(self, rbsp_bytes, nalu_sps: SPS, nalu_pps: PPS, verbose, order=None, include_header=False):
        super(VCLSlice, self).__init__(
            rbsp_bytes, verbose, order, include_header=include_header
        )

        self.sps = nalu_sps
        self.pps = nalu_pps

        # 7.3.2.8 Slice layer without partitioning RBSP syntax
        # values to be parsed from header
        # slice_header()
        self.first_mb_in_slice = None
        self.slice_type = None
        self.pic_parameter_set_id = None
        self.colour_plane_id = None
        self.frame_num = None
        self.field_pic_flag = 0
        self.bottom_field_flag = None
        self.idr_pic_id = None
        self.pic_order_cnt_lsb = None
        self.delta_pic_order_cnt_bottom = None
        self.delta_pic_order_cnt = None
        self.redundant_pic_cnt = None
        self.direct_spatial_mv_pred_flag = None
        self.num_ref_idx_active_override_flag = None
        self.num_ref_idx_l0_active_minus1 = 0  # this value should set default value
        self.num_ref_idx_l1_active_minus1 = 0
        self.ref_pic_list_modification_flag_l0 = None
        self.ref_pic_list_modification_flag_l1 = None
        self.cabac_init_idc = None
        self.slice_qp_delta = None
        self.sp_for_switch_flag = None
        self.slice_qs_delta = None
        self.disable_deblocking_filter_idc = None
        self.slice_alpha_c0_offset_div2 = None
        self.slice_beta_offset_div2 = None
        self.slice_group_change_cycle = None
        self.PicSizeInMapUnits = None
        self.PicWidthInMbs = None
        self.PicHeightInMbs = None
        self.PicSizeInMbs = None

        #   ref_pic_list_modification()
        self.modification_of_pic_nums_idc = None
        self.abs_diff_pic_num_minus1 = None
        self.long_term_pic_num = None

        #   pred_weight_table()
        self.luma_log2_weight_denom = None
        self.chroma_log2_weight_denom = None
        self.luma_weight_l0_flag = None
        self.luma_weight_l0 = None
        self.luma_offset_l0 = None
        self.chroma_weight_l0_flag = None
        self.chroma_weight_l0 = None
        self.chroma_offset_l0 = None
        self.luma_weight_l1_flag = None
        self.luma_weight_l1 = None
        self.luma_offset_l1 = None
        self.chroma_weight_l1_flag = None
        self.chroma_weight_l1 = None
        self.chroma_offset_l1 = None

        #   dec_ref_pic_marking()
        self.no_output_of_prior_pics_flag = None
        self.long_term_reference_flag = None
        self.adaptive_ref_pic_marking_mode_flag = None
        self.memory_management_control_operation = None
        self.difference_of_pic_nums_minus1 = None
        self.long_term_pic_num = None
        self.long_term_frame_idx = None
        self.max_long_term_frame_idx_plus1 = None

        # G.7.3.4 Slice header semantics, inferred values
        self.ref_layer_dq_id = -1
        self.scan_id_start = 0
        self.scan_id_end = 15

        # start parsing header
        self.slice_header()
        logger.debug(f"slice_header end pos={self.s.pos}")

        # values to be parsed from data
        # slice_data()
        self.mb_skip_run = None
        self.mb_field_decoding_flag = None

        self.MbaffFrameFlag = None
        self.MbToSliceGroupMap = None

        self.MbaffFrameFlag = None
        self.PicSizeInMbs = None

        self.SubWidthC = None
        self.SubHeightC = None
        self.BitDepthY = None
        self.BitDepthC = None
        self.MbWidthC = None
        self.MbHeightC = None

        self.ChromaArrayType = 1

        self.mapUnitToSliceGroupMap = None
        #   macroblock_layer()

        self.macroblocks = {}

        self.slice_data()
        # self.rbsp_trailing_bits()

    def slice_header(self):
        """
        parse slice_header
        7.3.3 Slice header syntax
        """
        sps, pps = self.sps, self.pps
        self.first_mb_in_slice = self.ue("first_mb_in_slice")
        self.slice_type = self.ue("slice_type")
        self.slice_type_clear = _get_slice_type(self.slice_type)
        self.pic_parameter_set_id = self.ue("pic_parameter_set_id")
        if sps.separate_colour_plane_flag == 1:
            self.colour_plane_id = self.u(2, "colour_plane_id")
        self.frame_num = self.u(sps.log2_max_frame_num_minus4 + 4, "frame_num")
        if not sps.frame_mbs_only_flag:
            self.field_pic_flag = self.u(1, "field_pic_flag")
            if self.field_pic_flag:
                self.bottom_field_flag = self.u(1, "bottom_field_flag")

        # IdrPicFlag = ((nal_unit_type = = 5) ? 1: 0)
        IdrPicFlag = self.nal_unit_type == 5
        if IdrPicFlag:
            self.idr_pic_id = self.ue("idr_pic_id")

        if sps.pic_order_cnt_type == 0:
            self.pic_order_cnt_lsb = self.u(sps.log2_max_pic_order_cnt_lsb_minus4 + 4, "pic_order_cnt_lsb")
            if (
                    pps.bottom_field_pic_order_in_frame_present_flag
                    and not self.field_pic_flag
            ):
                self.delta_pic_order_cnt_bottom = self.se("delta_pic_order_cnt_bottom")

        if sps.pic_order_cnt_type == 1 and not sps.delta_pic_order_always_zero_flag:
            self.delta_pic_order_cnt = []
            self.delta_pic_order_cnt.append(self.se("delta_pic_order_cnt"))
            if (
                    pps.bottom_field_pic_order_in_frame_present_flag and not self.field_pic_flag
            ):
                self.delta_pic_order_cnt.append(self.se("delta_pic_order_cnt"))

        if pps.redundant_pic_cnt_present_flag:
            self.redundant_pic_cnt = self.ue("redundant_pic_cnt")

        if self.slice_type_clear == "B":
            self.direct_spatial_mv_pred_flag = self.u(1, "direct_spatial_mv_pred_flag")

        if self.slice_type_clear in ["P", "SP", "B"]:
            self.num_ref_idx_active_override_flag = self.u(1, "num_ref_idx_active_override_flag")
            if self.num_ref_idx_active_override_flag:
                self.num_ref_idx_l0_active_minus1 = self.ue("num_ref_idx_l0_active_minus1")
                if self.slice_type_clear == "B":
                    self.num_ref_idx_l1_active_minus1 = self.ue("num_ref_idx_l1_active_minus1")

        # TODO: nal_unit == 20 or nal_unit == 21
        # ref_pic_list_mvc_modification( ) /* specified in Annex H */

        self.ref_pic_list_modification()
        if (
                pps.weighted_pred_flag
                and (self.slice_type_clear == "P" or self.slice_type_clear == "SP")
        ) or (
                pps.weighted_bipred_idc == 1 and self.slice_type_clear == "B"
        ):
            self.pred_weight_table()

        if self.nal_ref_idc != 0:
            self.dec_ref_pic_marking()

        if pps.entropy_coding_mode_flag and self.slice_type_clear != "I" and self.slice_type_clear != "SI":
            self.cabac_init_idc = self.ue("cabac_init_idc")
        self.slice_qp_delta = self.se("slice_qp_delta")

        if self.slice_type_clear == "SP" or self.slice_type_clear == "SI":
            if self.slice_type_clear == "SP":
                self.sp_for_switch_flag = self.u(1, "sp_for_switch_flag")
            self.slice_qs_delta = self.se("slice_qs_delta")

        if pps.deblocking_filter_control_present_flag:
            self.disable_deblocking_filter_idc = self.ue("disable_deblocking_filter_idc")
            if self.disable_deblocking_filter_idc != 1:
                self.slice_alpha_c0_offset_div2 = self.se("slice_alpha_c0_offset_div2")
                self.slice_beta_offset_div2 = self.se("slice_beta_offset_div2")

        PicHeightInMapUnits = sps.pic_height_in_map_units_minus1 + 1
        PicWidthInMbs = sps.pic_width_in_mbs_minus1 + 1
        PicSizeInMapUnits = PicWidthInMbs * PicHeightInMapUnits

        FrameHeightInMbs = (2 - sps.frame_mbs_only_flag) * PicHeightInMapUnits
        PicHeightInMbs = FrameHeightInMbs // (1 + self.field_pic_flag)

        self.PicSizeInMapUnits = PicSizeInMapUnits
        self.PicWidthInMbs = PicWidthInMbs
        self.PicHeightInMbs = PicHeightInMbs

        if pps.num_slice_groups_minus1 > 0 and 3 <= pps.slice_group_map_type <= 5:
            # bits length: Ceil( Log2( PicSizeInMapUnits ÷ SliceGroupChangeRate + 1 ) )
            self.slice_group_change_cycle = self.u(math.ceil(math.log(PicSizeInMapUnits / pps.slice_group_change_rate + 1, 2)), "slice_group_change_cycle")

    def ref_pic_list_modification(self):
        if self.slice_type % 5 != 2 and self.slice_type % 5 != 4:
            self.ref_pic_list_modification_flag_l0 = self.u(1, "ref_pic_list_modification_flag_l0")
            if self.ref_pic_list_modification_flag_l0:
                while True:
                    self.modification_of_pic_nums_idc = self.ue("modification_of_pic_nums_idc")
                    if self.modification_of_pic_nums_idc == 0 or self.modification_of_pic_nums_idc == 1:
                        self.abs_diff_pic_num_minus1 = self.ue("abs_diff_pic_num_minus1")
                    elif self.modification_of_pic_nums_idc == 2:
                        self.long_term_pic_num = self.ue("long_term_pic_num")

                    if self.modification_of_pic_nums_idc == 3:
                        break

        if self.slice_type % 5 == 1:
            self.ref_pic_list_modification_flag_l1 = self.u(1, "ref_pic_list_modification_flag_l1")
            if self.ref_pic_list_modification_flag_l1:
                while True:
                    self.modification_of_pic_nums_idc = self.ue("modification_of_pic_nums_idc")
                    if self.modification_of_pic_nums_idc == 0 or self.modification_of_pic_nums_idc == 1:
                        self.abs_diff_pic_num_minus1 = self.ue("abs_diff_pic_num_minus1")
                    elif self.modification_of_pic_nums_idc == 2:
                        self.long_term_pic_num = self.ue("long_term_pic_num")

                    if self.modification_of_pic_nums_idc == 3:
                        break

    def pred_weight_table(self):
        self.luma_log2_weight_denom = self.s.read("ue")
        if self.ChromaArrayType != 0:
            self.chroma_log2_weight_denom = self.s.read("ue")

        self.luma_weight_l0 = create_matrix(self.num_ref_idx_l0_active_minus1 + 1)
        self.luma_offset_l0 = create_matrix(self.num_ref_idx_l0_active_minus1 + 1)
        self.chroma_weight_l0 = create_matrix(self.num_ref_idx_l0_active_minus1 + 1, 2)
        self.chroma_offset_l0 = create_matrix(self.num_ref_idx_l0_active_minus1 + 1, 2)

        for i in range(self.num_ref_idx_l0_active_minus1 + 1):
            self.luma_weight_l0_flag = self.u(1, "luma_weight_l0_flag")
            if self.luma_weight_l0_flag:
                self.luma_weight_l0[i] = self.se("luma_weight_l0")
                self.luma_offset_l0[i] = self.se("luma_offset_l0")
            if self.ChromaArrayType != 0:
                self.chroma_weight_l0_flag = self.u(1, "chroma_weight_l0_flag")
                if self.chroma_weight_l0_flag:
                    for j in range(2):
                        self.chroma_weight_l0[i][j] = self.se("chroma_weight_l0")
                        self.chroma_offset_l0[i][j] = self.se("chroma_offset_l0")

        self.luma_weight_l1 = create_matrix(self.num_ref_idx_l1_active_minus1 + 1)
        self.luma_offset_l1 = create_matrix(self.num_ref_idx_l1_active_minus1 + 1)
        self.chroma_weight_l1 = create_matrix(self.num_ref_idx_l1_active_minus1 + 1, 2)
        self.chroma_offset_l1 = create_matrix(self.num_ref_idx_l1_active_minus1 + 1, 2)
        if self.slice_type % 5 == 1:
            for i in range(self.num_ref_idx_l1_active_minus1 + 1):
                self.luma_weight_l1_flag = self.u(1, "luma_weight_l1_flag")
                if self.luma_weight_l1_flag:
                    self.luma_weight_l1[i] = self.se("luma_weight_l1")
                    self.luma_offset_l1[i] = self.se("luma_offset_l1")
                if self.ChromaArrayType != 0:
                    self.chroma_weight_l1_flag = self.u(1, "chroma_weight_l1_flag")
                    if self.chroma_weight_l1_flag:
                        for j in range(2):
                            self.chroma_weight_l1[i][j] = self.se("chroma_weight_l1")
                            self.chroma_offset_l1[i][j] = self.se("chroma_offset_l1")

    def dec_ref_pic_marking(self):
        IdrPicFlag = self.nal_unit_type == 5
        if IdrPicFlag:
            self.no_output_of_prior_pics_flag = self.u(1, "no_output_of_prior_pics_flag")
            self.long_term_reference_flag = self.u(1, "long_term_reference_flag")
        else:
            self.adaptive_ref_pic_marking_mode_flag = self.u(1, "adaptive_ref_pic_marking_mode_flag")
            if self.adaptive_ref_pic_marking_mode_flag:
                while True:
                    self.memory_management_control_operation = self.ue("memory_management_control_operation")
                    if self.memory_management_control_operation == 0 or self.memory_management_control_operation == 1:
                        self.difference_of_pic_nums_minus1 = self.ue("difference_of_pic_nums_minus1")
                    elif self.memory_management_control_operation == 2:
                        self.long_term_pic_num = self.ue("long_term_pic_num")
                    elif self.memory_management_control_operation == 3 or self.memory_management_control_operation == 6:
                        self.long_term_frame_idx = self.ue("long_term_frame_idx")
                    elif self.memory_management_control_operation == 4:
                        self.max_long_term_frame_idx_plus1 = self.ue("max_long_term_frame_idx_plus1")

                    if self.memory_management_control_operation == 0:
                        break

    def slice_data(self):
        sps, pps = self.sps, self.pps

        self.setup_slice_data()

        if pps.entropy_coding_mode_flag:
            raise NotImplementedError("CABAC decoding is not implemented.")
        # MbaffFrameFlag = ( mb_adaptive_frame_field_flag && !field_pic_flag )
        MbaffFrameFlag = self.MbaffFrameFlag
        CurrMbAddr = self.first_mb_in_slice * (1 + MbaffFrameFlag)
        moreDataFlag = True
        prevMbSkipped = False
        while moreDataFlag:
            if self.slice_type_clear != "I" and self.slice_type_clear != "SI":
                if not pps.entropy_coding_mode_flag:
                    self.mb_skip_run = self.ue("mb_skip_run")
                    prevMbSkipped = self.mb_skip_run > 0
                    for i in range(self.mb_skip_run):
                        CurrMbAddr = self.NextMbAddress(CurrMbAddr)
                    if self.mb_skip_run > 0:
                        moreDataFlag = self.more_rbsp_data()
                else:
                    raise NotImplementedError("CABAC decoding is not implemented.")
            if moreDataFlag:
                if MbaffFrameFlag and (CurrMbAddr % 2 == 0 or (CurrMbAddr % 2 == 1 and prevMbSkipped)):
                    self.mb_field_decoding_flag = self.u(1, "mb_field_decoding_flag")
                self.macroblock_layer(CurrMbAddr)
            if not pps.entropy_coding_mode_flag:
                moreDataFlag = self.more_rbsp_data()
            else:
                raise NotImplementedError("CABAC decoding is not implemented.")
            CurrMbAddr = self.NextMbAddress(CurrMbAddr)

    def more_rbsp_data(self):
        return nalu_utils.more_rbsp_data(self.s)

    def macroblock_layer(self, CurrMbAddr):
        """
        parse macroblock_layer()
        7.3.5 Macroblock layer syntax
        """
        logger.debug(f"macroblock_layer: CurrMbAddr={CurrMbAddr}")
        logger.debug(f"macroblock_layer: start pos={self.s.pos}")
        sps, pps = self.sps, self.pps
        mb_type = self.ue("mb_type")
        if CurrMbAddr == 2:
            print()

        mb = MacroBlock(slice_type=self.slice_type_clear, start_pos=self.s.pos, mb_type=mb_type, CurrMbAddr=CurrMbAddr)
        self.macroblocks[CurrMbAddr] = mb
        mb.ChromaArrayType = self.ChromaArrayType

        mb_type = mb.mb_type

        if mb_type == I_PCM:
            pcm_sample_luma = create_matrix(256)
            pcm_sample_chroma = create_matrix(256)
            while not self.byte_aligned():
                self.s.read("uint:1")
            for i in range(256):
                pcm_sample_luma[i] = self.s.read(f"uint:{self.BitDepthY}")
            for i in range(2 * self.MbWidthC * self.MbHeightC):
                pcm_sample_chroma[i] = self.s.read(f"uint:{self.BitDepthC}")
            mb.pcm_sample_luma = pcm_sample_luma
            mb.pcm_sample_chroma = pcm_sample_chroma
        else:
            noSubMbPartSizeLessThan8x8Flag = 1
            if mb_type != I_NxN and mb.MbPartPredMode(0) != Intra_16x16 and mb.NumMbPart() == 4:
                self.sub_mb_pred(mb_type, mb, sps, pps)
                for mbPartIdx in range(4):
                    if mb.sub_mb_type[mbPartIdx] != B_Direct_8x8:
                        if self.NumSubMbPart(mb.sub_mb_type[mbPartIdx]) > 1:
                            noSubMbPartSizeLessThan8x8Flag = 0
                    elif not self.direct_spatial_mv_pred_flag:
                        noSubMbPartSizeLessThan8x8Flag = 0
            else:
                if pps.transform_8x8_mode_flag and mb_type == I_NxN:
                    transform_size_8x8_flag = self.u(1, "transform_size_8x8_flag")
                    mb.transform_size_8x8_flag = transform_size_8x8_flag
                self.mb_pred(mb_type, mb)

            CodedBlockPatternLuma, CodedBlockPatternChroma = 0, 0
            if mb.MbPartPredMode(0) != Intra_16x16:
                coded_block_pattern = self.me(mb, "coded_block_pattern")
                mb.coded_block_pattern = coded_block_pattern
                CodedBlockPatternLuma, CodedBlockPatternChroma = mb.get_coded_block_pattern()
                if (CodedBlockPatternLuma > 0 and
                        pps.transform_8x8_mode_flag and mb_type != I_NxN and
                        noSubMbPartSizeLessThan8x8Flag and
                        (mb_type != B_Direct_16x16 or sps.direct_8x8_inference_flag)):
                    transform_size_8x8_flag = self.u(1, "transform_size_8x8_flag")
                    mb.transform_size_8x8_flag = transform_size_8x8_flag
            if CodedBlockPatternLuma > 0 or CodedBlockPatternChroma > 0 or mb.MbPartPredMode(0) == Intra_16x16:
                mb_qp_delta = self.se("mb_qp_delta")
                mb.mb_qp_delta = mb_qp_delta
                self.residual(0, 15, mb)
        mb.end_pos = self.s.pos - 1

    def setup_slice_data(self):
        """
        do some setup for slice_data()
        """
        sps, pps = self.sps, self.pps

        self.ChromaArrayType = sps.chroma_format_idc if not sps.separate_colour_plane_flag else 0

        self.MbaffFrameFlag = 1 if (sps.mb_adaptive_frame_field_flag and not self.field_pic_flag) else 0
        self.PicSizeInMbs = self.PicWidthInMbs * self.PicHeightInMbs

        self.BitDepthY = sps.bit_depth_luma_minus8 + 8
        self.BitDepthC = sps.bit_depth_chroma_minus8 + 8

        # 6.2 Source, decoded, and output picture formats
        # SubWidthC is chroma / luma in horizontal, SubHeightC is chroma / luma in vertical
        if (sps.chroma_format_idc, sps.separate_colour_plane_flag) == (1, 0):
            self.SubWidthC, self.SubHeightC = 2, 2  # YUV 4:2:0
        elif (sps.chroma_format_idc, sps.separate_colour_plane_flag) == (2, 0):
            self.SubWidthC, self.SubHeightC = 2, 1  # YUV 4:2:2
        elif (sps.chroma_format_idc, sps.separate_colour_plane_flag) == (3, 0):
            self.SubWidthC, self.SubHeightC = 1, 1  # YUV 4:4:4

        if not sps.chroma_format_idc or sps.separate_colour_plane_flag:
            self.MbWidthC, self.MbHeightC = 0, 0
        else:
            self.MbWidthC = 16 // self.SubWidthC
            self.MbHeightC = 16 // self.SubHeightC

        self.setup_MbToSliceGroupMap(sps, pps)

    def setup_MbToSliceGroupMap(self, sps, pps):
        # 8.2.2 Decoding process for macroblock to slice group map
        # setup mapUnitToSliceGroupMap
        if pps.slice_group_map_type == 0:
            mapUnitToSliceGroupMap = create_matrix(self.PicSizeInMapUnits)
            PicSizeInMapUnits = self.PicSizeInMapUnits
            num_slice_groups_minus1 = pps.num_slice_groups_minus1
            run_length_minus1 = pps.run_length_minus1

            i = 0
            while True:
                iGroup = 0
                while iGroup <= num_slice_groups_minus1 and i < PicSizeInMapUnits:
                    j = 0
                    while j <= run_length_minus1[iGroup] and i + j < PicSizeInMapUnits:
                        mapUnitToSliceGroupMap[i + j] = iGroup
                        j += 1

                    i += run_length_minus1[iGroup] + 1
                    iGroup += 1
                if i >= PicSizeInMapUnits:
                    break
            self.mapUnitToSliceGroupMap = mapUnitToSliceGroupMap
        else:
            raise NotImplementedError("num_slice_groups_minus1 > 0 is not implemented.")

        # 8.2.2.8 Specification for conversion of map unit to slice group map to macroblock to slice group map
        MbToSliceGroupMap = create_matrix(self.PicSizeInMapUnits)
        if sps.frame_mbs_only_flag or self.field_pic_flag:
            for i in range(self.PicSizeInMbs):
                MbToSliceGroupMap[i] = self.mapUnitToSliceGroupMap[i]
        elif self.MbaffFrameFlag:
            for i in range(self.PicSizeInMbs):
                MbToSliceGroupMap[i] = self.mapUnitToSliceGroupMap[i // 2]
        elif not sps.frame_mbs_only_flag and not sps.mb_adaptive_frame_field_flag and not self.field_pic_flag:
            for i in range(self.PicSizeInMbs):
                MbToSliceGroupMap[i] = self.mapUnitToSliceGroupMap[i // (2 * sps.PicWidthInMbs)] + (
                        2 * (i % sps.PicWidthInMbs)
                ) + (i // sps.PicWidthInMbs) % 2
        else:
            raise ValueError("set up MbToSliceGroupMap failed.")

        self.MbToSliceGroupMap = MbToSliceGroupMap

    def NextMbAddress(self, n):
        i = n + 1

        while i < self.PicSizeInMbs and self.MbToSliceGroupMap[i] != self.MbToSliceGroupMap[n]:
            i += 1

        return i

    def byte_aligned(self):
        return self.s.pos % 8 == 0

    def sub_mb_pred(self, mb_type, mb, sps, pps):
        sub_mb_type = [0] * 4
        for mbPartIdx in range(4):
            sub_mb_type[mbPartIdx] = self.ue("sub_mb_type")

        ref_idx_l0 = [0] * 4
        for mbPartIdx in range(4):
            if (
                    self.num_ref_idx_l0_active_minus1 > 0 or self.mb_field_decoding_flag != self.field_pic_flag) and mb_type != P_8x8ref0 and \
                    sub_mb_type[mbPartIdx] != B_Direct_8x8 and mb.SubMbPredMode(sub_mb_type[mbPartIdx]) != Pred_L1:
                ref_idx_l0[mbPartIdx] = self.te(pps.num_ref_idx_l0_active_minus1)
            mb.ref_idx_l0 = ref_idx_l0

        ref_idx_l1 = [0] * 4
        for mbPartIdx in range(4):
            if ((self.num_ref_idx_l1_active_minus1 > 0 or
                 self.mb_field_decoding_flag != self.field_pic_flag) and
                    sub_mb_type[mbPartIdx] != B_Direct_8x8 and
                    mb.SubMbPredMode(sub_mb_type[mbPartIdx]) != Pred_L0):
                ref_idx_l1[mbPartIdx] = self.te(pps.num_ref_idx_l1_active_minus1)
            mb.ref_idx_l1 = ref_idx_l1

        mvd_l0, mvd_l1 = mb.mvd_l0, mb.mvd_l1
        for mbPartIdx in range(4):
            if (sub_mb_type[mbPartIdx] != B_Direct_8x8 and
                    mb.SubMbPredMode(sub_mb_type[mbPartIdx]) != Pred_L1):
                for subMbPartIdx in range(mb.NumSubMbPart(sub_mb_type[mbPartIdx])):
                    for compIdx in range(2):
                        mvd_l0[mbPartIdx][subMbPartIdx][compIdx] = self.se("mvd_l0")

        for mbPartIdx in range(4):
            if (sub_mb_type[mbPartIdx] != B_Direct_8x8 and
                    mb.SubMbPredMode(sub_mb_type[mbPartIdx]) != Pred_L0):

                for subMbPartIdx in range(mb.NumSubMbPart(sub_mb_type[mbPartIdx])):
                    for compIdx in range(2):
                        mvd_l1[mbPartIdx][subMbPartIdx][compIdx] = self.se("mvd_l1")

    def mb_pred(self, mb_type, mb):
        sps, pps = self.sps, self.pps
        partPredMode0 = mb.MbPartPredMode(0)
        numMbPart = mb.NumMbPart()
        if partPredMode0 in (Intra_4x4, Intra_8x8, Intra_16x16):

            if partPredMode0 == Intra_4x4:
                prev_intra4x4_pred_mode_flag = mb.prev_intra4x4_pred_mode_flag
                rem_intra4x4_pred_mode = mb.rem_intra4x4_pred_mode
                for luma4x4BlkIdx in range(16):
                    prev_intra4x4_pred_mode_flag[luma4x4BlkIdx] = self.u(1, "prev_intra4x4_pred_mode_flag")
                    if not prev_intra4x4_pred_mode_flag[luma4x4BlkIdx]:
                        rem_intra4x4_pred_mode[luma4x4BlkIdx] = self.u(3, "rem_intra4x4_pred_mode")

            if partPredMode0 == Intra_8x8:
                prev_intra8x8_pred_mode_flag = mb.prev_intra8x8_pred_mode_flag
                rem_intra8x8_pred_mode = mb.rem_intra8x8_pred_mode

                for luma8x8BlkIdx in range(4):
                    prev_intra8x8_pred_mode_flag[luma8x8BlkIdx] = self.u(1, "prev_intra8x8_pred_mode_flag")
                    if not prev_intra8x8_pred_mode_flag[luma8x8BlkIdx]:
                        rem_intra8x8_pred_mode[luma8x8BlkIdx] = self.u(3, "rem_intra8x8_pred_mode")
            if self.ChromaArrayType == 1 or self.ChromaArrayType == 2:
                intra_chroma_pred_mode = self.ue("intra_chroma_pred_mode")
                mb.intra_chroma_pred_mode = intra_chroma_pred_mode
        elif partPredMode0 != Direct:
            num_ref_idx_l0_active_minus1 = pps.num_ref_idx_l0_active_minus1
            num_ref_idx_l1_active_minus1 = pps.num_ref_idx_l1_active_minus1
            mb_field_decoding_flag = self.mb_field_decoding_flag
            field_pic_flag = self.field_pic_flag
            ref_idx_l0, ref_idx_l1 = mb.ref_idx_l0, mb.ref_idx_l1
            for mbPartIdx in range(numMbPart):
                if (num_ref_idx_l0_active_minus1 > 0 or mb_field_decoding_flag != field_pic_flag) and mb.MbPartPredMode(
                        mbPartIdx) != Pred_L1:
                    ref_idx_l0[mbPartIdx] = self.te(num_ref_idx_l0_active_minus1, "ref_idx_l0")
            for mbPartIdx in range(numMbPart):
                if (num_ref_idx_l1_active_minus1 > 0 or mb_field_decoding_flag != field_pic_flag) and mb.MbPartPredMode(
                        mbPartIdx) != Pred_L0:
                    ref_idx_l1[mbPartIdx] = self.te(num_ref_idx_l1_active_minus1, "ref_idx_l1")

            mvd_l0 = mb.mvd_l0
            for mbPartIdx in range(numMbPart):
                if mb.MbPartPredMode(mbPartIdx) != Pred_L1:
                    for compIdx in range(2):
                        mvd_l0[mbPartIdx][0][compIdx] = self.se("mvd_l0")

            mvd_l1 = mb.mvd_l1
            for mbPartIdx in range(numMbPart):
                if mb.MbPartPredMode(mbPartIdx) != Pred_L0:
                    for compIdx in range(2):
                        mvd_l1[mbPartIdx][0][compIdx] = self.se("mvd_l1")

    def residual(self, startIdx, endIdx, mb):
        sps, pps = self.sps, self.pps
        if not pps.entropy_coding_mode_flag:
            residual_block = self.residual_block_cavlc
        else:
            raise NotImplementedError("CAVLC decoding is not implemented.")

        i16x16DClevel, i16x16AClevel, level4x4, level8x8 = mb.i16x16DClevel, mb.i16x16AClevel, mb.level4x4, mb.level8x8
        self.residual_luma(i16x16DClevel, i16x16AClevel, level4x4, level8x8, startIdx, endIdx, mb,
                           Invoker.Intra16x16DCLevel, Invoker.Intra16x16ACLevel,
                           Invoker.LumaLevel4x4, Invoker.LumaLevel8x8)
        Intra16x16DCLevel = i16x16DClevel
        Intra16x16ACLevel = i16x16AClevel
        LumaLevel4x4 = level4x4
        LumaLevel8x8 = level8x8

        ChromaArrayType = self.ChromaArrayType
        CodedBlockPatternChroma, CodedBlockPatternLuma = mb.get_coded_block_pattern()
        if ChromaArrayType in (1, 2):

            ChromaDCLevel, ChromaACLevel = mb.ChromaDCLevel, mb.ChromaACLevel

            NumC8x8 = 4 // (self.SubWidthC * self.SubHeightC)
            for iCbCr in range(2):
                if (CodedBlockPatternChroma & 3) and startIdx == 0:
                    residual_block(ChromaDCLevel[iCbCr], 0, 4 * NumC8x8 - 1, 4 * NumC8x8,
                                   mb, Invoker.ChromaDCLevel)
                else:
                    for i in range(4 * NumC8x8):
                        ChromaDCLevel[iCbCr][i] = 0

            for iCbCr in range(2):
                for i8x8 in range(NumC8x8):
                    for i4x4 in range(4):
                        BlkIdx = i8x8 * 4 + i4x4
                        if CodedBlockPatternChroma & 2:
                            residual_block(ChromaACLevel[iCbCr][i8x8 * 4 + i4x4], max(0, startIdx - 1), endIdx - 1, 15,
                                           mb, Invoker.ChromaACLevelCr, BlkIdx)
                        else:
                            for i in range(15):
                                ChromaACLevel[iCbCr][BlkIdx][i] = 0

        elif ChromaArrayType == 3:
            self.residual_luma(i16x16DClevel, i16x16AClevel, level4x4, level8x8, startIdx, endIdx, mb,
                               Invoker.CbIntra16x16DCLevel, Invoker.CbIntra16x16ACLevel,
                               Invoker.CbLevel4x4, Invoker.CbLevel8x8)
            CbIntra16x16DCLevel = i16x16DClevel
            CbIntra16x16ACLevel = i16x16AClevel
            CbLevel4x4 = level4x4
            CbLevel8x8 = level8x8

            self.residual_luma(i16x16DClevel, i16x16AClevel, level4x4, level8x8, startIdx, endIdx, mb,
                               Invoker.CrIntra16x16DCLevel, Invoker.CrIntra16x16ACLevel,
                               Invoker.CrLevel4x4, Invoker.CrLevel8x8)

            CrIntra16x16DCLevel = i16x16DClevel
            CrIntra16x16ACLevel = i16x16AClevel
            CrLevel4x4 = level4x4
            CrLevel8x8 = level8x8

    def residual_luma(self, i16x16DClevel, i16x16AClevel, level4x4, level8x8, startIdx, endIdx, mb,
                      dc_invoker: Invoker, ac_invoker: Invoker, l4_invoker: Invoker, l8_invoker: Invoker):
        sps, pps = self.sps, self.pps
        if not pps.entropy_coding_mode_flag:
            residual_block = self.residual_block_cavlc
        else:
            raise NotImplementedError("CAVLC decoding is not implemented.")

        MbPartPredMod0 = mb.MbPartPredMode(0)
        transform_size_8x8_flag = mb.transform_size_8x8_flag
        entropy_coding_mode_flag = pps.entropy_coding_mode_flag
        CodedBlockPatternLuma, CodedBlockPatternChroma = mb.get_coded_block_pattern()

        if startIdx == 0 and MbPartPredMod0 == Intra_16x16:
            residual_block(i16x16DClevel, 0, 15, 16, mb, dc_invoker)
        for i8x8 in range(4):
            if not transform_size_8x8_flag or not entropy_coding_mode_flag:
                for i4x4 in range(4):
                    BlkIdx = i8x8 * 4 + i4x4
                    if CodedBlockPatternLuma & (1 << i8x8):
                        if MbPartPredMod0 == Intra_16x16:
                            residual_block(i16x16AClevel[BlkIdx],
                                           max(0, startIdx - 1), endIdx - 1, 15, mb, ac_invoker, BlkIdx)
                        else:
                            residual_block(level4x4[BlkIdx], startIdx, endIdx, 16,
                                           mb, l4_invoker, BlkIdx)
                    elif MbPartPredMod0 == Intra_16x16:
                        for i in range(15):
                            i16x16AClevel[BlkIdx][i] = 0
                    else:
                        for i in range(16):
                            level4x4[BlkIdx][i] = 0
                    if not entropy_coding_mode_flag and transform_size_8x8_flag:
                        for i in range(16):
                            level8x8[i8x8][4 * i + i4x4] = level4x4[BlkIdx][i]
            else:
                # after implement CAVLC, use codes below
                raise NotImplementedError("CAVLC decoding is not implemented.")
            # elif CodedBlockPatternLuma & (1 << i8x8):
            #     residual_block(level8x8[i8x8], 4 * startIdx, 4 * endIdx + 3, 64, mb, l8_invoker)
            # else:
            #     for i in range(64):
            #         level8x8[i8x8][i] = 0

    def residual_block_cavlc(self, coeffLevel, startIdx, endIdx, maxNumCoeff, mb: MacroBlock, invoker: Invoker, blkIdx=0):
        def get_suffixLength(l_p, s_l):
            if l_p == 14 and s_l == 0:
                return 4
            if l_p >= 15:
                return l_p - 3
            return s_l

        # step 1
        for i in range(maxNumCoeff):
            coeffLevel[i] = 0

        # step 2
        totalCoeff, trailingOnes, nC = self.ce1(mb, invoker, blkIdx)
        mb.TotalCoeff[blkIdx] = totalCoeff

        # step 3
        if totalCoeff > 0:
            levelVal = [0] * totalCoeff

            # 9.2.2 Parsing process for level information
            if totalCoeff > 10 and trailingOnes < 3:
                suffixLength = 1
            else:
                suffixLength = 0
            for i in range(totalCoeff):
                if i < trailingOnes:
                    trailing_ones_sign_flag = self.u(1, "trailing_ones_sign_flag")
                    levelVal[i] = 1 - 2 * trailing_ones_sign_flag
                else:
                    level_prefix = self.ce2()
                    levelSuffixSize = get_suffixLength(level_prefix, suffixLength)

                    levelCode = min(15, level_prefix) << suffixLength
                    if suffixLength > 0 or level_prefix >= 14:
                        level_suffix = self.u(levelSuffixSize, "level_suffix")
                        levelCode += level_suffix
                    if level_prefix >= 15 and suffixLength == 0:
                        levelCode += 15
                    if level_prefix >= 16:
                        levelCode += (1 << (level_prefix - 3)) - 4096
                    if i == trailingOnes and trailingOnes < 3:
                        levelCode += 2
                    if levelCode % 2 == 0:
                        levelVal[i] = (levelCode + 2) >> 1
                    else:
                        levelVal[i] = (-levelCode - 1) >> 1
                    if suffixLength == 0:
                        suffixLength = 1
                    if abs(levelVal[i]) > (3 << (suffixLength - 1)) and suffixLength < 6:
                        suffixLength += 1

            # 9.2.3 Parsing process for run information
            runVal = [0] * totalCoeff

            if totalCoeff < endIdx - startIdx + 1:
                total_zeros = self.ce3(maxNumCoeff, totalCoeff)
                zerosLeft = total_zeros
            else:
                zerosLeft = 0
            for i in range(totalCoeff - 1):
                if zerosLeft > 0 and i >= totalCoeff - min(totalCoeff, 4):
                    run_before = self.ce4(zerosLeft)
                    runVal[i] -= run_before
                else:
                    runVal[i] = 0
                    zerosLeft = zerosLeft - runVal[i]
            runVal[totalCoeff - 1] = zerosLeft

            # 9.2.4 Combining level and run information
            coeffNum = -1
            for i in range(totalCoeff - 1, -1, -1):
                coeffNum += runVal[i] + 1
                coeffLevel[startIdx + coeffNum] = levelVal[i]

    def ce1(self, mb, invoker: Invoker, blkIdx):
        """
        9.2.1
        parsing TotalCoeff, TrailingOnes and nC
        return TotalCoeff, TrailingOnes, nC
        """
        pos = self.s.pos
        nC = self.get_nc(mb, invoker, blkIdx)
        TotalCoeff, TrailingOnes = cavlc.coeff_token(self.s, nC)
        logger.debug(f'total_coeff={TotalCoeff}, trailing_ones={TrailingOnes}, nC={nC}, pos={pos}')
        return TotalCoeff, TrailingOnes, nC

    def get_nc(self, mb, invoker, blkIdx):
        """
        9.2.1
        """
        sps, pps = self.sps, self.pps
        ChromaArrayType = self.ChromaArrayType
        if invoker == Invoker.ChromaDCLevel:
            if ChromaArrayType == 1:
                return -1
            elif ChromaArrayType == 2:
                return -2
        # step 1, 2, 3
        if invoker in (Invoker.Intra16x16DCLevel, Invoker.CbIntra16x16DCLevel, Invoker.CrIntra16x16DCLevel):
            blkIdx = 0

        # step 4, get blkN
        if invoker in (Invoker.Intra16x16ACLevel, Invoker.Intra16x16DCLevel, Invoker.LumaLevel4x4):
            mbAddrA, blkA, mbAddrB, blkB = self.neighbouring_4x4_luma(mb, blkIdx)
        elif invoker in (Invoker.CbIntra16x16ACLevel, Invoker.CbIntra16x16DCLevel, Invoker.CbLevel4x4):
            mbAddrA, blkA, mbAddrB, blkB = self.neighbouring_4x4_chroma_3(mb, blkIdx)
        elif invoker in (Invoker.CrIntra16x16ACLevel, Invoker.CrIntra16x16DCLevel, Invoker.CrLevel4x4):
            mbAddrA, blkA, mbAddrB, blkB = self.neighbouring_4x4_chroma_3(mb, blkIdx)
        else:
            mbAddrA, blkA, mbAddrB, blkB = self.neighbouring_4x4_chroma(mb, blkIdx)

        # step 5, get availableFlagN
        availableFlagA = 1 if mbAddrA is not None else 0
        availableFlagB = 1 if mbAddrB is not None else 0

        mbAddrA_block, mbAddrB_block = None, None
        # step 6, get nN
        if availableFlagA:
            mbAddrA_block = self.get_macroblock(mbAddrA)
            if mbAddrA_block.mb_type in (P_Skip, B_Skip) or \
                    (mbAddrA_block.mb_type != I_PCM and mbAddrA_block.is_ac_residual_empty()):
                nA = 0
            elif mbAddrA_block.mb_type == I_PCM:
                nA = 16
            else:
                nA = mbAddrA_block.TotalCoeff[blkA]
        if availableFlagB:
            mbAddrB_block = self.get_macroblock(mbAddrB)
            if mbAddrB_block.mb_type in (P_Skip, B_Skip) or \
                    (mbAddrB_block.mb_type != I_PCM and mbAddrB_block.is_ac_residual_empty()):
                nB = 0
            elif mbAddrB_block.mb_type == I_PCM:
                nB = 16
            else:
                nB = mbAddrB_block.TotalCoeff[blkB]

        # step 7, get nC
        if availableFlagA and availableFlagB:
            nC = (nA + nB + 1) >> 1
        elif availableFlagA:
            nC = nA
        elif availableFlagB:
            nC = nB
        else:
            nC = 0

        return nC

    def neighbouring_4x4_luma(self, mb, blkIdx):
        """
        6.4.11.4
        """

        def get_mb_addr_and_blk_idx(xD, yD):
            # step 2
            x, y = inverse_4x4_luma_block_scanning(blkIdx)

            # step 3
            xN = x + xD
            yN = y + yD

            # step 4
            mbAddrN, (xW, yW) = self.derive_neighbour_location(mb, xN, yN)

            # step 5
            if mbAddrN is None:
                luma4x4BlkIdxN = None
            else:
                luma4x4BlkIdxN = derive_4x4_luma_blkIdx(xW, yW)

            return mbAddrN, luma4x4BlkIdxN

        mbAddrA, luma4x4BlkIdxA = get_mb_addr_and_blk_idx(-1, 0)
        mbAddrB, luma4x4BlkIdxB = get_mb_addr_and_blk_idx(0, -1)
        return mbAddrA, luma4x4BlkIdxA, mbAddrB, luma4x4BlkIdxB

    def derive_neighbour_location(self, mb, xN, yN, is_luma=True):
        """
        6.4.12 Derivation process for neighbouring locations
        """
        if is_luma:
            maxW, maxH = 16, 16
        else:
            maxW, maxH = self.MbWidthC, self.MbHeightC

        none_ret = None, (0, 0)
        if not self.MbaffFrameFlag:
            # 6.4.12.1 Specification for neighbouring locations in fields and non-MBAFF frames
            if (xN > maxW and 0 <= yN < maxH) or yN >= maxH:
                return none_ret
            if 0 <= xN < maxW and 0 <= yN < maxH:
                return mb.CurrMbAddr, (xN, yN)
            if xN < 0 and yN < 0:
                mb_addr, avail = self.derive_neighbour_addr(mb, MbAddrN.mbAddrD)
            elif xN < 0 <= yN < maxH:
                mb_addr, avail = self.derive_neighbour_addr(mb, MbAddrN.mbAddrA)
            elif maxW > xN >= 0 > yN:
                mb_addr, avail = self.derive_neighbour_addr(mb, MbAddrN.mbAddrB)
            elif xN >= maxW and yN < 0:
                mb_addr, avail = self.derive_neighbour_addr(mb, MbAddrN.mbAddrC)
            else:
                raise ValueError(f"derive neighbour location failed: xN={xN}, yN={yN}")

            if not avail:
                return none_ret
            xW = (xN + maxW) % maxW
            yW = (yN + maxH) % maxH
            return mb_addr, (xW, yW)
        else:
            raise NotImplementedError("MbaffFrameFlag is not implemented.")

    def derive_neighbour_addr(self, mb, addr_type: MbAddrN):
        """
        6.4.9 Derivation process for neighbouring macroblock addresses and their availability
        """

        def is_avail(a):
            return 0 <= a <= CurrMbAddr

        CurrMbAddr = mb.CurrMbAddr
        PicWidthInMbs = self.PicWidthInMbs
        if addr_type == MbAddrN.mbAddrA:
            addr = CurrMbAddr - 1
            return addr, CurrMbAddr % PicWidthInMbs != 0 and is_avail(addr)
        elif addr_type == MbAddrN.mbAddrB:
            addr = CurrMbAddr - PicWidthInMbs
            return addr, is_avail(addr)
        elif addr_type == MbAddrN.mbAddrC:
            addr = CurrMbAddr - PicWidthInMbs + 1
            return addr, (CurrMbAddr + 1) % PicWidthInMbs != 0 and is_avail(addr)
        else:
            addr = CurrMbAddr - PicWidthInMbs - 1
            return addr, CurrMbAddr % PicWidthInMbs != 0 and is_avail(addr)

    def neighbouring_4x4_chroma(self, mb, blkIdx):
        """
        6.4.11.5 Derivation process for neighbouring 4x4 chroma blocks
        """

        def get_mb_addr_and_blk_idx(xD, yD):
            # step 2
            x, y = inverse_4x4_chroma_block_scanning(blkIdx)

            # step 3
            xN = x + xD
            yN = y + yD

            # step 4
            mbAddrN, (xW, yW) = self.derive_neighbour_location(mb, xN, yN)

            # step 5
            if mbAddrN is None:
                luma4x4BlkIdxN = None
            else:
                luma4x4BlkIdxN = derive_4x4_chroma_blkIdx(xW, yW)

            return mbAddrN, luma4x4BlkIdxN

        mbAddrA, luma4x4BlkIdxA = get_mb_addr_and_blk_idx(-1, 0)
        mbAddrB, luma4x4BlkIdxB = get_mb_addr_and_blk_idx(0, -1)
        return mbAddrA, luma4x4BlkIdxA, mbAddrB, luma4x4BlkIdxB

    def neighbouring_4x4_chroma_3(self, mb, blkIdx):
        """
        6.4.11.6 Derivation process for neighbouring 4x4 chroma blocks for ChromaArrayType equal to 3
        """
        raise NotImplementedError("Derivation process for neighbouring 4x4 chroma blocks for ChromaArrayType equal to "
                                  "3 is not implemented.")

    def get_macroblock(self, addr) -> MacroBlock:
        if addr is None:
            raise ValueError("addr is None.")
        return self.macroblocks.get(addr)

    def ce2(self):
        """
        9.2.2.1 Parsing process for level_prefix
        """
        pos = self.s.pos
        level_prefix = cavlc.parse_level_prefix(self.s)
        logger.debug(f'level_prefix={level_prefix}, pos={pos}')
        return level_prefix

    def ce3(self, MaxNumCoeff, TotalCoeff):
        """
        parse total_zeros
        """
        pos = self.s.pos
        total_zeros = cavlc.parse_total_zeros(self.s, MaxNumCoeff, TotalCoeff)
        logger.debug(f'total_zeros={total_zeros}, pos={pos}')
        return total_zeros

    def ce4(self, zerosLeft):
        """
        parse run_before
        """
        pos = self.s.pos
        run_before = cavlc.parse_run_before(self.s, zerosLeft)
        logger.debug(f'run_before={run_before}, pos={pos}')
        return run_before

    def me(self, mb, info=None):
        ChromaArrayType = self.ChromaArrayType
        is_intra_4_8 = mb.mb_type == I_NxN
        is_inter = mb.mb_type >= P_SP_START

        if not is_intra_4_8 and not is_inter:
            raise ValueError("mb_type is not intra_4_8 or inter.")

        index = 0 if is_intra_4_8 else 1

        code_num = self.ue(info)
        if ChromaArrayType in [1, 2]:
            return CODE_NUM_MAP_TYPE_1_2[code_num][index]
        elif ChromaArrayType in [0, 3]:
            return CODE_NUM_MAP_TYPE_0_3[code_num][index]


class CodedSliceIDR(VCLSlice):
    """
    Coded slice of an IDR picture.
    """

    def __init__(self, rbsp_bytes, nalu_sps, nalu_pps, verbose, include_header=False):
        order = [
            "first_mb_in_slice",
            "slice_type",
            "slice_type_clear",
            "pic_parameter_set_id",
            "colour_plane_id",
            "frame_num",
            "field_pic_flag",
            "bottom_field_flag",
            "idr_pic_id",
        ]
        super(CodedSliceIDR, self).__init__(rbsp_bytes, nalu_sps, nalu_pps, verbose, order, include_header)

        self.print_verbose()


class CodedSliceNonIDR(VCLSlice):
    """
    Coded slice of a non-IDR picture.
    """

    def __init__(self, rbsp_bytes, nalu_sps, nalu_pps, verbose, include_header=False):
        super(CodedSliceNonIDR, self).__init__(rbsp_bytes, nalu_sps, nalu_pps, verbose, None, include_header)

        self.print_verbose()

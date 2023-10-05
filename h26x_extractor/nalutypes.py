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

from bitstring import BitStream
from tabulate import tabulate

from h26x_extractor import nalu_utils

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
            self.forbidden_zero_bit = self.s.read("uint:1")
            self.nal_ref_idc = self.s.read("uint:2")
            self.nal_unit_type = self.s.read("uint:5")

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
                        to_print.append([key, value])
            for key, value in sorted(vars(self).items()):
                if key == "verbose" or key == "s" or key == "order":
                    continue
                if self.order and key in self.order:
                    continue
                to_print.append([key, value])
            print(tabulate(to_print, headers=["field", "value"], tablefmt="grid"))


class AUD(NALU):
    """
    Access Unit Delimiter
    """

    def __init__(self, rbsp_bytes, verbose):
        super(AUD, self).__init__(rbsp_bytes, verbose)

        self.primary_pic_type = self.s.read("uint:3")

        self.print_verbose()


class VCLSlice(NALU):
    def __init__(self, rbsp_bytes, nalu_sps, nalu_pps, verbose, order=None, include_header=False):
        super(VCLSlice, self).__init__(
            rbsp_bytes, verbose, order, include_header=include_header
        )

        # 7.3.2.8 Slice layer without partitioning RBSP syntax
        # values to be parsed from header
        # slice_header()
        self.first_mb_in_slice = None
        self.slice_type = None
        self.pic_parameter_set_id = None
        self.colour_plane_id = None
        self.frame_num = None
        self.field_pic_flag = None
        self.bottom_field_flag = None
        self.idr_pic_id = None
        self.pic_order_cnt_lsb = None
        self.delta_pic_order_cnt_bottom = None
        self.delta_pic_order_cnt = None
        self.redundant_pic_cnt = None
        self.direct_spatial_mv_pred_flag = None
        self.num_ref_idx_active_override_flag = None
        self.num_ref_idx_l0_active_minus1 = 0  # this value should set default value
        self.num_ref_idx_l1_active_minus1 = None
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

        # start parsing header
        self.slice_header(nalu_sps, nalu_pps)

        # values to be parsed from header
        # slice_data()
        self.mb_skip_run = None
        self.mb_field_decoding_flag = None

        self.macroblocks = []

        # self.slice_data(nalu_sps, nalu_pps)
        # self.rbsp_trailing_bits()

    def slice_header(self, sps, pps):
        """
        parse slice_header
        7.3.3 Slice header syntax
        """
        self.first_mb_in_slice = self.s.read("ue")
        self.slice_type = self.s.read("ue")
        self.slice_type_clear = _get_slice_type(self.slice_type)
        self.pic_parameter_set_id = self.s.read("ue")
        if sps.separate_colour_plane_flag == 1:
            self.colour_plane_id = self.s.read("uint:2")
        self.frame_num = self.s.read("uint:%i" % (sps.log2_max_frame_num_minus4 + 4))
        if not sps.frame_mbs_only_flag:
            self.field_pic_flag = self.s.read("uint:1")
            if self.field_pic_flag:
                self.bottom_field_flag = self.s.read("uint:1")

        # IdrPicFlag = ((nal_unit_type = = 5) ? 1: 0)
        IdrPicFlag = self.nal_unit_type == 5
        if IdrPicFlag:
            self.idr_pic_id = self.s.read("ue")

        if sps.pic_order_cnt_type == 0:
            self.pic_order_cnt_lsb = self.s.read(
                "uint:%i" % (sps.log2_max_pic_order_cnt_lsb_minus4 + 4)
            )
            if (
                    pps.bottom_field_pic_order_in_frame_present_flag
                    and not self.field_pic_flag
            ):
                self.delta_pic_order_cnt_bottom = self.s.read("se")

        if sps.pic_order_cnt_type == 1 and not sps.delta_pic_order_always_zero_flag:
            self.delta_pic_order_cnt = []
            self.delta_pic_order_cnt.append(self.s.read("se"))
            if (
                    pps.bottom_field_pic_order_in_frame_present_flag and not self.field_pic_flag
            ):
                self.delta_pic_order_cnt.append(self.s.read("se"))

        if pps.redundant_pic_cnt_present_flag:
            self.redundant_pic_cnt = self.s.read("ue")

        if self.slice_type_clear == "B":
            self.direct_spatial_mv_pred_flag = self.s.read("uint:1")

        if self.slice_type_clear in ["P", "SP", "B"]:
            self.num_ref_idx_active_override_flag = self.s.read("uint:1")
            if self.num_ref_idx_active_override_flag:
                self.num_ref_idx_l0_active_minus1 = self.s.read("ue")
                if self.slice_type_clear == "B":
                    self.num_ref_idx_l1_active_minus1 = self.s.read("ue")

        # TODO: nal_unit == 20 or nal_unit == 21
        # ref_pic_list_mvc_modification( ) /* specified in Annex H */

        self.ref_pic_list_modification(sps, pps)
        if (
                pps.weighted_pred_flag
                and (self.slice_type_clear == "P" or self.slice_type_clear == "SP")
        ) or (
                pps.weighted_bipred_idc == 1 and self.slice_type_clear == "B"
        ):
            self.pred_weight_table(sps, pps)

        if self.nal_ref_idc != 0:
            self.dec_ref_pic_marking(sps, pps)

        if pps.entropy_coding_mode_flag and self.slice_type_clear != "I" and self.slice_type_clear != "SI":
            self.cabac_init_idc = self.s.read("ue")
        self.slice_qp_delta = self.s.read("se")

        if self.slice_type_clear == "SP" or self.slice_type_clear == "SI":
            if self.slice_type_clear == "SP":
                self.sp_for_switch_flag = self.s.read("uint:1")
            self.slice_qs_delta = self.s.read("se")

        if pps.deblocking_filter_control_present_flag:
            self.disable_deblocking_filter_idc = self.s.read("ue")
            if self.disable_deblocking_filter_idc != 1:
                self.slice_alpha_c0_offset_div2 = self.s.read("se")
                self.slice_beta_offset_div2 = self.s.read("se")

        if pps.num_slice_groups_minus1 > 0 and 3 <= pps.slice_group_map_type <= 5:
            PicHeightInMapUnits = sps.pic_height_in_map_units_minus1 + 1
            PicWidthInMbs = sps.pic_width_in_mbs_minus1 + 1
            PicSizeInMapUnits = PicWidthInMbs * PicHeightInMapUnits

            # bits length: Ceil( Log2( PicSizeInMapUnits ÷ SliceGroupChangeRate + 1 ) )
            self.slice_group_change_cycle = self.s.read(
                "uint:%i" % (math.ceil(math.log(PicSizeInMapUnits / pps.slice_group_change_rate + 1, 2)))
            )

    def rbsp_trailing_bits(self):
        # 7.3.2.11
        #   rbsp_stop_one_bit /* equal to 1 */
        #   while( !byte_aligned( ) )
        #        rbsp_alignment_zero_bit /* equal to 0 */
        pass

    def ref_pic_list_modification(self, sps, pps):
        if self.slice_type % 5 != 2 and self.slice_type % 5 != 4:
            self.ref_pic_list_modification_flag_l0 = self.s.read("uint:1")
            if self.ref_pic_list_modification_flag_l0:
                while True:
                    self.modification_of_pic_nums_idc = self.s.read("ue")
                    if self.modification_of_pic_nums_idc == 0 or self.modification_of_pic_nums_idc == 1:
                        self.abs_diff_pic_num_minus1 = self.s.read("ue")
                    elif self.modification_of_pic_nums_idc == 2:
                        self.long_term_pic_num = self.s.read("ue")

                    if self.modification_of_pic_nums_idc == 3:
                        break

        if self.slice_type % 5 == 1:
            self.ref_pic_list_modification_flag_l1 = self.s.read("uint:1")
            if self.ref_pic_list_modification_flag_l1:
                while True:
                    self.modification_of_pic_nums_idc = self.s.read("ue")
                    if self.modification_of_pic_nums_idc == 0 or self.modification_of_pic_nums_idc == 1:
                        self.abs_diff_pic_num_minus1 = self.s.read("ue")
                    elif self.modification_of_pic_nums_idc == 2:
                        self.long_term_pic_num = self.s.read("ue")

                    if self.modification_of_pic_nums_idc == 3:
                        break

    def pred_weight_table(self, sps, pps):
        self.luma_log2_weight_denom = self.s.read("ue")
        if sps.ChromaArrayType != 0:
            self.chroma_log2_weight_denom = self.s.read("ue")

        self.luma_weight_l0 = [0] * (self.num_ref_idx_l0_active_minus1 + 1)
        self.luma_offset_l0 = [0] * (self.num_ref_idx_l0_active_minus1 + 1)
        self.chroma_weight_l0 = [[[0] * 2] for _ in range(self.num_ref_idx_l0_active_minus1 + 1)]
        self.chroma_offset_l0 = [[[0] * 2] for _ in range(self.num_ref_idx_l0_active_minus1 + 1)]

        for i in range(self.num_ref_idx_l0_active_minus1 + 1):
            self.luma_weight_l0_flag = self.s.read("uint:1")
            if self.luma_weight_l0_flag:
                self.luma_weight_l0[i] = self.s.read("se")
                self.luma_offset_l0[i] = self.s.read("se")
            if sps.ChromaArrayType != 0:
                self.chroma_weight_l0_flag = self.s.read("uint:1")
                if self.chroma_weight_l0_flag:
                    for j in range(2):
                        self.chroma_weight_l0[i][j] = self.s.read("se")
                        self.chroma_offset_l0[i][j] = self.s.read("se")

        self.luma_weight_l1 = [0] * (self.num_ref_idx_l0_active_minus1 + 1)
        self.luma_offset_l1 = [0] * (self.num_ref_idx_l0_active_minus1 + 1)
        self.chroma_weight_l1 = [[[0] * 2] for _ in range(self.num_ref_idx_l0_active_minus1 + 1)]
        self.chroma_offset_l1 = [[[0] * 2] for _ in range(self.num_ref_idx_l0_active_minus1 + 1)]
        if self.slice_type % 5 == 1:
            for i in range(self.num_ref_idx_l1_active_minus1 + 1):
                self.luma_weight_l1_flag = self.s.read("uint:1")
                if self.luma_weight_l1_flag:
                    self.luma_weight_l1[i] = self.s.read("se")
                    self.luma_offset_l1[i] = self.s.read("se")
                if sps.ChromaArrayType != 0:
                    self.chroma_weight_l1_flag = self.s.read("uint:1")
                    if self.chroma_weight_l1_flag:
                        for j in range(2):
                            self.chroma_weight_l1[i][j] = self.s.read("se")
                            self.chroma_offset_l1[i][j] = self.s.read("se")

    def dec_ref_pic_marking(self, sps, pps):
        IdrPicFlag = self.nal_unit_type == 5
        if IdrPicFlag:
            self.no_output_of_prior_pics_flag = self.s.read("uint:1")
            self.long_term_reference_flag = self.s.read("uint:1")
        else:
            self.adaptive_ref_pic_marking_mode_flag = self.s.read("uint:1")
            if self.adaptive_ref_pic_marking_mode_flag:
                while True:
                    self.memory_management_control_operation = self.s.read("ue")
                    if self.memory_management_control_operation == 0 or self.memory_management_control_operation == 1:
                        self.difference_of_pic_nums_minus1 = self.s.read("ue")
                    elif self.memory_management_control_operation == 2:
                        self.long_term_pic_num = self.s.read("ue")
                    elif self.memory_management_control_operation == 3 or self.memory_management_control_operation == 6:
                        self.long_term_frame_idx = self.s.read("ue")
                    elif self.memory_management_control_operation == 4:
                        self.max_long_term_frame_idx_plus1 = self.s.read("ue")

                    if self.memory_management_control_operation == 0:
                        break

    def slice_data(self, sps, pps):
        if pps.entropy_coding_mode_flag:
            raise NotImplementedError("CABAC decoding is not implemented.")
        # MbaffFrameFlag = ( mb_adaptive_frame_field_flag && !field_pic_flag )
        MbaffFrameFlag = 1 if (sps.mb_adaptive_frame_field_flag and not self.field_pic_flag) else 0
        CurrMbAddr = self.first_mb_in_slice * (1 + MbaffFrameFlag)
        moreDataFlag = True
        prevMbSkipped = False
        while moreDataFlag:
            if self.slice_type_clear != "I" and self.slice_type_clear != "SI":
                if not pps.entropy_coding_mode_flag:
                    self.mb_skip_run = self.s.read("ue")
                    prevMbSkipped = self.mb_skip_run > 0
                    for i in range(self.mb_skip_run):
                        # TODO
                        CurrMbAddr = self.NextMbAddress(CurrMbAddr)
                    if self.mb_skip_run > 0:
                        moreDataFlag = self.more_rbsp_data()
                else:
                    raise NotImplementedError("CABAC decoding is not implemented.")
            if moreDataFlag:
                if MbaffFrameFlag and (CurrMbAddr % 2 == 0 or (CurrMbAddr % 2 == 1 and prevMbSkipped)):
                    self.mb_field_decoding_flag = self.s.read("uint:1")
                # TODO
                self.macroblock_layer(sps, pps)
            if not pps.entropy_coding_mode_flag:
                moreDataFlag = self.more_rbsp_data()
            else:
                raise NotImplementedError("CABAC decoding is not implemented.")
            CurrMbAddr = self.NextMbAddress(CurrMbAddr)

    def more_rbsp_data(self):
        return nalu_utils.more_rbsp_data(self.s)

    def macroblock_layer(self, sps, pps):
        pass


class MacroBlock:

    def __init__(self):
        self.mb_type = None

        # I_PCM
        self.pcm_alignment_zero_bit = None
        self.pcm_sample_luma = None
        self.pcm_sample_chroma = None

        self.transform_size_8x8_flag = None

        self.coded_block_pattern = None
        self.mb_qp_delta = None


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
        self.chroma_format_idc = None
        self.separate_colour_plane_flag = None
        self.ChromaArrayType = None
        self.bit_depth_luma_minus8 = None
        self.bit_depth_chroma_minus8 = None
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

            # If separate_colour_plane_flag is equal to 0, ChromaArrayType is set equal to chroma_format_idc.
            # – Otherwise (separate_colour_plane_flag is equal to 1), ChromaArrayType is set equal to 0.
            self.ChromaArrayType = self.chroma_format_idc if not self.separate_colour_plane_flag else 0

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
    def __init__(self, rbsp_bytes, verbose):
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
        self.slice_group_map_type = None
        self.run_length_minus1 = None
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

        self.pic_parameter_set_rbsp()

        self.print_verbose()

    def pic_parameter_set_rbsp(self):
        self.pic_parameter_set_id = self.s.read("ue")
        self.seq_parameter_set_id = self.s.read("ue")
        self.entropy_coding_mode_flag = self.s.read("uint:1")
        self.bottom_field_pic_order_in_frame_present_flag = self.s.read("uint:1")
        self.num_slice_groups_minus1 = self.s.read("ue")
        if self.num_slice_groups_minus1 > 0:
            self.slice_group_map_type = self.s.read("ue")
            if self.slice_group_map_type == 0:
                self.run_length_minus1 = []
                for i_group in range(self.num_slice_groups_minus1 + 1):
                    self.run_length_minus1.append(self.s.read("ue"))
            elif self.slice_group_map_type == 2:
                self.top_left = []
                self.bottom_right = []
                for i_group in range(self.num_slice_groups_minus1 + 1):
                    self.top_left.append(self.s.read("ue"))
                    self.bottom_right.append(self.s.read("ue"))
            elif self.slice_group_map_type in [3, 4, 5]:
                self.slice_group_change_direction_flag = self.s.read("uint:1")
                self.slice_group_change_rate_minus1 = self.s.read("ue")
            elif self.slice_group_map_type == 6:
                self.pic_size_in_map_units_minus1 = self.s.read("ue")
                self.slice_group_id = []
                for i in range(self.pic_size_in_map_units_minus1 + 1):
                    self.slice_group_id.append(self.s.read("uint:1"))
        self.num_ref_idx_l0_active_minus1 = self.s.read("ue")
        self.num_ref_idx_l1_active_minus1 = self.s.read("ue")
        self.weighted_pred_flag = self.s.read("uint:1")
        self.weighted_bipred_idc = self.s.read("uint:2")
        self.pic_init_qp_minus26 = self.s.read("se")
        self.pic_init_qs_minus26 = self.s.read("se")
        self.chroma_qp_index_offset = self.s.read("se")
        self.deblocking_filter_control_present_flag = self.s.read("uint:1")
        self.constrained_intra_pred_flag = self.s.read("uint:1")
        self.redundant_pic_cnt_present_flag = self.s.read("uint:1")

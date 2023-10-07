import unittest
from pathlib import Path

from crypt import utils
from h26x_extractor import h26x_parser, nalutypes


class NaluTypesTest(unittest.TestCase):
    def test_vcl_class(self):
        file = Path("../v/input/small_bunny_1080p_30fps_h264_keyframe_each_second_CAVLC.h264")
        file = Path("/Users/jusbin/Movies/vlc/FourPeople_1280x720_60.h264")
        data = bytes(utils.read_file(file))
        ex = h26x_parser.H26xParser(file, verbose=True)

        verbose = True

        sps, pps = None, None
        for i, (start, end, is4bytes, fb, nri, nalu_type) in enumerate(ex.nalu_pos):
            raw_data = utils.nalu_decode(data[start: end + 1])
            if nalu_type == nalutypes.NAL_UNIT_TYPE_SPS:
                sps = nalutypes.SPS(raw_data[1:], verbose)
            if nalu_type == nalutypes.NAL_UNIT_TYPE_PPS:
                pps = nalutypes.PPS(raw_data[1:], verbose)
            if nalu_type in (nalutypes.NAL_UNIT_TYPE_CODED_SLICE_IDR, nalutypes.NAL_UNIT_TYPE_CODED_SLICE_NON_IDR):
                nalu_slice = nalutypes.VCLSlice(raw_data, sps, pps, True, include_header=True)


if __name__ == "__main__":
    unittest.main()
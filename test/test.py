#!/usr/bin/env python3

"""Simple unittest usage."""

import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from h26x_extractor import h26x_parser


class ParsingTest(unittest.TestCase):
    def testAUDParser(self):
        """Simple AUD parsing."""
        blob = "000000010910"
        # create parser
        ex = h26x_parser.H26xParser(None, verbose=True, use_bitstream=blob)
        # make sure decode is happy
        ex.parse()

    def testfileParser(self):
        ex = h26x_parser.H26xParser('../v/input/small_bunny_1080p_30fps_h264_keyframe_each_second_CAVLC.h264', verbose=False)
        ex = h26x_parser.H26xParser('/Users/jusbin/Code/h264/data/baseline.264', verbose=False)
        ex.parse()


if __name__ == "__main__":
    unittest.main()

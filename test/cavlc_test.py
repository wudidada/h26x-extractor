import unittest

from bitstring import BitStream

from h26x_extractor.cavlc import *


class CAVLCTest(unittest.TestCase):
    def test_coeff_token_1(self):
        for nC in range(2):
            stream = BitStream(b'\xff')
            self.assertEqual(coeff_token(stream, nC), (0, 0))
            self.assertEqual(stream.pos, 1)

            # 3 4 0000 11
            stream = BitStream(b'\x0f\xff')
            self.assertEqual(coeff_token(stream, nC), (4, 3))
            self.assertEqual(stream.pos, 6)

            # 2 6 0000 0001 01
            stream = BitStream(b'\x01\x4f\xff')
            self.assertEqual(coeff_token(stream, nC), (6, 2))
            self.assertEqual(stream.pos, 10)

    def test_coeff_token_2(self):
        for nC in range(2, 4):
            # 0 0 11
            stream = BitStream(b'\xff\xff')
            self.assertEqual(coeff_token(stream, nC), (0, 0))
            self.assertEqual(stream.pos, 2)

            # 2 2 011
            stream = BitStream(b'\x77\xff')
            self.assertEqual(coeff_token(stream, nC), (2, 2))
            self.assertEqual(stream.pos, 3)

            # 0 7 0000 0001 111
            stream = BitStream(b'\x01\xfe\xff')
            self.assertEqual(coeff_token(stream, nC), (7, 0))
            self.assertEqual(stream.pos, 11)

    def test_coeff_token_3(self):
        for nC in range(4, 8):
            # 0 0 1111
            stream = BitStream(b'\xff\xff')
            self.assertEqual(coeff_token(stream, nC), (0, 0))
            self.assertEqual(stream.pos, 4)

            # 2 2 1101
            stream = BitStream(b'\xdf\xff')
            self.assertEqual(coeff_token(stream, nC), (2, 2))
            self.assertEqual(stream.pos, 4)

            # 0 7 0001 000
            stream = BitStream(b'\x10\xfe\xff')
            self.assertEqual(coeff_token(stream, nC), (7, 0))
            self.assertEqual(stream.pos, 7)

    def test_coeff_token_4(self):
        for nC in range(8, 16):
            # 0 0 0000 11
            stream = BitStream(b'\x0f\xff')
            # self.assertEqual(coeff_token(stream, nC), (0, 0))
            # self.assertEqual(stream.pos, 6)

            # 2 2 0001 10
            stream = BitStream(b'\x18\xff')
            # self.assertEqual(coeff_token(stream, nC), (2, 2))
            # self.assertEqual(stream.pos, 6)

            # 0 7 0110 00
            stream = BitStream(b'\x60\x00\xff')
            self.assertEqual(coeff_token(stream, nC), (7, 0))
            self.assertEqual(stream.pos, 6)

            # 3 16 1111 11
            stream = BitStream(b'\xff\x00\xff')
            self.assertEqual(coeff_token(stream, nC), (16, 3))
            self.assertEqual(stream.pos, 6)

    def test_parse_level_prefix(self):
        stream = BitStream(b'\x01')
        self.assertEqual(parse_level_prefix(stream), 7)
        self.assertEqual(stream.pos, 8)

        stream = BitStream(b'\x00\x20')
        self.assertEqual(parse_level_prefix(stream), 10)
        self.assertEqual(stream.pos, 11)

    def test_parse_total_zeros(self):
        # test table_other
        stream = BitStream(b'\x61\x11')
        self.assertEqual(parse_total_zeros(stream, 7, 1), 1)
        self.assertEqual(stream.pos, 3)

        stream = BitStream(b'\x18\x12')
        self.assertEqual(parse_total_zeros(stream, 3, 3), 9)
        self.assertEqual(stream.pos, 5)

        # test table_4_8
        stream = BitStream(b'\xff')
        self.assertEqual(parse_total_zeros(stream, 4, 1), 0)
        self.assertEqual(stream.pos, 1)

        stream = BitStream(b'\x00')
        self.assertEqual(parse_total_zeros(stream, 4, 2), 2)
        self.assertEqual(stream.pos, 2)


    def test_parse_run_before(self):
        stream = BitStream(b'\x00')
        self.assertEqual(parse_run_before(stream, 1), 1)
        self.assertEqual(stream.pos, 1)

        stream = BitStream(b'\x01')
        self.assertEqual(parse_run_before(stream, 3), 3)
        self.assertEqual(stream.pos, 2)

        stream = BitStream(b'\x81')
        self.assertEqual(parse_run_before(stream, 6), 6)
        self.assertEqual(stream.pos, 3)

        stream = BitStream(b'\x00\x44')
        self.assertEqual(parse_run_before(stream, 8), 13)
        self.assertEqual(stream.pos, 10)


if __name__ == '__main__':
    unittest.main()

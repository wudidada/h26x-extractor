import unittest

from bitstring import BitStream

from h26x_extractor import nalu_utils


class NaluUtilsTest(unittest.TestCase):
    def test_more_rbsp_data(self):
        data = BitStream('0x010100')
        self.assertTrue(nalu_utils.more_rbsp_data(data))
        data.pos = 8
        self.assertTrue(nalu_utils.more_rbsp_data(data))
        self.assertEqual(data.pos, 8)

        data.pos = 16
        self.assertTrue(not nalu_utils.more_rbsp_data(data))
        self.assertEqual(data.pos, 16)

        data.pos = 15
        self.assertTrue(not nalu_utils.more_rbsp_data(data))
        self.assertEqual(data.pos, 15)

        data.pos = 14
        self.assertTrue(nalu_utils.more_rbsp_data(data))
        self.assertEqual(data.pos, 14)


if __name__ == "__main__":
    unittest.main()
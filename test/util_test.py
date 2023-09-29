import random
import unittest

from crypt import utils


def bytes_equal(a, b):
    if len(a) != len(b):
        return False

    return all(map(lambda x: x[0] == x[1], zip(a, b)))


class ParsingTest(unittest.TestCase):
    def test_nalu_encode(self):
        for d in [b"\x00\x00\x00", b"\x00\x00\x01", b"\x00\x00\x02"]:
            data = d * 100

            res = util.nalu_encode(data)
            self.assertEqual(res.find(b"\x00\x00\x00"), -1)
            self.assertEqual(res.find(b"\x00\x00\x01"), -1)
            self.assertEqual(res.find(b"\x00\x00\x02"), -1)

    def test_nalu_decode(self):
        for _ in range(100):
            data = random.randbytes(100)
            self.assertEqual(data, util.nalu_decode(util.nalu_encode(data)))

        for d in [b"\x00\x00\x00", b"\x00\x00\x01", b"\x00\x00\x02"]:
            data = d * 1000
            encode = util.nalu_encode(data)
            decode = util.nalu_decode(encode)
            self.assertEqual(data, decode)

    def test_is_same_file(self):
        self.assertTrue(util.is_same_file(__file__, __file__))
        self.assertTrue(not util.is_same_file(__file__, unittest.__file__))


if __name__ == "__main__":
    unittest.main()

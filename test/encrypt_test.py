import unittest
from pathlib import Path
from crypt import crypter, utils


class EncryptTest(unittest.TestCase):
    def test_encrypt_no_enc(self):
        def enc(data, *args):
            return data

        f = Path('../v/input/small_bunny_1080p_30fps_h264_keyframe_each_one_second.h264')
        out_f = Path('../v/output/small_bunny_1080p_30fps_h264_keyframe_each_one_second.h264')

        crypter.encrypt(f, out_f, enc)
        self.assertTrue(util.is_same_file(f, out_f))

    def test_encrypt_no_enc_encode(self):
        def encode(data, *args):
            nbsp = util.nalu_decode(data)
            reverse_nbsp = nbsp[0:1] + bytes([~b & 0xFF for b in nbsp[1:]])
            return util.nalu_encode(reverse_nbsp)

        f = Path('../v/input/small_bunny_1080p_30fps_h264_keyframe_each_one_second.h264')
        out_f = Path('../v/output/small_bunny_1080p_30fps_h264_keyframe_each_one_second.h264')
        out_f2 = Path('../v/output/small_bunny_1080p_30fps_h264_keyframe_each_one_second_2.h264')

        crypter.encrypt(f, out_f, encode)
        self.assertTrue(not util.is_same_file(f, out_f))

        crypter.encrypt(out_f, out_f2, encode)
        self.assertTrue(util.is_same_file(f, out_f2))


if __name__ == '__main__':
    unittest.main()

from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet

from crypt.crypter import encrypt, decrypt
from crypt import utils

key = Fernet.generate_key()
f = Fernet(key)

enc_time = 0
dec_time = 0

encode_time = 0
decode_time = 0
def aes_ctr_encrypt(data, fb, nri, nalu_type):
    start = datetime.now()
    encrypted_data = f.encrypt(data)

    global enc_time
    enc_time += (datetime.now() - start).total_seconds()
    start = datetime.now()
    res = utils.nalu_encode(encrypted_data)
    global encode_time
    encode_time += (datetime.now() - start).total_seconds()
    return res

def aes_ctr_decrypt(data, fb, nri, nalu_type):
    start = datetime.now()
    decoded_data = bytes(utils.nalu_decode(data))
    global decode_time
    decode_time += (datetime.now() - start).total_seconds()
    start = datetime.now()
    global dec_time
    res = f.decrypt(decoded_data)
    dec_time += (datetime.now() - start).total_seconds()
    return res


def main():
    def enc(data, *args):
        return data

    f = Path('../v/input/small_bunny_1080p_30fps_h264_keyframe_each_one_second.h264')
    enc_file = Path('../v/output/small_bunny_1080p_30fps_h264_keyframe_each_one_second_aes.h264')
    dec_file = Path('../v/output/small_bunny_1080p_30fps_h264_keyframe_each_one_second_unaes.h264')

    start = datetime.now()
    encrypt(f, enc_file, aes_ctr_encrypt)
    print(f'encrypt cost {(datetime.now() - start).total_seconds()}')
    print(f'encrypt time {enc_time}')
    print(f'encode  time {encode_time}')
    print()
    start = datetime.now()
    decrypt(enc_file, dec_file, aes_ctr_decrypt)
    print(f'decrypt cost {(datetime.now() - start).total_seconds()}')
    print(f'decrypt time {dec_time}')
    print(f'decode  time {decode_time}')


if __name__ == '__main__':
    main()

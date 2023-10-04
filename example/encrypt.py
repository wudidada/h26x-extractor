import os
from datetime import datetime
from pathlib import Path

from bitstring import BitStream
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from crypt.crypter import encrypt, decrypt
from crypt import utils

class Encryptor:
    name = 'encryptor'
    unencrypted_len = 0

    def __int__(self):
        self.encrypt_cnt = 0
        self.decrypt_cnt = 0
        self.encrypt_time = 0
        self.decrypt_time = 0
        self.encode_time = 0
        self.decode_time = 0

        self.total_size = 0
        self.encrypt_size = 0
        self.encrypted_size = 0

    def encrypt(self, data, fb, nri, nalu_type):
        self.total_size += len(data)
        if not self.should_encrypt(data, fb, nri, nalu_type):
            self.encrypted_size += len(data)
            return data

        self.encrypt_cnt += 1
        start = datetime.now()

        if len(data) <= self.unencrypted_len:
            self.encrypted_size += len(data)
            return data

        encrypted_data = bytearray(data[0:self.unencrypted_len])
        encrypted_payload = self.do_encrypt(data[self.unencrypted_len:])
        encrypted_data.extend(encrypted_payload)

        self.encrypt_size += len(data) - self.unencrypted_len

        self.encrypt_time += (datetime.now() - start).total_seconds()
        start = datetime.now()
        res = utils.nalu_encode(bytes(encrypted_data))
        self.encode_time += (datetime.now() - start).total_seconds()
        self.encrypted_size += len(res)
        return res

    def decrypt(self, data, fb, nri, nalu_type):
        if not self.should_encrypt(data, fb, nri, nalu_type):
            return data
        self.decrypt_cnt += 1

        if len(data) <= self.unencrypted_len:
            return data

        start = datetime.now()
        decoded_data = utils.nalu_decode(data)
        self.decode_time += (datetime.now() - start).total_seconds()
        start = datetime.now()

        unencrypted_data = bytearray(decoded_data[0:self.unencrypted_len])
        unencrypted_payload = self.do_decrypt(decoded_data[self.unencrypted_len:])
        unencrypted_data.extend(unencrypted_payload)
        self.decrypt_time += (datetime.now() - start).total_seconds()
        return unencrypted_data

    def do_encrypt(self, data):
        return data

    def do_decrypt(self, data):
        return data

    def should_encrypt(self, data, fb, nri, nalu_type):
        return False

    def dump_info(self):
        print(f'======== {self.name} ========')
        print(f'encrypt   count: {self.encrypt_cnt}')
        print(f'decrypt   count: {self.decrypt_cnt}')
        print(f'encrypt    time: {self.encrypt_time}')
        print(f'encode     time: {self.encode_time}')
        print(f'decrypt    time: {self.decrypt_time}')
        print(f'decode     time: {self.decode_time}')
        print(f'total      size: {self.total_size}')
        print(f'encrypt    size: {self.encrypt_size}')
        print(f'encrypt   ratio: {self.encrypt_size / self.total_size}')
        print(f'encrypted  size: {self.encrypted_size}')
        print(f'encrypted ratio: {self.encrypted_size / self.total_size}')
        print()


class AesCBCEncryptor(Encryptor):
    name = 'aes_cbc'
    unencrypted_len = 8

    key = Fernet.generate_key()
    f = Fernet(key)

    def __init__(self):
        super().__int__()

    def should_encrypt(self, data, fb, nri, nalu_type):
        b = BitStream(data)
        b.read('ue')
        slice_type = b.read('ue')
        return nalu_type in (5,)

    def do_encrypt(self, data):
        return self.f.encrypt(data)

    def do_decrypt(self, data):
        return self.f.decrypt(data)


class AesCTREncryptor(Encryptor):
    name = 'aes_ctr'
    unencrypted_len = 10

    key = os.urandom(16)
    iv = os.urandom(16)

    # use AES-CTR mode

    def __init__(self):
        super().__int__()

    def should_encrypt(self, data, fb, nri, nalu_type):
        b = BitStream(data)
        b.read('ue')
        slice_type = b.read('ue')
        return nalu_type in (1, 5)

    def do_encrypt(self, data):
        cipher = Cipher(algorithms.AES(self.key), modes.CTR(self.iv))
        encryptor = cipher.encryptor()
        return encryptor.update(data) + encryptor.finalize()

    def do_decrypt(self, data):
        cipher = Cipher(algorithms.AES(self.key), modes.CTR(self.iv))
        decryptor = cipher.decryptor()
        return decryptor.update(data) + decryptor.finalize()


class SM4CTREncryptor(Encryptor):
    name = 'sm4_ctr'
    unencrypted_len = 10

    key = os.urandom(16)
    iv = os.urandom(16)

    # use AES-CTR mode

    def __init__(self):
        super().__int__()

    def should_encrypt(self, data, fb, nri, nalu_type):
        b = BitStream(data[1:])
        first_mb_in_slice = b.read('ue')
        slice_type = b.read('ue')
        # print(first_mb_in_slice, slice_type)
        return slice_type in (2, 7, 4, 9) or slice_type in (1, 6)

    def do_encrypt(self, data):
        cipher = Cipher(algorithms.SM4(self.key), modes.CTR(self.iv))
        encryptor = cipher.encryptor()
        return encryptor.update(data) + encryptor.finalize()

    def do_decrypt(self, data):
        cipher = Cipher(algorithms.SM4(self.key), modes.CTR(self.iv))
        decryptor = cipher.decryptor()
        return decryptor.update(data) + decryptor.finalize()


def main():
    f = Path('../v/input/small_bunny_1080p_30fps_h264_keyframe_each_one_second.h264')
    enc_file = Path('../v/output/small_bunny_1080p_30fps_h264_keyframe_each_one_second_aes.h264')
    dec_file = Path('../v/output/small_bunny_1080p_30fps_h264_keyframe_each_one_second_unaes.h264')

    encryptors = [AesCBCEncryptor(), AesCTREncryptor(), SM4CTREncryptor()]
    for encryptor in encryptors:
        start = datetime.now()
        encrypt(f, enc_file, encryptor.encrypt)
        print(f'encrypt cost {(datetime.now() - start).total_seconds()}')

        start = datetime.now()
        decrypt(enc_file, dec_file, encryptor.decrypt)
        print(f'decrypt cost {(datetime.now() - start).total_seconds()}')

        encryptor.dump_info()
        assert utils.is_same_file(f, dec_file)


if __name__ == '__main__':
    main()

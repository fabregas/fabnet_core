#!/usr/bin/python
"""
Copyright (C) 2013 Konstantin Andrusenko
    See the documentation for further information on copyrights,
    or contact the author. All Rights Reserved.

@package fabnet.util.encrypt
@author Konstantin Andrusenko
@date March 1, 2013
"""
import re
from Crypto.Cipher import AES
from Crypto import Random

BLOCK_SIZE = 16
INTERRUPT = '\x0F\x01'
PAD = '\x00'
INTERRUPT_LEN = len(INTERRUPT)
EOF_PATTERN = re.compile('%s%s*$'%(INTERRUPT, PAD))

class CryptoEngine:
    RAND = Random.new()

    def __init__(self, secret=None):
        if not secret:
            secret = self._get_random(16).encode('hex')

        self.__cipher = AES.new(secret, AES.MODE_CBC, '')
        self.__secret = secret

    def get_secret(self):
        return self.__secret

    def __add_padding(self, data):
        new_data = ''.join([data, INTERRUPT])

        new_data_len = len(new_data)
        remaining_len = BLOCK_SIZE - new_data_len
        to_pad_len = remaining_len % BLOCK_SIZE
        pad_string = PAD * to_pad_len

        ret_data = ''.join([new_data, pad_string])

        return ret_data

    def __strip_padding(self, data):
        found = re.search(EOF_PATTERN, data)
        if found:
            return data[:found.start()]
        return data

    def _get_random(self, cnt):
        while True:
            data = self.RAND.read(cnt)
            if data[0] != '\x00':
                return data

    def encrypt(self, data):
        plaintext_padded = self.__add_padding(data)
        return self.__cipher.encrypt(plaintext_padded)

    def decrypt(self, data):
        d_data = self.__cipher.decrypt(data)
        ret_data = self.__strip_padding(d_data)
        return ret_data



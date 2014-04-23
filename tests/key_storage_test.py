import unittest
import time
import os
import logging
import shutil
import threading
import json
import random
import subprocess
import signal
import string
import hashlib

from fabnet.core.key_storage import *
from fabnet.core.constants import NODE_ROLE, CLIENT_ROLE

VALID_STORAGE = './tests/cert/test_keystorage.p12'
INVALID_STORAGE = './tests/cert/test_keystorage_invalid.p12'
CA_CERTS = [open('./tests/cert/root_cert.pem').read(),\
           open('./tests/cert/nodes_cert.pem').read()]

PASSWD = 'node'

class TestKeyStorage(unittest.TestCase):
    def test01_valid_storage(self):
        ks = KeyStorage(VALID_STORAGE, PASSWD)
        with self.assertRaises(InvalidPassword):
            inv_ks = KeyStorage(INVALID_STORAGE, PASSWD+'rrr')

        inv_ks = KeyStorage(INVALID_STORAGE, PASSWD)
 
        with self.assertRaises(InvalidCertificate):
            role = ks.verify_cert(ks.cert())

        KeyStorage.install_ca_certs(CA_CERTS)
        role = ks.verify_cert(ks.cert())
        self.assertEqual(role, NODE_ROLE)

        context = ks.get_ssl_context()
        self.assertNotEqual(context, None)

        self.assertEqual(ks.cert_key(), 3)

if __name__ == '__main__':
    unittest.main()


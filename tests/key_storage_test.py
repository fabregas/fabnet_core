import unittest
import time
import os
import logging
import shutil
import threading
import json
import uuid
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
 
        data = '739341ec-0b2f-4cb6-8bf8-9b3a352f55d3'
        signed = ks.sign(data)
        with self.assertRaises(InvalidCertificate):
            cn, role = ks.verify_cert(ks.cert(), signed, data)

        KeyStorage.install_ca_certs(CA_CERTS)
        cn, role = ks.verify_cert(ks.cert(), signed, data)
        cn, role = ks.verify_cert(ks.cert(), signed, unicode(data))
        cn, role = ks.verify_cert(ks.cert(), unicode(signed), data)

        with self.assertRaises(AuthError):
            cn, role = ks.verify_cert(ks.cert(), signed, '32423412421')
        self.assertEqual(role, NODE_ROLE)

        context = ks.get_ssl_context()
        self.assertNotEqual(context, None)

        self.assertEqual(ks.cert_key(), 3)

        msg = '123.123.123.123~~node@sadddd.sss~~232324235233.3'
        encrypted = ks.sym_encrypt('1234567890qwertyuiop', msg)
        decrypted = ks.sym_decrypt('1234567890qwertyuiop', encrypted)
        self.assertEqual(msg, decrypted)

        encrypted = ks.encrypt(msg)
        decrypted = ks.decrypt(encrypted)
        self.assertEqual(msg, decrypted)

    def __test02_test_perf(self):
        N = 100000
        ks = KeyStorage(VALID_STORAGE, PASSWD)
        sid = str(uuid.uuid4())
        signed = ks.sign(sid)
        t0 = datetime.now()
        for i in xrange(N):
            #signed = ks.sign(str(uuid.uuid4()))
            cn, role = ks.verify_cert(ks.cert(), signed, sid)
        print 'full validation time: %s'%(datetime.now() - t0)

        key = '1234567890qwertyuiofasdfapSd1'
        encrypted = ks.sym_encrypt(key, '123.123.123.123~~node@sadddd.sss~~232324235233.3')
        t0 = datetime.now()
        for i in xrange(N):
            ks.sym_decrypt(key, encrypted)
        print 'sym dec time: %s'%(datetime.now() - t0)

if __name__ == '__main__':
    unittest.main()


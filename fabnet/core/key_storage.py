#!/usr/bin/python
"""
Copyright (C) 2012 Konstantin Andrusenko
    See the documentation for further information on copyrights,
    or contact the author. All Rights Reserved.

@package fabnet.core.key_storage
@author Konstantin Andrusenko
@date October 28, 2012

This module contains the implementation of
a basic secure saved key storage.
"""
import os
import re
import subprocess
import hashlib
import tempfile
from datetime import datetime

from M2Crypto import RSA, X509
from M2Crypto.SSL import Context

from constants import NODE_CERTIFICATE, CLIENT_CERTIFICATE, \
                        NODE_ROLE, CLIENT_ROLE


ROLES_MAP = { NODE_CERTIFICATE: NODE_ROLE,
              CLIENT_CERTIFICATE: CLIENT_ROLE }

OPENSSL_BIN = 'openssl'

class NeedCertificate(Exception):
    pass

class ExpiredCertificate(Exception):
    pass

class InvalidCertificate(Exception):
    pass

class InvalidPassword(Exception):
    pass

def exec_openssl(command, stdin=None):
    cmd = [OPENSSL_BIN]
    cmd.extend(command)

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, \
            stdin=subprocess.PIPE)
    stdout_value, stderr_value = proc.communicate(stdin)

    out = stdout_value
    if stderr_value:
        out += '\n%s' % stderr_value
    if proc.returncode != 0:
        raise Exception('OpenSSL error: %s'%out)

    return proc.returncode, out

class TmpFile:
    def __init__(self):
        self.__fd = None
        self.__path = None
        f_descr, self.__path = tempfile.mkstemp('-nimbusfs')
        self.__fd = os.fdopen(f_descr, 'wb')

    @property
    def name(self):
        return self.__path

    def write(self, data):
        self.__fd.write(data)

    def flush(self):
        self.__fd.flush()

    def close(self):
        if self.__fd:
            self.__fd.close()
            self.__fd = None
        if self.__path:
            os.remove(self.__path)
            self.__path = None

    def __del__(self):
        self.close()



class KeyStorage:
    __CA_CERTS = {}
    @classmethod
    def install_ca_certs(cls, certs):
        for cert in certs:
            cert_o = X509.load_cert_string(cert)
            cert_name = cert_o.get_subject().OU
            cls.__CA_CERTS[cert_name] = cert_o

    @classmethod
    def autodetect_ca(cls, path):
        ca_files = []
        for item in os.listdir(path):
            if not item.endswith('.ca'):
                continue
            f_path = os.path.join(path, item)
            if not os.path.isfile(f_path):
                continue
            ca_files.append(f_path)
            cls.__read_ca_from_file(f_path)
        return ca_files

    @classmethod
    def __read_ca_from_file(cls, f_path):
        data = open(f_path).read()
        certs = re.findall('(-----BEGIN CERTIFICATE-----.+?-----END CERTIFICATE-----)', data, re.MULTILINE | re.DOTALL)
        cls.install_ca_certs(certs)

    def __init__(self, path, password):
        self.__path = path
        self.__pwd = password
        self.__private = None
        self.__cert = None

        if os.path.exists(self.__path):
            self.load()

    def create(self, private):
        self.__private = private
        tmp_pri = TmpFile()
        tmp_pri.write(private)
        tmp_pri.flush()

        retcode, _ = exec_openssl(['pkcs12', '-export', '-inkey', tmp_pri.name, \
                '-nocerts', '-out', self.__path, '-password', 'stdin'], self.__pwd)

        tmp_pri.close()

    def load(self):
        tmp_file = TmpFile()
        try:
            retcode, out = exec_openssl(['pkcs12', '-in', self.__path, '-out', \
                    tmp_file.name, '-password', 'stdin', '-nodes'], self.__pwd)
        except Exception, err:
            raise InvalidPassword('Can not open key chain! Maybe password is invalid!')
        finally:
            data = open(tmp_file.name).read()
            tmp_file.close()

        pkey_s = re.search('(-----BEGIN \w*\s*PRIVATE KEY-----(\w|\W)+-----END \w*\s*PRIVATE KEY-----)', data)
        if not pkey_s:
            raise Exception('Private key does not found in key chain!')
        self.__private = pkey_s.groups()[0]

        cert_s = re.search('(-----BEGIN \w*\s*CERTIFICATE-----(\w|\W)+-----END \w*\s*CERTIFICATE-----)', data)
        if cert_s:
            self.__cert = cert_s.groups()[0]

    def cert(self):
        return self.__cert

    def hexdigest(self):
        return hashlib.sha1(self.__private).hexdigest()

    def private(self):
        return self.__private

    def private_obj(self):
        return RSA.load_key_string(self.__private)

    def encrypt(self, data):
        key = self.private_obj()
        return key.public_encrypt(data, RSA.pkcs1_oaep_padding)

    def decrypt(self, data):
        key = self.private_obj()
        return key.private_decrypt(data, RSA.pkcs1_oaep_padding)

    def cert_obj(self):
        if not self.__cert:
            raise Exception('Key storage does not initialized')
        return X509.load_cert_string(self.__cert)

    def pubkey(self):
        pkey = self.cert_obj().get_pubkey()
        return pkey.get_rsa().as_pem()

    def append_cert(self, cert):
        if not self.__private:
            raise Exception('Private key does not specified!')

        tmp_pri = TmpFile()
        tmp_pri.write(self.__private)
        tmp_pri.flush()

        tmp_cert = TmpFile()
        tmp_cert.write(cert)
        tmp_cert.flush()

        retcode, out =  exec_openssl(['pkcs12', '-export', \
                '-inkey', tmp_pri.name, '-in', tmp_cert.name, '-out', self.__path, \
                '-password', 'stdin'], self.__pwd)

        tmp_pri.close()
        tmp_cert.close()

    def get_ssl_context(self):
        _, certfile = tempfile.mkstemp()
        _, keyfile = tempfile.mkstemp()
        try:
            open(certfile, 'w').write(self.__cert)
            open(keyfile, 'w').write(self.__private)
            context = Context()
            context.load_cert(certfile, keyfile)

            return context
        finally:
            os.unlink(certfile)
            os.unlink(keyfile)

    def cert_key(self):
        cert = self.cert_obj()
        user_key = cert.get_serial_number()
        return user_key

    def verify_cert(self, cert_str):
        '''Verify certificate and return certificate role'''
        try:
            cert = X509.load_cert_string(str(cert_str))

            cert_end_dt = cert.get_not_after().get_datetime().utctimetuple()
            if cert_end_dt < datetime.utcnow().utctimetuple():
                raise InvalidCertificate('Certificate is out of date')
        except InvalidCertificate, err:
            raise err
        except Exception, err:
            raise Exception('verify_cert error: %s'%err)

        cert_type = cert.get_subject().OU
        ca_cert = self.__CA_CERTS.get(cert_type, None)
        if ca_cert is None:
            raise InvalidCertificate('Unknown certificate type: %s'%cert_type)

        if not cert.verify(ca_cert.get_pubkey()):
            raise InvalidCertificate('Certificate verification is failed!')
        return ROLES_MAP.get(cert_type, cert_type)


def init_keystore(ks_path, passwd):
    if not os.path.exists(ks_path):
        raise Exception('Key storage does not found at %s'%ks_path)
    return KeyStorage(ks_path, passwd)

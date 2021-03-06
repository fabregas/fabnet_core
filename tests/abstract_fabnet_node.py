import unittest
import time
import os
import logging
import json
import threading
from fabnet.utils.logger import core_logger as logger
#logger.setLevel(logging.DEBUG)

from fabnet.core.constants import RC_OK, RC_ERROR
from fabnet.core.fri_base import FabnetPacketRequest, FabnetPacketResponse
from fabnet.core.fri_server import FriServer
from fabnet.core.fri_client import FriClient
from fabnet.core.workers_manager import WorkersManager
from fabnet.core.workers import ProcessBasedFriWorker, ThreadBasedFriWorker
from fabnet.core.operations_processor import OperationsProcessor
from fabnet.core.key_storage import KeyStorage, init_keystore
from fabnet.core.operations_manager import OperationsManager
from datetime import datetime
from multiprocessing import Process
from threading import Thread
from Queue import Queue

from fabnet.core.operator import Operator, OperatorProcess, OperatorClient
from fabnet.core.operation_base import OperationBase
from fabnet.core.fri_base import RamBasedBinaryData
from fabnet.core.constants import NODE_ROLE, CLIENT_ROLE, RC_PERMISSION_DENIED, RC_AUTH_ERROR


VALID_STORAGE = './tests/cert/test_keystorage.p12'
INVALID_STORAGE = './tests/cert/test_keystorage_invalid.p12'
PASSWD = 'node'
CA_CERTS = [open('./tests/cert/root_cert.pem').read(),\
           open('./tests/cert/nodes_cert.pem').read()]

class UnauthOper(OperationBase):
    NAME='unauth'

    def process(self, packet):
        return FabnetPacketResponse()

class EchoOperation(OperationBase):
    ROLES = [NODE_ROLE, CLIENT_ROLE]
    NAME = 'echo'
    def process(self, packet):
        ret = FabnetPacketResponse(ret_parameters={'message': packet.parameters['message']})
        if packet.binary_data:
            ret.binary_data = RamBasedBinaryData(packet.binary_data.data(), 900000)

        return ret

    def callback(self, ret_packet, sender):
        fobj = open('%s/callback.log'%self.home_dir, 'w')
        fobj.write('params: %s\n'%ret_packet.ret_parameters['message'])
        if ret_packet.binary_data:
            fobj.write('binary: %s\n'%ret_packet.binary_data.data())
        fobj.close()

    @classmethod
    def check_resp(cls, msg, binary=''):
        fobj = open('/tmp/callback.log')
        try:
            params = fobj.readline()
            if params.strip() != 'params: %s'%msg:
                raise Exception('%s != %s'%(params.strip(), msg))
            if binary:
                bin = fobj.readline()
                if bin.strip() != 'binary: %s'%binary:
                    raise Exception('binary size ... %s != %s'%(len(bin.strip()), len(binary)))
        finally:
            fobj.close()
        os.unlink('/tmp/callback.log')



class EchoWithCallOperation(OperationBase):
    ROLES = [NODE_ROLE, CLIENT_ROLE]
    NAME = 'echo_with_call'
    def process(self, packet):
        if packet.parameters.get('is_sync_call', False):
            resp = self._init_operation(self.self_address, 'echo', packet.parameters, sync=True, binary_data=packet.binary_data)
            return resp
        else:
            self._init_operation(self.self_address, 'echo', packet.parameters, sync=False, binary_data=packet.binary_data)
            return FabnetPacketResponse(ret_message="initiated in async mode")

    def callback(self, ret_packet, sender):
        fobj = open('%s/callback_with_call.log'%self.home_dir, 'w')
        fobj.write('params: %s\n'%ret_packet.ret_message)
        fobj.write('data: %s'%ret_packet.binary_data.data())
        fobj.close()



class TestAbstractFabnetNode(unittest.TestCase):
    def __start_node(self, node_name, ks=None):
        server_name = node_name
        cur_thread = threading.current_thread()
        cur_thread.setName('%s-main'%server_name)

        proc = OperatorProcess(Operator, '127.0.0.1:6666', '/tmp', ks, True, server_name)

        proc.start_carefully()

        try:
            oper_manager = OperationsManager([EchoOperation, EchoWithCallOperation, UnauthOper], server_name, ks)
            workers_mgr = WorkersManager(OperationsProcessor, min_count=2, max_count=8, \
                                    server_name=server_name, init_params=(oper_manager, ks))
            fri_server = FriServer('127.0.0.1', 6666, workers_mgr, server_name)
            fri_server.start()
        except Exception, err:
            time.sleep(1)
            proc.stop()
            proc.join()
            raise err

        time.sleep(1)
        return fri_server, proc

    def __defferent_calls(self, key_storage=None):
        fri_server, operator_proc = self.__start_node('testnode00', key_storage)
        try:
            fri_client = FriClient(key_storage)

            #sync call without binary
            resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='echo', \
                                        parameters={'message': 'hello, fabregas!'}))
            self.assertEqual(resp.ret_code, 0, resp.ret_message)
            self.assertEqual(resp.ret_parameters['message'], 'hello, fabregas!')

            #sync call without binary
            resp = fri_client.call('127.0.0.1:6666', FabnetPacketRequest(method='echo', \
                                        parameters={'message': 'hello, fabregas!'}))
            time.sleep(1)
            EchoOperation.check_resp('hello, fabregas!')

            #sync call with binary unchanked
            data = '0123456789'*900000
            resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='echo', \
                                        parameters={'message': 'hello, fabregas!'}, \
                                        binary_data=RamBasedBinaryData(data)))

            self.assertEqual(resp.ret_code, 0, resp.ret_message)
            self.assertEqual(resp.binary_data.data(), data)
            self.assertEqual(resp.ret_parameters['message'], 'hello, fabregas!')

            #sync call with binary chanked
            resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='echo', \
                                        parameters={'message': 'hello, fabregas!'}, \
                                        binary_data=RamBasedBinaryData(data, 900000)))

            self.assertEqual(resp.ret_code, 0, resp.ret_message)
            self.assertEqual(resp.binary_data.data(), data)
            self.assertEqual(resp.ret_parameters['message'], 'hello, fabregas!')
            session_id = fri_client.get_session_id()
            if key_storage:
                self.assertNotEqual(session_id, None)
            else:
                self.assertEqual(session_id, None)

            #async call with binary
            resp = fri_client.call('127.0.0.1:6666', FabnetPacketRequest(method='echo', \
                                        parameters={'message': 'hello, fabregas!'}, \
                                        binary_data=RamBasedBinaryData(data, 900000)))
            time.sleep(1)
            EchoOperation.check_resp('hello, fabregas!', data)
            n_session_id = fri_client.get_session_id()
            self.assertEqual(session_id, n_session_id)

            fri_client = FriClient(key_storage)
            resp = fri_client.call('127.0.0.1:6666', FabnetPacketRequest(method='echo', \
                                        parameters={'message': 'hello, fabregas!'}, \
                                        binary_data=RamBasedBinaryData(data, 900000)))
            n_session_id = fri_client.get_session_id()
            if key_storage:
                self.assertNotEqual(session_id, n_session_id)

            #unauth cal
            resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='unauth'))
            if key_storage:
                self.assertEqual(resp.ret_code, RC_PERMISSION_DENIED, resp.ret_message)
            else:
                self.assertEqual(resp.ret_code, 0, resp.ret_message)

            #EchoWithCallOperation
            #sync call without binary
            resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='echo_with_call', \
                                        parameters={'message': 'hello, fabregas!', 'is_sync_call':True},\
                                        binary_data=RamBasedBinaryData(data, 900000)))
            self.assertEqual(resp.ret_code, 0, resp.ret_message)
            self.assertEqual(resp.ret_parameters['message'], 'hello, fabregas!')
            self.assertEqual(resp.binary_data.data(), data)

            #sync call without binary (async in operation)
            resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='echo_with_call', \
                                        parameters={'message': 'hello, fabregas!', 'is_sync_call':False}))
            self.assertEqual(resp.ret_code, 0, resp.ret_message)
            time.sleep(1)
            EchoOperation.check_resp('hello, fabregas!')

            #sync call with binary (async in operation)
            resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='echo_with_call', \
                                        parameters={'message': 'hello, fabregas!', 'is_sync_call':False},\
                                        binary_data=RamBasedBinaryData(data, 900000)))
            for i in xrange(10):
                if os.path.exists('/tmp/callback.log'):
                    break
                time.sleep(1)
            time.sleep(1)
            self.assertEqual(resp.ret_code, 0, resp.ret_message)
            EchoOperation.check_resp('hello, fabregas!', data)
        finally:
            fri_server.stop()
            operator_proc.stop()
            operator_proc.join()

    def test00_without_ssl(self):
        self.__defferent_calls()

    def test01_with_ssl(self):
        KeyStorage.install_ca_certs(CA_CERTS)
        ks = init_keystore(VALID_STORAGE, PASSWD)
        self.__defferent_calls(ks)

    def test02_with_invalid_ks(self):
        KeyStorage.install_ca_certs(CA_CERTS)
        key_storage = KeyStorage(INVALID_STORAGE, PASSWD)
        fri_server, operator_proc = self.__start_node('testnode00', key_storage)
        try:
            fri_client = FriClient(key_storage)

            #sync call without binary
            resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='echo', \
                                        parameters={'message': 'hello, fabregas!'}))
            self.assertEqual(resp.ret_code, RC_AUTH_ERROR, resp.ret_message)
            self.assertTrue('Certificate verification is failed!' in resp.ret_message)
        finally:
            fri_server.stop()
            operator_proc.stop()
            operator_proc.join()

if __name__ == '__main__':
    unittest.main()


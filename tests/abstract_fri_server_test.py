import unittest
import time
import os
import logging
import json
import threading
from datetime import datetime
from multiprocessing import Process

from fabnet.core.constants import RC_OK, RC_ERROR
from fabnet.core.fri_base import FabnetPacketRequest, FabnetPacketResponse
from fabnet.core.fri_server import FriServer
from fabnet.core.fri_client import FriClient
from fabnet.core.workers_manager import WorkersManager
from fabnet.core.workers import ProcessBasedFriWorker, ThreadBasedFriWorker
from fabnet.core.key_storage import KeyStorage
from fabnet.utils.logger import logger

logger.setLevel(logging.DEBUG)

VALID_STORAGE = './tests/cert/test_keystorage.p12'
INVALID_STORAGE = './tests/cert/test_keystorage_invalid.p12'
PASSWD = 'node'

def test_packet_process(packet_processor):
    fri_request = packet_processor.recv_packet()
    #logger.info('recved packet: %s'%fri_request)

    if fri_request.method == 'HelloFabregas':
        resp = FabnetPacketResponse(ret_code=RC_OK, ret_message='Hello, dear friend!')
    else:
        resp = FabnetPacketResponse(ret_code=RC_ERROR, \
                ret_message='Unknown operation "%s"'%fri_request.method)

    packet_processor.send_packet(resp)

class MyProcessBasedFriProcessor(ProcessBasedFriWorker):
    def process(self, packet_processor):
        test_packet_process(packet_processor)

class MyThreadBasedFriProcessor(ThreadBasedFriWorker):
    def process(self, packet_processor):
        test_packet_process(packet_processor)


class TestAbstractFriServer(unittest.TestCase):
    def __start_server(self, processor_class, routine, ks=None, add_args=()):
        server_name = 'test-node'
        cur_thread = threading.current_thread()
        cur_thread.setName('%s-main'%server_name)

        workers_mgr = WorkersManager(processor_class, min_count=1, max_count=8, \
                                server_name=server_name, init_params=(ks,))
        fri_server = FriServer('127.0.0.1', 6666, workers_mgr, server_name)

        fri_server.start()

        try:
            routine()
        finally:
            fri_server.stop()

    def test00_workers_nossl(self):
        def call_methods():
            fri_client = FriClient()
            resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='HelloFabregas'))
            self.assertEqual(resp.ret_code, 0, resp.ret_message)
            self.assertEqual(resp.ret_message, 'Hello, dear friend!')

            resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='SomeMethod'))
            self.assertNotEqual(resp.ret_code, 0, resp.ret_message)
            self.assertEqual(resp.ret_message, 'Unknown operation "SomeMethod"')
            time.sleep(1)

        self.__start_server(MyThreadBasedFriProcessor, call_methods)
        self.__start_server(MyProcessBasedFriProcessor, call_methods)

    def test01_workers_ssl(self):
        ks = KeyStorage(VALID_STORAGE, PASSWD)
        def call_methods():
            fri_client = FriClient(ks)

            resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='HelloFabregas'))
            self.assertEqual(resp.ret_code, 0, resp.ret_message)
            self.assertEqual(resp.ret_message, 'Hello, dear friend!')

            resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='SomeMethod'))
            self.assertNotEqual(resp.ret_code, 0, resp.ret_message)
            self.assertEqual(resp.ret_message, 'Unknown operation "SomeMethod"')
            time.sleep(1)

        self.__start_server(MyThreadBasedFriProcessor, call_methods, ks)
        self.__start_server(MyProcessBasedFriProcessor, call_methods, ks)


    def test02_workers_nossl_spawn_stop(self):
        def stress_routine():
            def call_method():
                fri_client = FriClient()
                for i in xrange(1000):
                    resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='HelloFabregas'))
                    self.assertEqual(resp.ret_code, 0, resp.ret_message)

            processes = []
            for i in xrange(4):
                p = Process(target=call_method)
                processes.append(p)

            t0 = datetime.now()
            for p in processes:
                p.start()

            for p in processes:
                p.join()

            print 'stress time: %s'%(datetime.now()-t0)
            time.sleep(1)


        print '======== MyThreadBasedFriProcessor stress test...'
        self.__start_server(MyThreadBasedFriProcessor, stress_routine)

        print '======== MyProcessBasedFriProcessor stress test...'
        self.__start_server(MyProcessBasedFriProcessor, stress_routine)

    def test03_workers_ssl_spawn_stop(self):
        ks = KeyStorage(VALID_STORAGE, PASSWD)

        def stress_routine():
            def call_method():
                fri_client = FriClient(ks)
                for i in xrange(1000):
                    resp = fri_client.call_sync('127.0.0.1:6666', FabnetPacketRequest(method='HelloFabregas'))
                    self.assertEqual(resp.ret_code, 0, resp.ret_message)

            processes = []
            for i in xrange(4):
                p = Process(target=call_method)
                processes.append(p)

            t0 = datetime.now()
            for p in processes:
                p.start()

            for p in processes:
                p.join()

            print 'stress time: %s'%(datetime.now()-t0)
            time.sleep(1)


        print '======== MyThreadBasedFriProcessor stress test...'
        self.__start_server(MyThreadBasedFriProcessor, stress_routine, ks)

        print '======== MyProcessBasedFriProcessor stress test...'
        self.__start_server(MyProcessBasedFriProcessor, stress_routine, ks)



if __name__ == '__main__':
    unittest.main()


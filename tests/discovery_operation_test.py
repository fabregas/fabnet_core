import unittest
import time
import os
import logging
import threading
import json
import random
from datetime import datetime
from fabnet.utils.safe_json_file import SafeJsonFile
from fabnet.core import constants
constants.CHECK_NEIGHBOURS_TIMEOUT = 1
from fabnet.core.fri_server import FriServer
from fabnet.core.fri_client import FriClient
from fabnet.core.fri_base import FabnetPacketRequest, FabnetPacketResponse
from fabnet.core.node import Node
from fabnet.operations.manage_neighbours import ManageNeighbour
from fabnet.operations.discovery_operation import DiscoveryOperation
from fabnet.operations.topology_cognition import TopologyCognition
from fabnet.utils.logger import logger
from fabnet.core.constants import NT_UPPER, NT_SUPERIOR
from fabnet.core.operator import OperatorClient

#logger.setLevel(logging.DEBUG)

NODES_COUNT = 5

class TestServerThread(threading.Thread):
    def __init__(self, port, neighbour=None, create_home=True, auth_key=None):
        threading.Thread.__init__(self)
        self.port = port
        self.stopped = True
        self.node = None
        self.config = {'CHECK_NEIGHBOURS_TIMEOUT': 1}
        self.recreate_home = create_home
        self.neighbour = neighbour
        self.op_auth_key = auth_key

    def run(self):
        address = '127.0.0.1:%s'%self.port
        home_dir = '/tmp/node_%s'%self.port
        if self.recreate_home:
            if os.path.exists(home_dir):
                os.system('rm -rf %s'%home_dir)
            os.mkdir(home_dir)
        node_name = 'node%s'%self.port

        node = Node('127.0.0.1', self.port, home_dir, node_name,
                    ks_path=None, ks_passwd=None, node_type='BASE', config=self.config)
        node.set_auth_key(self.op_auth_key)

        node.start(self.neighbour)
        self.node = node

        self.stopped = False

        while not self.stopped:
            time.sleep(0.1)

        node.stop()

    def stop(self):
        self.stopped = True




class TestDiscoverytOperation(unittest.TestCase):
    def test_discovery_operation(self):
        server1 = server2 = server3 = None
        #os.system('rm /tmp/fabnet_topology.db')
        try:
            server1 = TestServerThread(1986, auth_key='123')
            server1.start()
            server2 = TestServerThread(1987, '127.0.0.1:1986', auth_key='234')
            time.sleep(1.5)
            server2.start()
            server3 = TestServerThread(1988, '127.0.0.1:1986', auth_key='432')
            time.sleep(1.5)
            server3.start()

            time.sleep(2.5)

            operator = OperatorClient('node1986', '123')
            operator1 = OperatorClient('node1987', '234')
            operator2 = OperatorClient('node1988', '432')

            self.assertEqual(sorted(operator.get_neighbours(NT_UPPER)), ['127.0.0.1:1987', '127.0.0.1:1988'])
            self.assertEqual(sorted(operator.get_neighbours(NT_SUPERIOR)), ['127.0.0.1:1987', '127.0.0.1:1988'])
            self.assertEqual(sorted(operator1.get_neighbours(NT_UPPER)), ['127.0.0.1:1986', '127.0.0.1:1988'])
            self.assertEqual(sorted(operator1.get_neighbours(NT_SUPERIOR)), ['127.0.0.1:1986', '127.0.0.1:1988'])
            self.assertEqual(sorted(operator2.get_neighbours(NT_UPPER)), ['127.0.0.1:1986', '127.0.0.1:1987'])
            self.assertEqual(sorted(operator2.get_neighbours(NT_SUPERIOR)), ['127.0.0.1:1986', '127.0.0.1:1987'])

            auth_k = operator.get_auth_key()
            auth_k1 = operator1.get_auth_key()
            auth_k2 = operator2.get_auth_key()
            self.assertEqual(auth_k, auth_k1)
            self.assertEqual(auth_k1, auth_k2)
            old_auth_key = auth_k

            packet_obj = FabnetPacketRequest(method='ChangeAuthKey')
            fri_client = FriClient()
            addr = random.choice(['127.0.0.1:1986', '127.0.0.1:1987', '127.0.0.1:1988'])
            fri_client.call(addr, packet_obj)
            time.sleep(.5)
            auth_k = operator.get_auth_key()
            auth_k1 = operator1.get_auth_key()
            auth_k2 = operator2.get_auth_key()
            self.assertEqual(auth_k, auth_k1)
            self.assertEqual(auth_k1, auth_k2)
            self.assertNotEqual(auth_k, old_auth_key)

            server1.stop()
            server1.join()
            server1 = None
            time.sleep(1.5)
            self.assertEqual(operator1.get_neighbours(NT_UPPER), ['127.0.0.1:1988'])
            self.assertEqual(operator1.get_neighbours(NT_SUPERIOR), ['127.0.0.1:1988'])
            self.assertEqual(operator2.get_neighbours(NT_UPPER), ['127.0.0.1:1987'])
            self.assertEqual(operator2.get_neighbours(NT_SUPERIOR), ['127.0.0.1:1987'])
        finally:
            try:
                if server1:
                    server1.stop()
                    server1.join()
            except Exception, err:
                print 'ERROR while stopping server1: %s'%err
            time.sleep(1)
            try:
                if server2:
                    server2.stop()
                    server2.join()
            except Exception, err:
                print 'ERROR while stopping server2: %s'%err
            time.sleep(1)
            try:
                if server3:
                    server3.stop()
                    server3.join()
            except Exception, err:
                print 'ERROR while stopping server3: %s'%err


    def __perf_op_auth(self, key):
        server1 = None
        try:
            server1 = TestServerThread(1986, auth_key=key)
            server1.start()
            time.sleep(1)

            operator = OperatorClient('node1986', key)
            N = 10000
            t0 = datetime.now()
            for i in xrange(N):
                hd = operator.get_home_dir()
            print 'process with key=%s : %s'%(key, datetime.now() - t0)
        finally:
            try:
                if server1:
                    server1.stop()
                    server1.join()
            except Exception, err:
                print 'ERROR while stopping server1: %s'%err

    def __test_op_auth_perf(self):
        self.__perf_op_auth(None)
        self.__perf_op_auth('ee7551a1ff1ea42607c4383c68fd2214f1fec125')

    def test_topology_cognition(self):
        servers = []
        addresses = []
        #os.system('rm /tmp/fabnet_topology.db')
        try:
            for i in range(1900, 1900+NODES_COUNT):
                address = '127.0.0.1:%s'%i
                if not addresses:
                    neighbour = None
                else:
                    neighbour = random.choice(addresses)

                server = TestServerThread(i, neighbour)
                server.start()
                servers.append(server)
                addresses.append(address)
                time.sleep(1.5)

            time.sleep(1)

            packet = {  'method': 'TopologyCognition',
                        'sender': None,
                        'parameters': {}}
            packet_obj = FabnetPacketRequest(**packet)
            fri_client = FriClient()
            addr = random.choice(addresses)
            fri_client.call(addr, packet_obj)

            time.sleep(1)
            operator = OperatorClient('node%s'%addr.split(':')[-1])
            home_dir = operator.get_home_dir()

            db = SafeJsonFile(os.path.join(home_dir, 'fabnet_topology.db'))
            nodes = db.read()
            print 'NODES LIST: %s'%str(nodes)

            for i in range(1900, 1900+NODES_COUNT):
                address = '127.0.0.1:%s'%i
                self.assertTrue(nodes.has_key(address))
                self.assertTrue(len(nodes[address]['uppers']) >= 2)
                self.assertTrue(len(nodes[address]['superiors']) >= 2)
                self.assertEqual(nodes[address]['node_name'], 'node%s'%i)


            print '=================== autodiscovery test ================'
            #autodiscovery
            idx = 0
            for i, server in enumerate(servers):
                if ('127.0.0.1:%s'%server.port) == addr:
                    idx = i
                    break
            server = servers[idx]
            server.stop()
            server.join()
            time.sleep(1)
            
            port = server.port
            server = TestServerThread(port, '127.0.0.1:11111', False) #host should be down
            server.start()
            servers.append(server)
            time.sleep(2)
            
            fri_client = FriClient()
            packet_obj = FabnetPacketRequest(method='NodeStatistic')
            resp = fri_client.call_sync('127.0.0.1:%s'%port, packet_obj)
            self.assertEqual(resp.ret_code, 0, resp.ret_message)
            self.assertTrue(int(resp.ret_parameters['NeighboursInfo']['uppers_balance']) >= 0, resp.ret_parameters)
            self.assertTrue(int(resp.ret_parameters['NeighboursInfo']['superiors_balance']) >= 0)

        finally:
            for server in servers:
                if server:
                    server.stop()
                    server.join()
                    time.sleep(1)


if __name__ == '__main__':
    unittest.main()


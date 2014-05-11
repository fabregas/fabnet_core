import unittest
import time
import os
import logging
import threading
import json
import random
from fabnet.core import constants
from datetime import datetime
constants.CHECK_NEIGHBOURS_TIMEOUT = 1
constants.STAT_COLLECTOR_TIMEOUT = 1
constants.STAT_OSPROC_TIMEOUT = 1
from fabnet.core.fri_base import FabnetPacketRequest, FabnetPacketResponse
from fabnet.core.node import Node
from fabnet.core.fri_client import FriClient
from fabnet.core.operator import Operator
from fabnet.utils.logger import logger
from fabnet.core.key_storage import init_keystore

logger.setLevel(logging.DEBUG)
VALID_STORAGE = './tests/cert/test_keystorage.p12'
PASSWD = 'node'

class TestNodeStatistic(unittest.TestCase):
    def test_node(self):
        try:
            server = None
            address = '127.0.0.1:1987'
            if os.path.exists('/tmp/test_node_stat'):
                os.system('rm -rf /tmp/test_node_stat')
            os.system('mkdir /tmp/test_node_stat')

            os.system('cp ./tests/cert/test_certs.ca /tmp/test_node_stat/')
            node = Node('127.0.0.1', 1987, '/tmp/test_node_stat', 'node_stat_test',
                        ks_path=VALID_STORAGE, ks_passwd=PASSWD, node_type='BASE')
            node.start(None)
            server = node
            time.sleep(1)

            packet = {  'method': 'NodeStatistic',
                        'sender': '',
                        'parameters': {'reset_op_stat': True},
                        'sync': True}
            packet_obj = FabnetPacketRequest(**packet)

            key_storage = init_keystore(VALID_STORAGE, PASSWD)
            cert = key_storage.cert()
            ckey = key_storage.cert_key()
            client = FriClient(True, cert, ckey)

            ret_packet = client.call_sync('127.0.0.1:1987', packet_obj)
            time.sleep(1.5)
            packet['parameters']['base_info'] = True
            packet_obj = FabnetPacketRequest(**packet)
            ret_packet = client.call_sync('127.0.0.1:1987', packet_obj)

            self.assertEqual(isinstance(ret_packet, FabnetPacketResponse), True)
            self.assertEqual(ret_packet.ret_code, 0, ret_packet.ret_message)
            print json.dumps(ret_packet.ret_parameters)
            self.assertEqual(ret_packet.ret_parameters['BaseInfo']['node_name'], 'node_stat_test')
            self.assertEqual(ret_packet.ret_parameters['BaseInfo']['home_dir'], '/tmp/test_node_stat')
            self.assertEqual(ret_packet.ret_parameters['BaseInfo']['node_types'], ['base'])
            self.assertEqual(int(ret_packet.ret_parameters['NeighboursInfo']['uppers_balance']), -1)
            self.assertEqual(int(ret_packet.ret_parameters['NeighboursInfo']['superiors_balance']), -1)
            self.assertTrue(float(ret_packet.ret_parameters['SystemInfo']['loadavg_5']) >= 0)
            self.assertTrue(float(ret_packet.ret_parameters['SystemInfo']['loadavg_10']) >= 0)
            self.assertTrue(float(ret_packet.ret_parameters['SystemInfo']['loadavg_15']) >= 0)
            self.assertTrue(len(ret_packet.ret_parameters['SystemInfo']['core_version'])>0)
            self.assertTrue(len(ret_packet.ret_parameters['SystemInfo']['uptime']) > 0)
            self.assertTrue(float(ret_packet.ret_parameters['FriAgentWMStat']['workers']) > 0)
            self.assertTrue(float(ret_packet.ret_parameters['FriAgentWMStat']['busy']) == 0)
            self.assertTrue(float(ret_packet.ret_parameters['OperatorWorkerWMStat']['workers']) > 0)
            self.assertTrue(float(ret_packet.ret_parameters['OperatorWorkerWMStat']['busy']) >= 1)
            self.assertTrue(float(ret_packet.ret_parameters['OperationsProcessorWMStat']['workers']) > 0)
            self.assertTrue(float(ret_packet.ret_parameters['OperationsProcessorWMStat']['busy']) == 0)
            self.assertTrue(float(ret_packet.ret_parameters['FriServerProcStat']['threads']) > 0)
            self.assertTrue(float(ret_packet.ret_parameters['FriServerProcStat']['memory']) > 1000)
            self.assertTrue(float(ret_packet.ret_parameters['OperatorProcStat']['threads']) > 0)
            self.assertTrue(float(ret_packet.ret_parameters['OperatorProcStat']['memory']) > 1000)
            self.assertTrue(float(ret_packet.ret_parameters['OperationsProcessorProcStat']['threads']) > 0)
            self.assertTrue(float(ret_packet.ret_parameters['OperationsProcessorProcStat']['memory']) > 1000)

            self.assertTrue(ret_packet.ret_parameters['OperationsProcTime']['NodeStatistic'] > 0)
            self.assertEqual(ret_packet.ret_parameters['OperationsProcTime']['TopologyCognition'], 0)

            time.sleep(.2)
        finally:
            if server:
                server.stop()


if __name__ == '__main__':
    unittest.main()


import unittest
import time
import os
import logging
import signal
import json
import random
from fabnet.core.fri_base import FabnetPacketRequest, FabnetPacketResponse
from fabnet.core.fri_client import FriClient
from fabnet.core.operator import Operator
from fabnet.utils.logger import logger
import subprocess
from fabnet.core.constants import RC_UPGRADE_ERROR

logger.setLevel(logging.DEBUG)

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

class TestUpgradeNode(unittest.TestCase):
    def test_node_upgrade(self):
        server_proc = None
        try:
            os.system('rm -rf /tmp/upgr_node && mkdir /tmp/upgr_node')
            os.system('echo "exit 0" > /tmp/upgr_node/test_installator && chmod +x /tmp/upgr_node/test_installator')
            ##os.system('rm -rf /tmp/upgrade_node.log')

            address = '127.0.0.1:1987'
            args = ['/usr/bin/python', './bin/fabnet-node', address, 'init-fabnet', 'test_upgr_node', '/tmp/upgr_node', 'BASE']
            args.append('--nodaemon')
            server_proc = subprocess.Popen(args)
            time.sleep(1)

            client = FriClient()
            params = {'config': {'INSTALLATOR_PATH': os.path.join(BASE_PATH, 'bin/pkg-install')}}
            packet_obj = FabnetPacketRequest(method='UpdateNodeConfig', parameters=params)
            ret = client.call_sync('127.0.0.1:1987', packet_obj)
            self.assertEqual(ret.ret_code, 0)

            packet_obj = FabnetPacketRequest(method='UpgradeNode', parameters={})
            ret = client.call_sync('127.0.0.1:1987', packet_obj)
            self.assertEqual(ret.ret_code, 0)

            packet_obj = FabnetPacketRequest(method='UpgradeNode', parameters={'releases': {'base': 'some_unknown_url'}})
            ret = client.call_sync('127.0.0.1:1987', packet_obj)
            self.assertEqual(ret.ret_code, RC_UPGRADE_ERROR)
            self.assertTrue(os.path.exists('/tmp/upgr_node/upgrade_node.log'))
            self.assertTrue('Invalid path' in open('/tmp/upgr_node/upgrade_node.log').read())

            params = {'config': {'INSTALLATOR_PATH': '/tmp/upgr_node/test_installator'}}
            packet_obj = FabnetPacketRequest(method='UpdateNodeConfig', parameters=params)
            ret = client.call_sync('127.0.0.1:1987', packet_obj)
            self.assertEqual(ret.ret_code, 0)

            packet_obj = FabnetPacketRequest(method='UpgradeNode', parameters={'releases': {'base': 'some_ok_url'}})
            ret = client.call_sync('127.0.0.1:1987', packet_obj)
            self.assertEqual(ret.ret_code, 0)
            self.assertTrue(os.path.exists('/tmp/upgr_node/upgrade_node.log'))
            self.assertTrue('successfully' in open('/tmp/upgr_node/upgrade_node.log').read())
        finally:
            os.system('rm -rf /tmp/upgr_node')
            if server_proc:
                server_proc.send_signal(signal.SIGINT)
                server_proc.wait()


if __name__ == '__main__':
    unittest.main()


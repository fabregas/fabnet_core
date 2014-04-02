import unittest
import time
import os
import logging
import threading
import json
import random
import shutil

from fabnet.core.fri_base import FabnetPacketRequest
from fabnet.core.fri_client import FriClient

#logger.setLevel(logging.DEBUG)

NODES = [('/tmp/node_daemon_test_01', '127.0.0.1:1984', 'test01', 'BASE'), \
        ('/tmp/node_daemon_test_02', '127.0.0.1:1985', 'test02', 'TestNode')]

DAEMON_BIN = os.path.abspath(os.path.join(os.path.dirname(__file__), '../fabnet/bin/node-daemon'))


class TestNodeDaemon(unittest.TestCase):
    def test_00_init(self):
        for node in NODES:
            if os.path.exists(node[0]):
                shutil.rmtree(node[0])
            os.mkdir(node[0])

    def test_01_node_daemon(self):
        config = '%s/fabnet.conf'%NODES[0][0]
        self.assertTrue(not os.path.exists(config))
        ret = os.system('FABNET_NODE_HOME="%s" %s init-config %s %s %s'%(NODES[0][0], \
                DAEMON_BIN, NODES[0][1], NODES[0][2], NODES[0][3]))
        self.assertEqual(ret, 0)
        self.assertTrue(os.path.exists(config))

        data = open(config).read()
        self.assertTrue("FABNET_NODE_HOST = '127.0.0.1'" in data)
        self.assertTrue("FABNET_NODE_PORT = '1984'" in data)
        self.assertTrue("NODE_NAME = 'test01'" in data)
        self.assertTrue("NODE_TYPE = 'BASE'" in data)

        ret = os.system('FABNET_NODE_HOME="%s" %s start'%(NODES[0][0], DAEMON_BIN))
        self.assertNotEqual(ret, 0)
        ret = os.system('FABNET_NODE_HOME="%s" %s start init-fabnet'%(NODES[0][0], DAEMON_BIN))
        self.assertEqual(ret, 0)
        second_started = False
        try:
            cert = ckey = None
            client = FriClient(bool(cert), cert, ckey)

            packet = FabnetPacketRequest(method='DiscoveryOperation', parameters={}, sync=True)
            resp = client.call_sync(NODES[0][1], packet)
            self.assertEqual(resp.ret_code, 0)
            self.assertEqual(resp.ret_parameters['uppers'], [])
            self.assertEqual(resp.ret_parameters['superiors'], [])
            print '\n', resp.ret_parameters, '\n'

            #start second node
            ret = os.system('FABNET_NODE_HOME="%s" %s init-config %s %s %s'%(NODES[1][0], \
                DAEMON_BIN, NODES[1][1], NODES[1][2], NODES[1][3]))
            self.assertEqual(ret, 0)

            test_operator_str = '''from fabnet.core.operator.base_operator import Operator
class TestOperator(Operator):
    OPTYPE = 'TestNode'

    def __init__(self, self_address, home_dir='/tmp/', key_storage=None, \
                    is_init_node=False, node_name='unknown-node', config={}):
        Operator.__init__(self, self_address, home_dir, key_storage, is_init_node, node_name, config)
        open('%s/test.out', 'w').write(node_name)
''' % NODES[1][0]
            plugins_conf = '''operators:
    TestNode: test_operator.TestOperator'''

            open('%s/test_operator.py'%NODES[1][0], 'w').write(test_operator_str)
            open('%s/test_plugins_conf.yaml'%NODES[1][0], 'w').write(plugins_conf)

            ret = os.system('FABNET_NODE_HOME="%s" PYTHONPATH="%s" FABNET_PLUGINS_CONF="%s/test_plugins_conf.yaml" %s start %s'\
                    %(NODES[1][0], NODES[1][0], NODES[1][0], DAEMON_BIN, NODES[0][1]))
            self.assertEqual(ret, 0)
            second_started = True

            time.sleep(1)
            
            packet = FabnetPacketRequest(method='DiscoveryOperation', parameters={}, sync=True)
            resp = client.call_sync(NODES[1][1], packet)
            self.assertEqual(resp.ret_code, 0)
            self.assertEqual(resp.ret_parameters['uppers'], [NODES[0][1]])
            self.assertEqual(resp.ret_parameters['superiors'], [NODES[0][1]])
            print '\n', resp.ret_parameters, '\n'

            packet = FabnetPacketRequest(method='DiscoveryOperation', parameters={}, sync=True)
            resp = client.call_sync(NODES[0][1], packet)
            self.assertEqual(resp.ret_code, 0)
            self.assertEqual(resp.ret_parameters['uppers'], [NODES[1][1]])
            self.assertEqual(resp.ret_parameters['superiors'], [NODES[1][1]])
            print '\n', resp.ret_parameters, '\n'

            self.assertTrue(os.path.exists('%s/test.out'%NODES[1][0]))
            self.assertTrue(NODES[1][2] in open('%s/test.out'%NODES[1][0]).read())
        finally:
            ret = os.system('FABNET_NODE_HOME="%s" %s stop'%(NODES[0][0], DAEMON_BIN))
            self.assertEqual(ret, 0)

            if second_started:
                ret = os.system('FABNET_NODE_HOME="%s" %s stop'%(NODES[1][0], DAEMON_BIN))




if __name__ == '__main__':
    unittest.main()


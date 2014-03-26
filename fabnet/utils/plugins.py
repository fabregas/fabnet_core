import os
import yaml

'''
operators:
    DHT: fabnet_dht.dht.dht_operator.DHTOperator
    MGMT: fabnet_mgmt.mgmt_operator.MgmtOperator
'''

class PluginsManager:
    def __init__(self, plugins_config):
        self.__operators = {}

        if not os.path.exists(plugins_config):
            return

        data = yaml.load(open(plugins_config).read())
        operators = data.get('operators', {})

        for node_type, obj_path in operators.items():
            parts = obj_path.split('.')
            obj = parts[-1]
            module = '.'.join(parts[:-1])

            exec('from %s import %s'%(module, obj))

            self.__operators[node_type] = eval(obj)

    def get_operators(self):
        return self.__operators

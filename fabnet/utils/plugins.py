import os
import yaml

'''example

operators:
    DHT: fabnet_dht.dht.dht_operator.DHTOperator
    MGMT: fabnet_mgmt.mgmt_operator.MgmtOperator
'''

class PluginsManager:
    __config_path = None

    @classmethod
    def __get_plugins_config_file(cls):
        if cls.__config_path:
            return cls.__config_path

        cls.__config_path = '/opt/blik/fabnet/conf/fabnet_plugins.yaml'
        if os.path.exists(os.path.join(os.path.dirname(__file__), '../../.git')): #test environment
            cls.__config_path = os.environ.get('FABNET_PLUGINS_CONF', cls.__config_path)

        return cls.__config_path

    @classmethod
    def register_operator(cls, node_type, object_path):
        plugins_config = cls.__get_plugins_config_file()
        data = yaml.load(open(plugins_config).read())

        operators = data.get('operators', {})
        operators[node_type] = object_path
        data['operators'] = operators

        r_str = yaml.dump(data, default_flow_style=False)
        open(plugins_config, 'w').write(r_str)

    @classmethod
    def get_operators(cls):
        plugins_config = cls.__get_plugins_config_file()
        if not os.path.exists(plugins_config):
            return {}

        operators = {}
        data = yaml.load(open(plugins_config).read())
        operators = data.get('operators', {})

        for node_type, obj_path in operators.items():
            parts = obj_path.split('.')
            obj = parts[-1]
            module = '.'.join(parts[:-1])

            exec('from %s import %s'%(module, obj))

            operators[node_type] = eval(obj)
        return operators

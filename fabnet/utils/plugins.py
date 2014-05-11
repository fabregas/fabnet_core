import os
import yaml

from fabnet.utils.logger import logger

'''example

operators:
    DHT: fabnet_dht.dht.dht_operator.DHTOperator
    MGMT: fabnet_mgmt.mgmt_operator.MgmtOperator
'''

class PluginsManager:
    DEFAULT_CONFIG_PATH = '/opt/blik/fabnet/conf/fabnet_plugins.yaml'
    __config_path = None
    __versions = {}

    @classmethod
    def __get_plugins_config_file(cls):
        if cls.__config_path:
            return cls.__config_path

        cls.__config_path = cls.DEFAULT_CONFIG_PATH
        if os.path.exists(os.path.join(os.path.dirname(__file__), '../../.git')): #test environment
            cls.__config_path = os.environ.get('FABNET_PLUGINS_CONF', cls.__config_path)

        return cls.__config_path

    @classmethod
    def register_operator(cls, node_type, object_path, version=None):
        plugins_config = cls.__get_plugins_config_file()
        if os.path.exists(plugins_config):
            data = yaml.load(open(plugins_config).read())
        else:
            data = {}

        operators = data.get('operators', {})
        operators[node_type] = {'object_path': object_path, 'version': version}
        data['operators'] = operators

        r_str = yaml.dump(data, default_flow_style=False)
        open(plugins_config, 'w').write(r_str)

    @classmethod
    def get_version(cls, node_type):
        if not cls.__versions:
            plugins_config = cls.__get_plugins_config_file()
            if not os.path.exists(plugins_config):
                logger.warning('Plugins configuration does not found in %s'%plugins_config)
                return {}

            operators = {}
            data = yaml.load(open(plugins_config).read())
            operators = data.get('operators', {})

            for node_type, op_info in operators.items():
                cls.__versions[node_type.lower()] = op_info.get('version', 'unknown')

        return cls.__versions.get(node_type.lower(), 'unknown')

    @classmethod
    def get_operators(cls):
        plugins_config = cls.__get_plugins_config_file()
        if not os.path.exists(plugins_config):
            logger.warning('Plugins configuration does not found in %s'%plugins_config)
            return {}

        operators = {}
        data = yaml.load(open(plugins_config).read())
        operators = data.get('operators', {})

        for node_type, op_info in operators.items():
            obj_path = op_info['object_path']
            version = op_info.get('version', 'unknown')
            cls.__versions[node_type.lower()] = version
            parts = obj_path.split('.')
            obj = parts[-1]
            module = '.'.join(parts[:-1])

            try:
                exec('from %s import %s'%(module, obj))
            except Exception, err:
                logger.error('Plugin %s loading error for node type %s. Details: %s'%(obj_path, node_type, err))
                continue

            operators[node_type.lower()] = eval(obj)
        return operators


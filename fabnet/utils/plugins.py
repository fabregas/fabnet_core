import os
import yaml

from fabnet.utils.logger import logger

'''example

operators:
    DHT: fabnet_dht.dht.dht_operator.DHTOperator
    MGMT: fabnet_mgmt.mgmt_operator.MgmtOperator
mgmt_plugins:
    DHT: {cli_plugins: path.to.object}
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
        cls.update_section('operators', {node_type: {'object_path': object_path, 'version': version}})

    @classmethod
    def get_version(cls, node_type, nocache=False):
        if not cls.__versions or nocache:
            operators = cls.get_section('operators')

            for s_node_type, op_info in operators.items():
                cls.__versions[s_node_type.lower()] = op_info.get('version', 'unknown')

        return cls.__versions.get(node_type.lower(), 'unknown')

    @classmethod
    def get_operators(cls):
        operators = cls.get_section('operators')

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
                logger.warning('Plugin %s loading error. Details: %s'%(obj_path, err))
                continue

            operators[node_type.lower()] = eval(obj)
        return operators

    @classmethod
    def get_section(cls, section):
        plugins_config = cls.__get_plugins_config_file()
        if not os.path.exists(plugins_config):
            logger.warning('Plugins configuration does not found in %s'%plugins_config)
            return {}

        operators = {}
        data = yaml.load(open(plugins_config).read())
        return data.get(section, {})

    @classmethod
    def update_section(cls, section_name, section):
        plugins_config = cls.__get_plugins_config_file()
        if os.path.exists(plugins_config):
            data = yaml.load(open(plugins_config).read())
        else:
            data = {}

        cur_section = data.get(section_name, {})
        cur_section.update(section)
        data[section_name] = cur_section

        r_str = yaml.dump(data, default_flow_style=False)
        open(plugins_config, 'w').write(r_str)


#!/usr/bin/python
"""
Copyright (C) 2012 Konstantin Andrusenko
    See the documentation for further information on copyrights,
    or contact the author. All Rights Reserved.

@package fabnet.operations.upgrade_node_operation

@author Konstantin Andrusenko
@date Novenber 5, 2012
"""
import os
from datetime import datetime

from fabnet.core.operation_base import  OperationBase
from fabnet.core.fri_base import FabnetPacketResponse
from fabnet.utils.logger import oper_logger as logger
from fabnet.utils.exec_command import run_command_ex
from fabnet.core.constants import ET_ALERT, NODE_ROLE, RC_UPGRADE_ERROR

INSTALLATOR = '/opt/blik/fabnet/bin/pkg-install'

class UpgradeNodeOperation(OperationBase):
    ROLES = [NODE_ROLE]
    NAME = 'UpgradeNode'

    def before_resend(self, packet):
        """In this method should be implemented packet transformation
        for resend it to neighbours

        @params packet - object of FabnetPacketRequest class
        @return object of FabnetPacketRequest class
                or None for disabling packet resend to neigbours
        """
        return packet

    def __upgrade_node(self, origin_urls, force=False):
        f_upgrade_log = None
        try:
            f_upgrade_log = open(os.path.join(self.home_dir, 'upgrade_node.log'), 'a')
            custom_installator = self.operator.get_config_value('INSTALLATOR_PATH')
            installator = custom_installator or INSTALLATOR

            for origin_url in origin_urls:
                f_upgrade_log.write('='*80+'\n')
                f_upgrade_log.write('UPGRADE FROM %s ... NOW = %s\n'%(origin_url, datetime.now()))
                f_upgrade_log.write('='*80+'\n')

                params = ['sudo', installator, origin_url]
                if force:
                    params.append('--force')

                ret, cout, cerr = run_command_ex(params)
                f_upgrade_log.write(cout)
                f_upgrade_log.write(cerr)
                if ret != 0:
                    raise Exception(cerr.strip())
            f_upgrade_log.write('Node is upgraded successfully!\n\n')
        finally:
            if f_upgrade_log:
                f_upgrade_log.close()


    def process(self, packet):
        """In this method should be implemented logic of processing
        reuqest packet from sender node

        @param packet - object of FabnetPacketRequest class
        @return object of FabnetPacketResponse
                or None for disabling packet response to sender
        """
        releases = packet.parameters.get('releases', {})
        optype = self.operator.get_type().lower()
        
        for n_type, urls in releases.items():
            if n_type.lower() != optype:
                continue

            if type(urls) not in (list, tuple):
                urls = [urls]

            try:
                self.__upgrade_node(urls, packet.parameters.get('force', False))
            except Exception, err:
                self._throw_event(ET_ALERT, 'UpgradeNodeOperation failed', err)
                logger.error('[UpgradeNodeOperation] %s'%err)
                return FabnetPacketResponse(ret_code=RC_UPGRADE_ERROR, ret_message=err)

            return FabnetPacketResponse()
        else:
            logger.warning('UpgradeNodeOperation: release URL does not specified for "%s" node type'%optype)


    def callback(self, packet, sender):
        """In this method should be implemented logic of processing
        response packet from requested node

        @param packet - object of FabnetPacketResponse class
        @param sender - address of sender node.
        If sender == None then current node is operation initiator

        @return object of FabnetPacketResponse
                that should be resended to current node requestor
                or None for disabling packet resending
        """
        pass

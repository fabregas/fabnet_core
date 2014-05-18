#!/usr/bin/python
"""
Copyright (C) 2014 Konstantin Andrusenko
    See the documentation for further information on copyrights,
    or contact the author. All Rights Reserved.

@package fabnet.operations.set_auth_key

@author Konstantin Andrusenko
@date May 18, 2014
"""
from fabnet.core.operation_base import  OperationBase
from fabnet.utils.logger import oper_logger as logger
from fabnet.core.constants import NODE_ROLE, RC_ERROR
from fabnet.core.config import Config

class ChangeAuthKeyOperation(OperationBase):
    ROLES = [NODE_ROLE]
    NAME = 'ChangeAuthKey'

    def before_resend(self, packet):
        """In this method should be implemented packet transformation
        for resend it to neighbours

        @params packet - object of FabnetPacketRequest class
        @return object of FabnetPacketRequest class
                or None for disabling packet resend to neigbours
        """
        auth_key = packet.parameters.get('auth_key', None)
        if auth_key:
            auth_key = str(auth_key)
            if len(auth_key) < 16:
                logger.error('SetAuthKey: too short auth_key!')
                return
        else:
            auth_key = self.operator.generate_auth_key()
            packet.parameters['auth_key'] = auth_key

        return packet

    def process(self, packet):
        """In this method should be implemented logic of processing
        reuqest packet from sender node

        @param packet - object of FabnetPacketRequest class
        @return object of FabnetPacketResponse
                or None for disabling packet response to sender
        """
        auth_key = packet.parameters['auth_key']
        self.operator.set_auth_key(auth_key)
        logger.info('ChangeAuthKey: new auth key is installed!')


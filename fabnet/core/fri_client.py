#!/usr/bin/python
"""
Copyright (C) 2012 Konstantin Andrusenko
    See the documentation for further information on copyrights,
    or contact the author. All Rights Reserved.

@package fabnet.core.fri_client
@author Konstantin Andrusenko
@date December 27, 2012

This module contains the implementation of FriClient class.
"""
import socket
import ssl
import threading

from constants import RC_ERROR, RC_AUTH_ERROR, FRI_CLIENT_TIMEOUT, FRI_CLIENT_READ_TIMEOUT

from fri_base import FabnetPacket, FabnetPacketResponse, FriException, FriAuthException
from socket_processor import SocketProcessor

class FriClient:
    """class for calling asynchronous operation over FRI protocol"""
    def __init__(self, key_storage=None):
        self.__key_storage = key_storage
        self.__session_id = None
        self.__lock = threading.Lock()

    def get_session_id(self):
        self.__lock.acquire()
        try:
            return self.__session_id
        finally:
            self.__lock.release()

    def __int_call(self, node_address, packet, conn_timeout, read_timeout=None):
        proc = None

        try:
            address = node_address.split(':')
            if len(address) != 2:
                raise FriException('Node address %s is invalid! ' \
                            'Address should be in format <hostname>:<port>'%node_address)
            hostname = address[0]
            try:
                port = int(address[1])
                if 0 > port > 65535:
                    raise ValueError()
            except ValueError:
                raise FriException('Node address %s is invalid! ' \
                            'Port should be integer in range 0...65535'%node_address)

            if not isinstance(packet, FabnetPacket):
                raise Exception('FRI request packet should be an object of FabnetPacket')

            packet.session_id = self.__session_id

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(conn_timeout)

            if self.__key_storage:
                sock = ssl.wrap_socket(sock)

            sock.connect((hostname, port))

            proc = SocketProcessor(sock, self.__key_storage)

            sock.settimeout(read_timeout)

            resp = proc.send_packet(packet, wait_response=True)

            if proc.get_session_id():
                self.__lock.acquire()
                try:
                    self.__session_id = proc.get_session_id()
                finally:
                    self.__lock.release()

            return resp
        except FriAuthException, err:
            return FabnetPacketResponse(ret_code=RC_AUTH_ERROR, ret_message='[FriClient] %s' % err)
        except Exception, err:
            return FabnetPacketResponse(ret_code=RC_ERROR, ret_message='[FriClient][%s] %s' % (err.__class__.__name__, err))
        finally:
            if proc:
                proc.close_socket()


    def call(self, node_address, packet, timeout=FRI_CLIENT_TIMEOUT):
        packet = self.__int_call(node_address, packet, timeout, FRI_CLIENT_READ_TIMEOUT)
        return packet.ret_code, packet.ret_message

    def call_sync(self, node_address, packet, timeout=FRI_CLIENT_TIMEOUT):
        packet.sync = True
        packet = self.__int_call(node_address, packet, timeout, FRI_CLIENT_READ_TIMEOUT)
        return packet

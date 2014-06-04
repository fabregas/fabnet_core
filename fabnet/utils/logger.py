#!/usr/bin/python
"""
Copyright (C) 2011 Konstantin Andrusenko
    See the documentation for further information on copyrights,
    or contact the author. All Rights Reserved.

@package fabnet.utils.logger
@author Konstantin Andrusenko
@date August 20, 2012

This module contains the fabnet logger initialization
"""
import logging, logging.handlers
import socket
import sys

class MultiprocessSysLogHandler(logging.handlers.SysLogHandler):
    def _connect_unixsocket(self, address):
        self.acquire()
        try:
            use_socktype = self.socktype
            if use_socktype is None:
                use_socktype = socket.SOCK_DGRAM
            if getattr(self, 'socket', None):
                self.socket.close()
                self.socket = None
            self.socket = socket.socket(socket.AF_UNIX, use_socktype)
            try:
                self.socket.connect(address)
                # it worked, so set self.socktype to the used type
                self.socktype = use_socktype
            except socket.error, err:
                self.socket.close()
                if self.socktype is not None:
                    # user didn't specify falling back, so fail
                    raise
                use_socktype = socket.SOCK_STREAM
                self.socket = socket.socket(socket.AF_UNIX, use_socktype)
                try:
                    self.socket.connect(address)
                    # it worked, so set self.socktype to the used type
                    self.socktype = use_socktype
                except socket.error, err:
                    self.socket.close()
                    raise
        finally:
            self.release()

def init_logger(logger_name='localhost', to_console=True):
    logger = logging.getLogger(logger_name)

    logger.setLevel(logging.INFO)

    if sys.platform == 'darwin':
        log_path = '/var/run/syslog'
    else:
        log_path = '/dev/log'

    hdlr = MultiprocessSysLogHandler(address=log_path, facility=logging.handlers.SysLogHandler.LOG_DAEMON)
    #formatter = logging.Formatter('%(filename)s: %(levelname)s: %(message)s')

    formatter = logging.Formatter('FABNET-%(name)s %(levelname)s [%(threadName)s] %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)

    if to_console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)

    return logger

logger = init_logger()
core_logger = init_logger('CORE')
oper_logger = init_logger('OPER')

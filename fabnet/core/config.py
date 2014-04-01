#!/usr/bin/python
"""
Copyright (C) 2012 Konstantin Andrusenko
    See the documentation for further information on copyrights,
    or contact the author. All Rights Reserved.

@package fabnet.core.config
@author Konstantin Andrusenko
@date November 15, 2012
"""
import os
import threading
import copy

class ConfigAttrs(type):
    __params = {}
    __lock = threading.RLock()
    __config_file = None

    @classmethod
    def update_config(cls, new_config, nosave=False):
        cls.__lock.acquire()
        try:
            cls.__params.update(new_config)

            if not nosave:
                cls.save()
        finally:
            cls.__lock.release()

    @classmethod
    def get_config_dict(cls, default=None):
        cls.__lock.acquire()
        try:
            return copy.copy(cls.__params)
        finally:
            cls.__lock.release()

    def __getattr__(cls, attr):
        return cls.get(attr)

    @classmethod
    def get(cls, attr):
        cls.__lock.acquire()
        try:
            return cls.__params.get(attr, None)
        finally:
            cls.__lock.release()

    @classmethod
    def load(cls, config_file):
        cls.__config_file = config_file
        if not os.path.exists(config_file):
            return

        try:
            gl = {}
            lc = {}
            execfile(config_file, gl, lc)
        except Exception, err:
            raise Exception('Invalid config file! %s'%err)

        cls.update_config(lc, nosave=True)

    @classmethod
    def save(cls):
        if not cls.__config_file:
            return

        cfg_str = ''
        cls.__lock.acquire()
        try:
            for key, value in cls.__params.items():
                cfg_str += "%s = '%s'\n"%(key, value)
        finally:
            cls.__lock.release()

        open(cls.__config_file, 'w').write(cfg_str)


class Config(object):
    __metaclass__ = ConfigAttrs


import os
import sys
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

if __name__ == '__main__':
    setup(
        name = "fabnet-core",
        version = read('VERSION'),
        author = "Fabregas",
        author_email = "kksstt@gmail.com",
        description = ("Fabnet network core."),
        license = "CC BY-NC",
        url = "https://github.com/fabregas/fabnet_core/wiki",
        packages= find_packages('.'),
        package_dir={'fabnet': 'fabnet'},
        scripts=['./fabnet/bin/node-daemon', './fabnet/bin/fabnet-node',
                './fabnet/bin/fri-caller', './fabnet/bin/pkg-install'],
        long_description=read('README.md'),
    )


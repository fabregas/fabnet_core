#!/usr/bin/python

import sys
import os

if len(sys.argv) != 2:
    print('Usage: %s <version>'%sys.argv[0])
    sys.exit(1)

open('VERSION', 'w').write(sys.argv[1])
open('fabnet/__init__.py', 'w').write('VERSION = "%s"\n'%sys.argv[1])
ret = os.system('git add VERSION')
ret = os.system('git add fabnet/__init__.py')
if ret:
    print('ERROR! "git add" failed!')
    sys.exit(1)

ret = os.system("git commit -m 'updated version file (%s)'"%sys.argv[1])

ret = os.system('git tag %s -a'%sys.argv[1])
if ret:
    print('ERROR! "git tag" failed!')
    sys.exit(1)


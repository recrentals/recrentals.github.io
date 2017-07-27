# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import signal
import sys
import json
import traceback

from runner_utils import escape, unescape, CodecademyLib
from runner_io import RunnerIO
from base_runner import BaseRunner

# Replace Flask object with our proxy
try:
    import proxy_flask
    del proxy_flask
except ImportError:
    # survive without flask
    pass

#################################################
## IMPORTANT
## changes out of the 'runner' directorym
## drops to an unprivileged user
##
## This is mostly a duplicate of the header in CLIRunner
## But the decision not to abstract was made in order to
## stress the importance that every runner execute this code
os.chdir(os.environ[str('RUN_DIRECTORY')])
try:
    uid = int(os.environ[str('RUN_UID')])
    gid = int(os.environ[str('RUN_GID')])
except KeyError:
    # then we don't have it, so a NOOP
    pass
else:
    os.setresgid(gid,gid,gid)
    os.setresuid(uid,uid,uid)

finally:
    if 0 in [os.getuid(), os.geteuid(), os.getgid(), os.geteuid()]:
        sys.exit(5) # do not allow process to run as root

# and now clean out the env
os.environ.pop(str('RUN_DIRECTORY'), None)
os.environ.pop(str('RUN_UID'), None)
os.environ.pop(str('RUN_GID'), None)

# END SETUP
#################################################

# make python 'requests' library know where our SSL certs are
os.environ['REQUESTS_CA_BUNDLE'] = '/etc/ssl/certs/ca-certificates.crt'


class ServerRunner(BaseRunner):

    def handle_command(self, command, code):
        if command == 'RUN':
            res = self.run_server(code)

    def run_server(self, code):
        with RunnerIO(self.codecademy_lib) as runner_io:

            try:
                compiled = self.compilecode(code)
                res = eval(compiled, {})
                runner_io.result(res)
            except Exception as e:
                try:
                    type, value, tb = sys.exc_info()
                    sys.last_type = type
                    sys.last_value = value
                    sys.last_traceback = tb
                    tblist = traceback.extract_tb(tb)
                    del tblist[:1]
                    list = traceback.format_list(tblist)
                    # Remove all errors not scpoed to codecademy file.
                    list = filter(lambda e: e.find('File "/') == -1, list)
                    # Remove runner2.py
                    list = filter(lambda e: e.find('runner2') == -1, list)
                    if list:
                        list.insert(0, "Traceback (most recent call last):\n")
                    list[len(list):] = traceback.format_exception_only(type, value)
                finally:
                    tblist = tb = None
                runner_io.stderr.write(''.join(list))

# Start it!
ServerRunner().start()

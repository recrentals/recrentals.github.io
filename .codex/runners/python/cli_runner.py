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

#################################################
## IMPORTANT
## changes out of the 'runner' directorym
## drops to an unprivileged user
##
## This is mostly a duplicate of the header in ServerRunner
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

# add custom dwolla hacks around SSL verification
os.environ['DWOLLA_VERIFY_SSL'] = 'False'
os.environ['DWOLLA_API_HOST'] = 'http://ca.dwollalabs.com/'

class CLIRunner(BaseRunner):

    TEST_HARNESS = "def ___test(code, result, CC, error):\n%s"
    TEST_EVAL = '___test(codecademy_lib.code, codecademy_lib.result, codecademy_lib, codecademy_lib.error)'

    def __init__(self, **kwargs):
        BaseRunner.__init__(self, **kwargs)

        self.test_globals = {
            'codecademy_lib' : self.codecademy_lib
        }

        # Constants that are substituted by the network proxy. Defined because
        # strings that look like constants are confusing.
        self.run_globals = {
          'ACCOUNT_SID':  'ACCOUNT_SID',
          'API_KEY':      'API_KEY',
          'AUTH_TOKEN':   'AUTH_TOKEN',
          'PIN':          'PIN'
        }

    def handle_command(self, command, code):
        if command == 'RUN':
            self.reset()
            res = self.execute(code, self.run_globals)
            self.codecademy_lib.result = res
            self.codecademy_lib.code = code
        elif command == 'TEST':
            self.test_globals.update(self.run_globals)
            self.execute(code, self.test_globals)
        elif command == 'SCT':
            self.test_globals.update(self.run_globals)
            self.sct(code, self.test_globals)

    def reset(self):
        self.codecademy_lib.result = None
        self.codecademy_lib.error = None
        self.codecademy_lib._prints = []
        self.codecademy_lib.code = ''

    def execute(self, code, globals):
        with RunnerIO(self.codecademy_lib) as runner_io:
            res = None
            try:
                compiled = self.compilecode(code)
                res = eval(compiled, globals)
                runner_io.result(res)
            except Exception as e:
                self.codecademy_lib.error = e
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

        return res

    def sct(self, test_body, globals):
        with RunnerIO(self.codecademy_lib) as runner_io:
            if test_body == '':
                test_body = 'pass'

            # Indent all lines by one because this will go in a function.
            test_body = "\n".join(["\t" + line for line in test_body.split("\n")])
            ret = {}
            try:
                compiled = self.compilecode(self.TEST_HARNESS % test_body)
                eval(compiled, globals)
                compiled = self.compilecode(self.TEST_EVAL)
                res = eval(compiled, globals)
            except Exception as e:
                ret['error'] = repr(e)
                runner_io.sct(ret)
                return

            if res == True:
                ret['pass'] = True
            else:
                ret['pass'] = False
                if isinstance(res, basestring):
                    ret['hint'] = res
                else:
                    ret['hint'] = None
            runner_io.sct(ret)

# Start it!
CLIRunner().start()

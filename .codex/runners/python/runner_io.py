"""
IO Wrappers, including Context Manager that wraps std in out err
"""
import sys
import json

from runner_utils import escape, unescape

class RunnerIO(object):

    def __init__(self, codecademy_lib):
        self.codecademy_lib = codecademy_lib

    def __enter__(self):
        self.stdout = sys.stdout
        self.runner_stdout = RunnerStdout(self, self.codecademy_lib)
        # install this to sys
        sys.stdout = self.runner_stdout

        self.stdin = sys.stdin
        self.runner_stdin = RunnerStdin(self)
        # install it in sys
        sys.stdin = self.runner_stdin

        self.stderr = sys.stderr
        # install stdout at stdin
        sys.stderr = self.runner_stdout

        return self

    def __exit__(self, *args):
        # uninstall sys
        sys.stdout = self.stdout
        sys.stdin = self.stdin
        sys.stderr = self.stderr

    def result(self, s):
        self.stdout.write('RESULT ' + repr(s))
        self.stdout.write('\r')
        self.stdout.flush()

    def request_stdin(self):
        self.stdout.write('STDIN')
        self.stdout.write('\r')
        self.stdout.flush()

    def debug(self, s):
        for line in s.split('\n'):
            self.stdout.write('DEBUG ' + line)
            self.stdout.write('\r')
            self.stdout.flush()

    def sct(self, ret):
        s = json.dumps(ret)
        self.stdout.write('SCT ' + s)
        self.stdout.write('\r')
        self.stdout.flush()


class RunnerStdout(object):

    def __init__(self, runner_io, codecademy_lib):
        self.runner_io = runner_io
        self.codecademy_lib = codecademy_lib
        self.buff = []

    def write(self, s):
        # `print` in python does two writes, one to write the string, the other for
        # `\n`. Obviously we want to avoid recording single `\n` prints from the python
        # interpreter. But what if the user `print('\n')` we want to be able to handle
        # that. To do that we maintain a buffer of all consecutive writes that is flushed
        # to `CC.prints` when we get a single `\n` while we have items in the buffer.
        if s == '\n' and len(self.buff):
            self.codecademy_lib._prints += self.buff
            self.buff = []
        else:
            self.buff.append(s)
        self.runner_io.stdout.write('OUTPUT ' + escape(s))
        self.runner_io.stdout.write('\r')
        self.runner_io.stdout.flush()

    def __getattr__(self, name):
        return self.runner_io.stdout.__getattribute__(name)


class RunnerStdin(object):

    def __init__(self, runner_io):
        self.runner_io = runner_io

    def read(self):
        self.runner_io.request_stdin()
        return  unicode(self.runner_io.stdin.read(), encoding="utf-8")

    def readline(self):
        self.runner_io.request_stdin()
        return  unicode(self.runner_io.stdin.readline(), encoding="utf-8")

    def __getattr__(self, name):
        return self.runner_io.stdin.__getattribute__(name)

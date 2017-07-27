import traceback
import sys

from runner_utils import escape, unescape, CodecademyLib

class BaseRunner(object):

    def __init__(self, **kwargs):
        self.codecademy_lib = CodecademyLib()

    # readline() normally blocks until input, but if the controlling process
    # has died, it will return an empty string '' instead.
    def readline(self):
        line = sys.stdin.readline()
        line = unicode(line, encoding="utf-8")
        if 0 == len(line):
          raise EOFError
        return line[0:-1]

    def getcode(self):
        code = ''
        while True:
            line = self.readline()
            if line == '\r':
                break
            code += '\n' + line
        return unescape(code.strip())

    def compilecode(self, code):
        if code.find('\n') > -1 or code == '':
            return compile(code, 'python', 'exec')
        else:
            try:
                return compile(code, 'python', 'eval')
            except:
                return compile(code, 'python', 'single')

    def start(self):
        res = None
        spin = True

        while spin:
            try:
                command = self.readline().strip()
                code = self.getcode()
                self.handle_command(command, code)
            except EOFError:
                spin = False

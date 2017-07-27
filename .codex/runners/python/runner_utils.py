"""
Utils shit
"""

class CodecademyLib(object):
    result = None
    error = None
    _prints = []
    command = None
    code = ''

    def printed(self, item):
        return item in self._prints

    def prints(self):
        return self._prints

def escape(s):
    return s.replace('\r', '\\r').encode('utf-8')

def unescape(s):
    return s.replace('\\r', '\r')

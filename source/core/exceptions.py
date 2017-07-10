# Exceptions collection


class CoreException(Exception):

    def __init__(self, code=500, msg='', data=None):
        self.msg = msg
        self.code = code
        self.data = data or {}

    def __str__(self):
        return u'%s : %s' % (self.code, self.msg or 'Unknown')

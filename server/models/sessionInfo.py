from server.models.phone import Phone


class SessionInfo(object):
    def __init__(self, phones=[], settings=[]):
        self.phones = phones
        self.settings = settings

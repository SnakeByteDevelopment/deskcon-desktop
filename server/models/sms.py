class Sms(object):
    def __init__(self, name, number, message, *args, **kwargs):
        self.name = name
        self.number = number
        self.message = message

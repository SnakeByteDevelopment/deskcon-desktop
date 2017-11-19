import json

class SslMessage(object):
    def __init__(self, uuid, name, type, data):
        self.uuid = uuid
        self.name = name
        self.type = type
        self.data = data

    def dump_to_json(self):
        return json.dumps(self)

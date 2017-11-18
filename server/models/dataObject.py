import json

from server.jsonHelper import json2obj
from server.models.phone import PhoneState


class DataObject(object):
    def __init__(self, uuid, devicename, type, data, *args, **kwargs):
        self.uuid = uuid
        self.device_name = devicename
        self.data_type = type
        if self.data_type == "STATS":
            self.data = PhoneState(**json.loads(data))
        else:
            self.data = data

    def to_nice_string(self):
        print "UUID", self.uuid, \
            "NAME", self.device_name, \
            "TYPE", self.data_type, \
            "MSG", self.data

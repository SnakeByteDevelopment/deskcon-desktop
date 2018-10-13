import json

from server.jsonHelper import json2obj
from server.models.phone import PhoneState


class DataObject(object):
    def __init__(self, uuid, devicename, type, data, phone=None, *args, **kwargs):
        self.uuid = uuid
        self.device_name = devicename
        self.data_type = type
        try:
            self.data = json.loads(data)
        except ValueError:
            self.data = data
        self.phone = phone

    def to_nice_string(self):
        print("UUID", self.uuid, \
            "NAME", self.device_name, \
            "TYPE", self.data_type, \
            "MSG", self.data)

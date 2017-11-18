class Phone(object):
    def __init__(self, uuid, device_name, battery, volume, battery_state, missed_sms_count, missed_call_count, ip,
                 can_message, control_port, storage, wifi_strength):
        self.uuid = uuid
        self.device_name = device_name
        self.state = PhoneState(battery, volume, battery_state, missed_sms_count, missed_call_count, ip, can_message,
                                control_port, storage, wifi_strength)


class PhoneState(object):
    def __init__(self, battery=None, volume=None, battery_state=False, missed_sms=None, missed_calls=None, ip=None,
                 can_message=False, control_port=9096, storage=None, wifi_strength=None, *args, **kwargs):
        self.wifi_strength = wifi_strength
        self.missed_calls = missed_calls
        self.battery = battery
        self.control_port = control_port
        self.missed_sms = missed_sms
        self.storage = storage
        self.volume = volume
        self.battery_state = battery_state
        self.can_message = can_message
        self.ip = ip

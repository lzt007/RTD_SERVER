import json

class ProtocolError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))



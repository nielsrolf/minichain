import json
from datetime import datetime


def datetime_converter(o):
    if isinstance(o, datetime):
        return o.strftime("%Y-%m-%dT%H:%M:%S")


def datetime_parser(dct):
    for k, v in dct.items():
        try:
            dct[k] = datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")
        except (TypeError, ValueError):
            pass
    return dct


# Usage:
# with open('data.json', 'w') as f:
#     json.dump([i.dict() for i in self.memories], f, default=datetime_converter)

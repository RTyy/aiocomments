import datetime
import decimal
import json
import uuid

from collections import OrderedDict

from core.db.models import Model

from .duration import duration_iso_string


def is_aware(value):
    return value.utcoffset() is not None


class JSONEncoder(json.JSONEncoder):
    """JSONEncoder subclass that knows how to encode date/time, decimal types and UUIDs."""

    def default(self, o):
        # See "Date Time String Format" in the ECMA-262 specification.
        if isinstance(o, datetime.datetime):
            r = o.isoformat()
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'
            return r
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, datetime.time):
            if is_aware(o):
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, datetime.timedelta):
            return duration_iso_string(o)
        elif isinstance(o, decimal.Decimal):
            return str(o)
        elif isinstance(o, uuid.UUID):
            return str(o)
        elif isinstance(o, decimal.Decimal):
            return float(o)
        elif isinstance(o, Model):
            return OrderedDict(o)
        else:
            return super().default(o)


def json_dumps(*args, **kwargs):
    return json.dumps(*args, cls=JSONEncoder, **kwargs)

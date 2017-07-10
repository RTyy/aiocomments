from aiohttp.web import json_response

from .db.models import Model
from .db.query import QueryResultIterator
from .utils.collections import ObjectDict
from .utils.json import json_dumps


def error_response(code=500, msg='', data=None):
    """Default Json response for errors and exceptions."""
    # prepare data for the error response
    response = {
        "error": msg,
        "data_errors": data or {}
    }
    response = json_response(response, dumps=json_dumps)
    response.set_status(code, msg)

    return response

async def prepare_json_response(response):
    # create json response if raw data were returned
    if isinstance(response, Model):
        response = ObjectDict(response)
    elif isinstance(response, QueryResultIterator):
        response = await response
    elif not isinstance(response, (dict, list)):
        response = {"data": str(response)}

    return response

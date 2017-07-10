import sys
import traceback

from aiohttp.web import StreamResponse, HTTPException, json_response

from .exceptions import CoreException
from .response import error_response, prepare_json_response
from .utils.json import json_dumps


async def handle_404(request, response):
    return error_response(404, 'Page Not Found')


async def handle_500(request, response):
    return error_response(500, 'Internal Server Error')


def handlers(error_handlers):
    async def middleware(app, handler):
        """Middleware prepares jsonified response."""
        async def middleware_handler(request):
            try:
                response = await handler(request)
                if not isinstance(response, StreamResponse):
                    response = await prepare_json_response(response)
                    response = json_response(response, dumps=json_dumps)

            except CoreException as e:
                response = error_response(e.code, e.msg, e.data)

            except HTTPException as e:
                override = error_handlers.get(e.status)
                if override is None:
                    raise
                else:
                    return await override(request, e)
            except Exception as e:
                print(traceback.format_exc(), file=sys.stdout)
                return error_response(500, 'Internal Server Error')

            return response

        return middleware_handler
    return middleware

json_response_middleware = handlers({404: handle_404,
                                     500: handle_500})

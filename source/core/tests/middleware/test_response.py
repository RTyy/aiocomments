import pytest
from aiohttp import web

from core.middlewares import json_response_middleware


async def json_test_handler(request):
    return {"a": 1, "b": 2}


async def string_test_handler(request):
    return 'random string'


@pytest.fixture
def cli(loop, test_client):
    app = web.Application()
    app.router.add_get('/test/json', json_test_handler)
    app.router.add_get('/test/string', string_test_handler)

    # setup jsonify middleware
    app.middlewares.append(json_response_middleware)

    return loop.run_until_complete(test_client(app))


async def test_auto_json_response(cli):
    resp = await cli.get('/test/json')
    assert resp.status == 200
    assert await resp.json() == {"a": 1, "b": 2}


async def test_string_auto_json_response(cli):
    resp = await cli.get('/test/string')
    assert resp.status == 200
    assert await resp.json() == {"data": "random string"}


# @pytest.mark.xfail
# async def test_error_json_response(cli):
#     error_data = {
#         "error": 'Page Not Found',
#         "data_errors": []
#     }
#     resp = await cli.get('/test/1')
#     assert resp.status == 404
#     assert await resp.json() == error_data

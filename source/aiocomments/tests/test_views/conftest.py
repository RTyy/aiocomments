"""Pytest Fixtures."""
import pytest
from trafaret_config.simple import read_and_validate

from core.config.trafaret import TRAFARET
from core.main import init, _initdb


@pytest.fixture
def cli(loop, test_client):
    """Default aiocomments client."""
    config = read_and_validate('./config/test.yaml', TRAFARET)
    app = init(loop, config)
    _initdb(config)
    return loop.run_until_complete(test_client(app))

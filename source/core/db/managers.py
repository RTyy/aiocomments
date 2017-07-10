"""Model Managers."""
from .query import Query


class ModelManager:
    """Default Model Manager."""

    def __init__(self, model):
        """Setup."""
        self._model = model

    def __call__(self, db):
        """Init manager with DB connection."""
        return Query(self._model, db)

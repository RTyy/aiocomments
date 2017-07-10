"""SQLAlchemy Core Wrapper in a Django Style."""
import asyncio
import sys

from collections import OrderedDict
from sqlalchemy import select, func


PY_34 = sys.version_info < (3, 5)
PY_35 = sys.version_info >= (3, 5)
PY_352 = sys.version_info >= (3, 5, 2)


class QueryResultIterator:
    """Simple Qurey Result Iterator."""

    def __init__(self, model, result_proxy):
        """Setup."""
        self._model = model
        self._result_proxy = result_proxy
        self._keys = result_proxy.keys()

    def handle_row(self, row):
        """Row handler."""
        result = OrderedDict()

        for k in self._keys:
            result[k] = row[k]

        return result

    async def fetchone(self):
        """Fetch one row from the result."""
        row = await self._result_proxy.fetchone()
        return self.handle_row(row) if row else None

    async def fetchmany(self, chunk_size=1000):
        """Fetch many rows from the result."""
        chunk = await self._result_proxy.fetchmany(chunk_size)
        if chunk:
            return [self.handle_row(row) for row in chunk]
        else:
            return None

    async def fetchall(self):
        """Fetch all rows from the result."""
        rows = await self._result_proxy.fetchall()
        return [self.handle_row(row) for row in rows]

    def __await__(self):
        """Await override. Return the result of fetchall()."""
        return self.fetchall().__await__()

    if PY_35:
        def __aiter__(self):
            """Async iterator override."""
            return self

        if not PY_352:  # pragma: no cover
            __aiter__ = asyncio.coroutine(__aiter__)


class ModelIterator(QueryResultIterator):
    """Iterator that creates models based on supplied query result."""

    def handle_row(self, row):
        """Row handler."""
        return self._model.from_db(**dict(row))

    if PY_35:
        async def __anext__(self):
            """Async interator next() override."""
            ret = await self.fetchone()
            if ret is not None:
                return ret
            else:
                raise StopAsyncIteration  # noqa


class Query:
    """Query Implementation.

    Example:

        Query(ModelNme, db).select(ModeName.id, ModelName.name)
            .filter(ModelName.id == 1)

        Creates query to load ModelName Instance with id eqaul to 1.

    """

    def __init__(self, model, db):
        """Setup."""
        self._db = db
        self._model = model
        self._where = []
        self._order_by = []
        self._select = None
        self._limit = None
        self._offset = None
        # class that will iterate query results
        self._iterator_class = ModelIterator

    def _clone(self):
        clone = Query(self._model, self._db)
        clone._where = self._where
        clone._order_by = self._order_by
        clone._select = self._select
        clone._limit = self._limit
        clone._offset = self._offset
        clone._iterator_class = self._iterator_class
        return clone

    def _build_where(self, q):
        for w in self._where:
            q = q.where(w)
        return q

    def select(self, *args):
        """Set the list of requred fields."""
        clone = self._clone()
        if len(args):
            clone._select = []
            for arg in args:
                if isinstance(arg, type(self._model)):
                    for storage in arg._meta.storages:
                        clone._select.append(storage.table)
                else:
                    clone._select.append(arg)
        else:
            clone._select = None

        return clone

    def filter(self, *args):
        """Set the query fiters based on sqlalchemy where clauses."""
        if args:
            clone = self._clone()
            clone._where += args
            return clone

        return self

    def order_by(self, *args):
        """Set the orders or clear it when called without arguments."""
        clone = self._clone()
        if args:
            clone._order_by += args
        else:
            clone._order_by = []
        return clone

    @property
    def raw(self):
        """Return clone of the query and makes it to yeild raw rows."""
        clone = self._clone()
        clone._iterator_class = QueryResultIterator
        return clone

    def _build_select_query(self):
        q = select(self._select) if self._select \
            else select([s.table for s in self._model._meta.storages])
        q = self._build_where(q)
        q = q.order_by(*self._order_by)
        if self._limit:
            q = q.limit(self._limit)
        if self._offset:
            q = q.offset(self._offset)

        return q

    async def _do_select(self):
        """Return selected iterator with row proxy or row proxy itself."""
        q = self._build_select_query()
        if self._iterator_class is None:
            return await self._db.execute(q)
        else:
            return self._iterator_class(self._model, await self._db.execute(q))

    async def get(self, *args):
        """Return first suitable record from the storage."""
        clone = self.filter(*args)
        q_result = await clone[1]
        result = await q_result.fetchone()
        if result is None:
            raise self._model.DoesNotExist()

        return result

    async def flat(self, *fields):
        """Return flat repr of the specified fields from the query result."""
        clone = self._clone()
        clone._select = fields
        clone._iterator_class = None
        result = []
        async for row in clone:
            result += row.values()
        return result

    async def count(self):
        """Count function."""
        clone = self.select(func.count(self._model.pk))
        clone._iterator_class = None
        result = await (await clone).fetchone()
        return result[0]

    async def insert(self, **values):
        """Transform query to insert supplied values."""
        result = {}
        for storage in self._model._meta.storages:
            q = storage.table.insert().returning(*storage.c).values(
                **{n: values[n] for n in storage.fields.keys()
                   if n in values and values[n] is not None})

            r = await self._db.execute(q)
            result.update(await r.fetchone())

        return result

    async def update(self, **values):
        """Transform query to update db records with supplied values."""
        result = {}
        for storage in self._model._meta.storages:
            q = self._build_where(storage.table.update().returning(*storage.c))
            q = q.values(**{n: values[n] for n in storage.fields.keys()
                            if n in values})

            r = await self._db.execute(q)
            result.update(await r.fetchone())

        return result

    async def delete(self, *args):
        """Transform query to delete db records."""
        self.filter(*args)
        storage = self._model._meta.storages[0]
        q = self._build_where(storage.table.delete())
        r = await self._db.execute(q)
        return r.rowcount

    async def __getitem__(self, key):
        """Override __getitem__ to work as limit:offset pair."""
        if isinstance(key, slice):
            offset = key.start
            # limit = key.stop - key.start
            limit = key.stop
        else:
            offset = None
            limit = int(key)

        self._offset = offset
        self._limit = limit

        return await self._do_select()

    def __await__(self):
        """Override await to execute query."""
        return self._do_select().__await__()

    if PY_35:
        def __aiter__(self):
            return self._do_select()

        if not PY_352:  # pragma: no cover
            __aiter__ = asyncio.coroutine(__aiter__)

    def __str__(self):
        """Override string representation."""
        return str(self._build_select_query())

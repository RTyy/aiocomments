import aiopg.sa
import logging
import sqlalchemy as sa

from aiohttp.web_request import Request

__all__ = ['acquire_connection']

meta = sa.MetaData()

log = logging.getLogger('database')


def migrate(config):
    conf = config['postgres']
    dsn = 'postgresql://{user}:{password}@{host}:{port}/{database}'.format(
        database=conf['database'],
        user=conf['user'],
        password=conf['password'],
        host=conf['host'],
        port=conf['port'])

    engine = sa.create_engine(dsn, echo=conf['debug'])
    with engine.connect() as conn:
        for tname, t in meta.tables.items():
            try:
                conn.execute(sa.text("DROP TABLE %s CASCADE" % tname))
                # t.drop(engine)
            except Exception:
                log.debug("Table '%s' does not exists" % tname)

    meta.create_all(engine)


async def init_pg(app):
    conf = app['config']['postgres']
    engine = await aiopg.sa.create_engine(
        database=conf['database'],
        user=conf['user'],
        password=conf['password'],
        host=conf['host'],
        port=conf['port'],
        minsize=conf['minsize'],
        maxsize=conf['maxsize'],
        loop=app.loop)
    app['db'] = engine


async def close_pg(app):
    app['db'].close()
    await app['db'].wait_closed()


def acquire_connection(f):
    async def wrapper(view, *args, **kwargs):
        _request = view if isinstance(view, Request) else view.request
        async with _request.app['db'].acquire() as conn:
            return await f(view, conn, *args, **kwargs)
    return wrapper

"""Main Module."""
import argparse
import asyncio
import importlib
import logging
import os
import sys

import jinja2
import aiohttp_jinja2

from aiohttp import web
from trafaret_config import commandline
from pathlib import Path

from core.db import close_pg, init_pg, migrate as db_migrate
from core.fs import FileStorage
# from core.pubsub import init_redis_pub, init_redis_sub, \
#   close_redis_pub, close_redis_sub
from core.utils import import_string, query_yes_no
from core.utils.supervisor import Supervisor
from core.config.trafaret import TRAFARET


from aiocomments.lib.xml_reporter import CommentsXMLReporter


PROJECT_PATH = Path(__file__).parent.parent.absolute()
PROJECT_ROOT = str(PROJECT_PATH)


class BackgroundTasks:

    async def startup(self, app):
        # setup database
        await init_pg(app)
        # setup XML Comments Download Tasks Handler
        self.c_xml_reporter = CommentsXMLReporter(app, 3, loop=app.loop)
        # app.loop.create_task(self.c_xml_reporter.run())

    async def cleanup(self, app):
        # stop XML Download Handler
        await self.c_xml_reporter.stop()
        # close database
        await close_pg(app)


def init(loop, config):
    # setup application and extensions
    app = web.Application(loop=loop)

    # load config from yaml file in current dir
    app['config'] = config

    # setup Jinja2 template renderer
    aiohttp_jinja2.setup(
        app, loader=jinja2.PackageLoader('aiocomments', 'templates'))

    bg_tasks = BackgroundTasks()
    app.on_startup.append(bg_tasks.startup)
    app.on_cleanup.append(bg_tasks.cleanup)

    for ap in config['apps']:
        # setup router
        # load routes for the application from app_name.routes
        routes_file = Path(os.path.join(PROJECT_ROOT, ap, "routes.py"))
        if routes_file.is_file():
            url_import = ".".join([ap, "routes"])
            m = importlib.import_module(url_import)
            # setup views and routes
            for route in m.ROUTES:
                app.router.add_route(*route)
        else:
            logging.warning("Couldn't parse routes for applicaton: %s", ap)

    # setup middlewares
    for url_import in config['middlewares']:
        try:
            middleware = import_string(url_import)
            app.middlewares.append(middleware)
        except ImportError as e:
            logging.warning("Couldn't setup middleware: %s", url_import)
            raise e

    # setup simple file storage
    if config['filestorage']:
        storage_path = config['filestorage']['root']
        app['fs'] = FileStorage(storage_path)

    return app


def initdb(options):
    print("=" * 8, "Run Database Initialization", "=" * 8)
    if options.silent or query_yes_no(
        "All the currently stored data will be destroyed." +
            "Do you want to proceed?", 'no'):
        config = commandline.config_from_options(options, TRAFARET)
        _initdb(config)
        print("DB Init Complete!")
    sys.exit(0)


def _initdb(config):
    """Run migration process."""
    # load user defined apps
    for ap in config['apps']:
        # setup router
        routes_file = Path(os.path.join(PROJECT_ROOT, ap, "routes.py"))
        if routes_file.is_file():
            # load routes for the application from app_name.routes
            url_import = ".".join([ap, "routes"])
            importlib.import_module(url_import)
        else:
            logging.warning("Couldn't parse routes for applicaton: %s", ap)

    db_migrate(config)


def serve(options):
    """Run development server."""
    logger = logging.getLogger('supervisor')
    logger.debug("Development Mode: ON")

    sargv = sys.argv.copy()
    sargv.remove('serve')
    args = [sys.executable] + ['-W%s' % o for o in sys.warnoptions] + sargv

    Supervisor(args, options).start()


def server(options):
    """Run standalone server."""
    # read config
    config = commandline.config_from_options(options, TRAFARET)

    # init asyncio loop
    loop = asyncio.get_event_loop()

    # init application
    app = init(loop, config)
    # app.on_startup.append(start_background_tasks)
    # app.on_cleanup.append(cleanup_background_tasks)

    # run application server
    web.run_app(app,
                host=app['config']['host'],
                port=app['config']['port'],
                loop=loop)

    # close loop (aiohttp didn't close it cuz we provided custom loop)
    loop.close()


def main(argv):
    # init logging
    logging.basicConfig(level=logging.DEBUG)

    ap = argparse.ArgumentParser()
    commandline.standard_argparse_options(ap,
                                          default_config='./config/main.yaml')
    #
    # define your command-line arguments here
    #
    subparsers = ap.add_subparsers(title='modes',
                                   description='available modes',
                                   help='additional help')
    # ap_migrate = subparsers.add_parser(
    #    'migrate', help='Migrate (Temporary Reinstall Database)')
    # ap_migrate.set_defaults(mode=migrate)
    ap_migrate = subparsers.add_parser(
        'initdb', help='Init DB by droping and creating all the tables')
    ap_migrate.set_defaults(mode=initdb)
    ap_migrate.add_argument("-s", "--silent", action="store_true",
                            dest="silent", help="run in silent mode")
    ap_serve = subparsers.add_parser(
        'serve', help='Development Mode (Reload on module update)')
    ap_serve.set_defaults(mode=serve)

    options = ap.parse_args(argv)

    mode = getattr(options, 'mode', server)
    mode(options)


if __name__ == '__main__':
    main(sys.argv[1:])

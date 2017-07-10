import importlib
import logging
import os
import signal
import subprocess
import sys
import time

from trafaret_config import commandline

from ..config.trafaret import TRAFARET


IS_WIN = (sys.platform == "win32")
logger = logging.getLogger('supervisor')


class Supervisor:
    def __init__(self, args, options):
        self._mtimes = {}
        self._error_files = []
        self._warm_start = False

        self.args = args
        self.options = options
        self.environ = os.environ.copy()
        # self.config_filename = os.path.abspath(os.path.join(os.environ['PROJECT_ROOT'] + self.options.config))
        self.config_filename = os.path.abspath(self.options.config)
        self.user_modules = {}

    def start(self):
        if not self._warm_start:
            # load config file
            config = commandline.config_from_options(self.options, TRAFARET)
            # import user defined modules
            observe_modules = ['.'.join([app, 'routes']) for app in config['apps']] + \
                              [m.rsplit('.', 1)[0] for m in config['middlewares']]

            for module_path in observe_modules:
                if module_path in self.user_modules:
                    importlib.reload(self.user_modules[module_path])
                else:
                    self.user_modules[module_path] = importlib.import_module(module_path)

        # run application in a subprocess
        self.p = subprocess.Popen(self.args, env=self.environ)
        try:
            while True:
                cfilename, cmodule = self.code_changed()
                if cfilename:
                    # send a keyboardinterrupt signal to subprocess
                    # this will stop aiohttp in it.
                    self.stop()
                    # do warm start if config file wasn't chnaged
                    self._warm_start = not cfilename == self.config_filename
                    # reload changed module
                    if cmodule:
                        # try to reload changed module and just skip any excptions
                        # (they will be caught in the subprocess)
                        try:
                            importlib.reload(cmodule)
                        except Exception:
                            pass

                    # strart process again
                    logger.debug('Restart Development Server...')
                    self.start()
                    break
                # recheck timer
                time.sleep(2)
        except KeyboardInterrupt:
            # stop aiohttp in the subprocess
            self.stop()
            sys.exit(0)

    def stop(self):
        # stop aiohttp in the subprocess
        self.p.send_signal(signal.SIGINT)
        # wait for subprocess terminaiton
        self.p.wait()

    def code_changed(self):
        files = {self.config_filename: None}

        for m in sys.modules.values():
            try:
                files[m.__file__] = m
            except AttributeError:
                pass

        for filename in list(files.keys()) + self._error_files:
            if not filename:
                continue

            if filename.endswith(".pyc") or filename.endswith(".pyo"):
                filename = filename[:-1]

            if filename.endswith("$py.class"):
                filename = filename[:-9] + ".py"

            if not os.path.exists(filename):
                # File might be in an egg, so it can't be reloaded.
                continue

            stat = os.stat(filename)
            mtime = stat.st_mtime

            if IS_WIN:
                mtime -= stat.st_ctime

            if filename not in self._mtimes:
                self._mtimes[filename] = mtime
                continue

            if mtime != self._mtimes[filename]:
                self._mtimes.clear()

                try:
                    del self._error_files[self._error_files.index(filename)]
                except ValueError:
                    pass

                return filename, files.get(filename, None)

        return False, None

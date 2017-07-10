import os
import uuid


class FileStorage:
    """Simple file storage handler."""

    def __init__(self, root):
        self.root = root
        # create storage dirs
        if not os.path.isdir(self.root):
            os.makedirs(self.root)

    def generate_filename(self, ext=None):
        """Return a brand new filename for a new file created within storage."""
        while True:
            fname = str(uuid.uuid4())
            if ext:
                fname = '%s.%s' % (fname, ext)
            fpath = self.path(fname)
            if not os.path.isfile(fpath):
                open(fpath, 'w+')
                break

        return fname

    def path(self, fname):
        """Retrun absoulute path to the file in storage."""
        return os.path.join(self.root, fname)

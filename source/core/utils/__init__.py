import importlib
import sys


def import_string(path):
    try:
        module_path, var_name = path.rsplit('.', 1)
    except ValueError as e:
        raise e

    try:
        m = importlib.import_module(module_path)
    except ImportError as e:
        raise e

    try:
        return getattr(m, var_name)
    except AttributeError as e:
        msg = u"Module %s doesn't define variable '%s'" % (module_path, var_name)
        raise Exception(msg)


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def dict_to_uri_query(d):
    return "&".join(['%s=%s' % (k, v) for k, v in d.items()])

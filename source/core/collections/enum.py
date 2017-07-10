"""Swift 3 Style Enum Implementation."""
from collections import OrderedDict


class EnumCaseMixin:
    """Enum Case Mixin."""

    def __get_pair(self):
        return (self, self.verbose)
    pair = property(__get_pair)


class EnumCase:
    """Case generator.

    Generates case classes based on case value types and returns
    case instance of the generated class.
    """

    enum_case_classes = {}

    def __new__(cls, value, verbose=None):
        """Create a case instance based on supplied attributes."""
        t = type(value)
        enum_case_class = cls.enum_case_classes.setdefault(
            t.__name__,
            type('%sEnumCase' % t.__name__, (EnumCaseMixin, t), {})
        )

        enum_case = enum_case_class(value)
        enum_case.verbose = verbose or value

        return enum_case


class EnumMeta(type):
    """Meta."""

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        """Make namepace ordered."""
        return OrderedDict()

    def __new__(cls, name, bases, nmspc):
        """Override class creation process."""
        cases = OrderedDict()
        backrefs = dict()
        for case_name, case in nmspc.items():
            if case_name.isupper():
                if isinstance(case, EnumCaseMixin):
                    cases[case_name] = case

                elif isinstance(case, tuple) and len(case) == 2:
                    nmspc[case_name] = EnumCase(*case)
                    cases[case_name] = nmspc[case_name]
                    backrefs[case[0]] = nmspc[case_name]

        class_ = super().__new__(cls, name, bases, nmspc)
        class_.__cases = cases
        class_.__backrefs = backrefs
        return class_

    def get_pairs(self):
        """Return Enum as tuple of defined EnumCase tuples."""
        return tuple(case.pair for case in self.__cases.values())
    pairs = property(get_pairs)

    def by_verbose(self, verbose, default=None):
        """Search and return a case by it's verbose."""
        for val, verb in self:
            if verb == verbose:
                return val

        return default

    def __contains__(self, case_name):
        """Override contains."""
        return case_name in self.__cases

    def __iter__(self):
        """Override Iteator."""
        for case in self.__cases.values():
            yield case.pair

    def __getitem__(self, key):
        """Override slicing."""
        return self.__backrefs.get(key, None)

    # def __call__(self, *args, **kwargs):
    #     if args:
    #         if len(args) > 1:
    #             return tuple(self.__choices.get(arg, None)
    #                          for arg in args if arg in self.__choices)
    #         return self.__choices.get(args[0], None)
    #     return super().__call__(args, kwargs)


class Enum(metaclass=EnumMeta):
    """Base Enum Class."""

    pass
    # def __init__(self, *args, **kwargs):
    #     pass

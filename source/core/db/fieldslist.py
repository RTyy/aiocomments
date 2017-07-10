"""Field List Helper."""
LOOKUP_SEP = '__'


class ListWrapper(list):
    def __init__(self, *args):
        self.extend(args)


class DictWrapper(dict):
    def __init__(self, *args, **kwargs):
        self.update(zip(args, args))
        self.update(kwargs)


class ListDictWrapper(dict):
    def __init__(self, *args, **kwargs):
        for arg in args:
            self[arg] = ()
        self.update(kwargs)


exclude = type('Exclude', (ListWrapper,), {})
custom = type('Custom', (DictWrapper,), {})
related = type('Related', (ListDictWrapper,), {})


class FieldsList(list):

    def __init__(self, *args):
        self._all = True
        self.exclude = set()
        self.custom = dict()
        self.related = dict()
        self.append(*args)

    def __contains__(self, field):
        return field not in self.exclude and (self._all or super().__contains__(field))

    def append(self, *args):
        for el in args:
            if el is None:
                self._all = False

            elif isinstance(el, str):
                super().append(el)
                self._all = False

            elif isinstance(el, exclude):
                self.exclude = self.exclude.union(set(el))

            elif isinstance(el, custom):
                for alias, field in el.items():
                    self.custom[alias] = field.split(LOOKUP_SEP)

            elif isinstance(el, related):
                for r_field, fields in el.items():
                    r_path = r_field.split(LOOKUP_SEP)

                    related_list = self

                    for r in r_path[:-1]:
                        related_list = related_list.related.setdefault(r, FieldsList(None))

                    related_list.related.setdefault(r_path[-1], FieldsList()).append(*fields)

        return self

"""Storage Implementation based on SQLAlchemy Table."""

import sqlalchemy as sa

from core.db import meta


class Storage(object):
    """Storage Class."""

    def __init__(self, name, fields, constraints={}):
        """Setup storage with name, fields and possible constratints."""
        defined_fields = [f.define() for f in fields.values()]
        self.__table = sa.Table(name, meta, *defined_fields)

        for c in constraints.get('unique', ()):
            self.__table.append_constraint(sa.UniqueConstraint(*c))

        for c in constraints.get('index', ()):
            self.__table.append_constraint(sa.Index(*c))

        self.__fields = fields

    @property
    def c(self):
        """Table C."""
        return self.__table.c

    @property
    def table(self):
        """Table."""
        return self.__table

    @property
    def fields(self):
        """Defined fields."""
        return self.__fields

    @property
    def is_primary(self):
        """If storage has a primary key."""
        return True if self.__table.primary_key else False

    @property
    def primary_key(self):
        """Return Storage primary key."""
        return self.__table.primary_key

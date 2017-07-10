import sqlalchemy as sa

from sqlalchemy import CheckConstraint, func

__all__ = [
    'func',
    'CheckConstraint',
    'String',
    'Integer',
    'Text',
    'DateTime',
    'Float',
]


class Field:
    """Proxy class for sqlalchemy Column builder."""

    def __init__(self, *args, **kwargs):
        self.name = None
        self.args = args
        self.kwargs = kwargs
        self.default = kwargs.get('default', None)
        self.type = sa.Integer
        self.type_args = []
        self.type_kwargs = {}

    def define(self):
        t = self.type if not self.type_args and not self.type_kwargs else self.type(*self.type_args, **self.type_kwargs)
        return sa.Column(self.name, t, *self.args, **self.kwargs)


class String(Field):
    def __init__(self, *args, max_length=255, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = sa.String
        self.type_args = [max_length]


class Integer(Field):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Float(Field):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = sa.Float


class Serial(Integer):
    def __init__(self, *args, **kwargs):
        kwargs['primary_key'] = True
        kwargs['nullable'] = False
        super().__init__(*args, **kwargs)


class Text(Field):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = sa.Text


class DateTime(Field):
    def __init__(self, *args, with_timezone=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = sa.DateTime
        self.type_kwargs = {'timezone': with_timezone}


class Boolean(Field):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = sa.Boolean


class ForeignKey(Field):
    def __init__(self, fk_column, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = sa.ForeignKey
        self.type_args = [fk_column]

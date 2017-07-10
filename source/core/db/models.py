"""Base Model Implemenation."""

from collections import OrderedDict

from .exceptions import ObjectDoesNotExist
from .fields import Field, Serial
from .fieldslist import FieldsList, exclude
from .managers import ModelManager
from .storage import Storage
from ..utils.comboprops import comboproperty


class ModelMeta:
    """Model Descriptor Class."""

    def __init__(self, model):
        """Setup Descriptor."""
        self.model = model
        self.name = model.__name__
        self.storagename = self.name.lower()
        self.pk = 'id'
        self.storages = []
        self.fields = OrderedDict()
        self.constraints = {
            'unique': (),
            'index': (),
        }
        # instance db state: 0 - unsaved; 1 - saved;
        self.db_state = 0


class ModelMetaBase(type):
    """Model Meta Class."""

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        """Make a namespace dict Orderd."""
        return OrderedDict()

    def __new__(cls, name, bases, nmspc, **kwargs):
        """Override model class creation."""
        parents = [b for b in bases if isinstance(b, ModelMetaBase)]
        if not parents:
            return type.__new__(cls, name, bases, nmspc)

        module = nmspc.pop('__module__')
        model = type.__new__(cls, name, bases, {'__module__': module})

        _meta = nmspc.pop('Meta', None)

        meta = ModelMeta(model)
        meta.storagename = getattr(_meta, 'storagename', meta.storagename)
        meta.constraints['unique'] = getattr(_meta, 'unique', ())
        meta.constraints['index'] = getattr(_meta, 'index', ())

        # set serial field
        meta.fields[meta.pk] = Serial()
        meta.fields[meta.pk].name = meta.pk
        # parse declared fields
        for n, attr in nmspc.items():
            # handle declared fields
            if isinstance(attr, Field):
                attr.name = n
                meta.fields[n] = attr

            # set the rest declared attributes as is
            else:
                setattr(model, n, attr)

        # define model storage
        storage = Storage(meta.storagename, meta.fields, meta.constraints)
        meta.storages.append(storage)

        # set model fields as pointers to storage fields (columns)
        for n, f in meta.fields.items():
            setattr(model, n, storage.c[n])

        model._meta = meta
        model.list = ModelManager(model)
        model.DoesNotExist = type('DoesNotExist',
                                  (ObjectDoesNotExist,),
                                  {'__module__': module})

        return model

    def __repr__(self):
        """Override representation."""
        return u'<Model: %s>' % self.__name__


class Model(metaclass=ModelMetaBase):
    """Base Model."""

    def __init__(self, **kwargs):
        """Fill the model fields with supplied data."""
        self.__fill(**kwargs)

    # @property
    # def pk(self):
    #     return getattr(self, self._meta.pk)

    @comboproperty
    def pk(self):
        """Primary key wrapper."""
        return getattr(self, self._meta.pk)

    @pk.classproperty
    def pk(self):
        """Primary key wrapper."""
        return getattr(self, self._meta.pk)

    @classmethod
    def from_db(cls, **kwargs):
        """Init model with data loaded from the db."""
        instance = cls(**kwargs)
        instance._meta.db_state = 1
        return instance

    def __fill(self, **kwargs):
        for n, v in self._meta.fields.items():
            val = kwargs.pop(n, v.default)
            if hasattr(val, '__call__'):
                val = val()

            setattr(self, n, val)

        # set the rest object attributes
        for n, v in kwargs.items():
            setattr(self, n, v)

    async def to_dict(self, *fields, **options):
        """Prepare python dict representation of the model instance.

        Usage:
            to_dict(field_name1, field_name2,
                    exclude(field_name3),
                    custom(custom_field_name=method_or_property_name)
                    )

            means that we want to build a dict with a field field_name1,
            field_name2 and custom_field_name excluding field_name3.
            wherein custom_file_name will actully point to another field or
            method of the model.

        """
        fl = options.pop('fieldslist', FieldsList()).append(*fields)
        result = {fld: value for fld, value in self if fld in fl}
        # handle custom fields
        for alias, fpath in fl.custom:
            obj = self
            for fld in fpath:
                obj = getattr(obj, fld, None)

            value = obj() if hasattr(obj, '__call__') else obj
            # if not is_protected_type(value):
            #     if hasattr(value, 'to_dict'):
            #         value = value.to_dict(**self._options)
            #     else:
            #         value = str(value)
            result[fld] = value

        # handle related fields
        for fld, sfl in fl.related.items():
            result[fld] = getattr(self, fld).to_dict(fields_list=sfl)

        return result

    async def save(self, db):
        """Save model instance to the database."""
        if self.pk and self._meta.db_state == 1:
            # update previosly saved object record
            data = await self.to_dict(exclude(type(self)._meta.pk))
            r = await self.list(db).filter(
                type(self).pk == self.pk).update(**data)
        else:
            # insert new object record
            r = await self.list(db).insert(**dict(self))
            self._meta.db_state = 1

        self.__fill(**r)

    async def delete(self, db):
        """Delete model instance from the database."""
        if self.pk and self._meta.db_state == 1:
            await self.list(db).delete(type(self).pk == self.pk)
            # reset instance primary key to None
            setattr(self, type(self)._meta.pk, None)

    def __iter__(self):
        """Override model iterator.

        It should yield model field name and it's value as a tupel.
        """
        for n in self._meta.fields.keys():
            yield (n, getattr(self, n, None))

    def __repr__(self):
        """Represenation."""
        return u'<%s : %s>' % (self._meta.name, self.pk)

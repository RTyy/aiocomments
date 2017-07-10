# Core decorators


__all__ = ['combomethod', 'comboproperty']


class ComboMethodDecriptor:
    def __init__(self, object_method, class_method=None, class_property=None, object_property=None):
        self.object_method = object_method
        self.object_property = object_property if not object_method else None
        self.class_method = class_method
        self.class_property = class_property if not class_method else None

    def __get__(self, obj, cls=None):
        cls = cls or type(obj)
        if obj:
            if self.object_method:
                return self.object_method.__get__(obj, cls)

            elif self.object_property:
                return self.object_property(obj)

        else:
            if self.class_method:
                def class_method(*args, **kwargs):
                    return self.class_method(cls, *args, **kwargs)
                return class_method

            elif self.class_property:
                return self.class_property(cls)

    def __set__(self, obj, value):
        raise AttributeError("Can't reset Combo Method")

    def classmethod(self, class_method):
        if self.class_property is not None:
            raise AttributeError("Class property for combomethod was setted already.")
        self.class_method = class_method
        return self

    def classproperty(self, class_property):
        if self.class_method is not None:
            raise AttributeError("Class method for combomethod was setted already.")
        self.class_property = class_property
        return self


def combomethod(method):
    return ComboMethodDecriptor(method)


class ComboPropertyDescriptor(ComboMethodDecriptor):

    def __init__(self, object_property, class_method=None, class_property=None):
        super().__init__(None, class_method, class_property, object_property)

    def __set__(self, obj, value):
        raise AttributeError("Can't reset Combo Property")


def comboproperty(method):
    return ComboPropertyDescriptor(method)

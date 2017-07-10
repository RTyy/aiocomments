from core.utils.comboprops import combomethod, comboproperty


def test_combomethod():

    class TestClass:
        @combomethod
        def test_method(self, obj_test_var):
            return obj_test_var

        @test_method.classmethod
        def test_method(self, cls_test_var):
            return cls_test_var

    c = TestClass()

    assert c.test_method(42) == 42
    assert TestClass.test_method(4242) == 4242


def test_combomethod_classproperty():

    class TestClass:
        @combomethod
        def test_method(self, obj_test_var):
            return obj_test_var

        @test_method.classproperty
        def test_method(self):
            return (self, 4242)

    c = TestClass()

    assert c.test_method(42) == 42
    assert TestClass.test_method == (TestClass, 4242)


def test_comboproperty():

    class TestClass:
        @comboproperty
        def test_property(self):
            return (self, 42)

        @test_property.classproperty
        def test_property(self):
            return (self, 4242)

    c = TestClass()

    assert c.test_property == (c, 42)
    assert TestClass.test_property == (TestClass, 4242)


def test_comboproperty_classmethod():

    class TestClass:
        @comboproperty
        def test_property(self):
            return (self, 42)

        @test_property.classmethod
        def test_property(self, x):
            return (self, x)

    c = TestClass()

    assert c.test_property == (c, 42)
    assert TestClass.test_property(424242) == (TestClass, 424242)

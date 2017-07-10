
from core.collections import Enum
from core.collections.enum import EnumCase


def test_int_enum_case_generator():
    case = EnumCase(1)

    assert isinstance(case, int)
    assert case == 1
    assert not case == '1'


def test_string_enum_case_generator():
    case = EnumCase('test_value')

    assert isinstance(case, str)
    assert case == 'test_value'


def test_enum_case_verbose():
    case = EnumCase(1)
    assert case.verbose == 1

    case = EnumCase(1, 'One')
    assert case.verbose == 'One'


def test_enum_case_pair():
    case = EnumCase(1, 'One')
    assert case.pair == (1, 'One')


def test_int_based_enum():
    class TestIntEnum(Enum):
        ONE = 1, 'One'
        TWO = 2, 'Two'
        THREE = 3, 'Three'

    assert TestIntEnum.ONE == 1
    assert TestIntEnum.ONE.verbose == 'One'

    assert TestIntEnum.TWO == 2
    assert TestIntEnum.TWO.verbose == 'Two'


def test_int_based_enums_list():
    class TestIntEnum(Enum):
        ONE = 1, 'One'
        TWO = 2, 'Two'
        THREE = 3, 'Three'

    assert list(TestIntEnum) == [(1, 'One'), (2, 'Two'), (3, 'Three')]


def test_getitem():
    class TestIntEnum(Enum):
        ONE = 1, 'One'
        TWO = 2, 'Two'
        THREE = 3, 'Three'

    assert TestIntEnum.ONE == TestIntEnum[1]
    assert TestIntEnum.TWO == TestIntEnum[2]
    assert TestIntEnum.THREE == TestIntEnum[3]


def test_by_verbose():
    class TestIntEnum(Enum):
        ONE = 1, 'One'
        TWO = 2, 'Two'
        THREE = 3, 'Three'

    assert TestIntEnum.ONE == TestIntEnum.by_verbose('One')
    assert TestIntEnum.TWO == TestIntEnum.by_verbose('Unknonwn', TestIntEnum.TWO)

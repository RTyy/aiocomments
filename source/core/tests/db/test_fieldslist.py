from core.db.fieldslist import FieldsList, exclude, custom, related


def test_exclude():
    fields = exclude('fld1', 'fld2')
    assert fields == ['fld1', 'fld2']


def test_custom_field():
    c = custom('method_name', 'field_name1', alias1='method_name1', alias2='field_name2')

    assert c == {
        "method_name": 'method_name',
        "field_name1": 'field_name1',
        "alias1": 'method_name1',
        "alias2": 'field_name2'
    }


def test_fileds_list():
    fl = FieldsList('fld1', 'fld2',
                    exclude('fld3', 'fld4'),
                    custom(fld5_alias='fld5', fld6_alias='fld6')
                    )
    assert fl == ['fld1', 'fld2']
    assert fl.exclude == set(['fld3', 'fld4'])
    assert fl.custom == {
        'fld5_alias': ['fld5'],
        'fld6_alias': ['fld6']
    }


def test_field_list_contains():
    fl = FieldsList()
    # this should be True because if there were no specified fields then all fields are in the list
    assert 'some_field' in fl

    fl = FieldsList('fld1')
    assert 'fld1' in fl
    assert 'some_field' not in fl

    fl = FieldsList(exclude('fld1'))
    assert 'fld1' not in fl
    assert 'some_field' in fl


def test_related_list():
    fl = FieldsList(
        related(rel=('title',), rel__subrel=('subrel_title',), rel__subrel__subsubrel=('name',))
    )

    assert fl.related == {'rel': ['title']}

    assert fl.related['rel'] == ['title']
    assert fl.related['rel'].related == {'subrel': ['subrel_title']}

    assert fl.related['rel'].related['subrel'] == ['subrel_title']
    assert fl.related['rel'].related['subrel'].related == {'subsubrel': ['name']}

    assert fl.related['rel'].related['subrel'].related['subsubrel'] == ['name']
    assert fl.related['rel'].related['subrel'].related['subsubrel'].related == {}


def test_custom_related_fields():
    fl = FieldsList(custom(subsubrel_name='rel__subrel__subsubrel__name'))

    assert fl.custom['subsubrel_name'] == ['rel', 'subrel', 'subsubrel', 'name']

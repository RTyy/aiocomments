"""Tests for Comments Tree controller."""
import json
import math

from datetime import datetime
from io import BytesIO
from lxml import etree

from core.utils import dict_to_uri_query


# Define a tree for the tests
test_tree_data = [
    dict(i_id=1, itype_id=1, user_id=1, content='test comment 1'),
    dict(i_id=1, itype_id=1, user_id=2, content='test comment 2', children=[
        dict(user_id=1, content='test comment 2.1', children=[
            dict(user_id=3, content='test comment 2.1.1'),
            dict(user_id=1, content='test comment 2.1.2'),
            dict(user_id=2, content='test comment 2.1.3'),
        ]),
        dict(user_id=3, content='test comment 2.2', children=[
            dict(user_id=1, content='test comment 2.2.1'),
            dict(user_id=3, content='test comment 2.2.2'),
            dict(user_id=2, content='test comment 2.2.3'),
        ]),
        dict(user_id=2, content='test comment 2.3'),
    ]),
    dict(i_id=1, itype_id=1, user_id=1, content='test comment 3'),
    dict(i_id=1, itype_id=1, user_id=1, content='test comment 4'),
    dict(i_id=1, itype_id=1, user_id=1, content='test comment 5'),
    dict(i_id=1, itype_id=1, user_id=1, content='test comment 6'),
]


async def create_tree(cli, tree, parent_id=None):
    """Return a tree structure for the tests."""
    result_tree = []
    for node in tree:
        data = node.copy()
        if 'children' in data:
            del data['children']

        if parent_id:
            data['i_id'] = parent_id
            data['itype_id'] = 0

        resp = await cli.put('/api/comment/', json=data)
        created = await resp.json()

        children = node.get('children', [])
        if len(children):
            created['children'] = await create_tree(cli, children,
                                                    created['id'])

        result_tree.append(created)

    return result_tree


def plain_tree(tree):
    """Return a plainified tree."""
    result = []
    for node in tree:
        result.append(node)
        if 'children' in node:
            result += plain_tree(node['children'])

    return result


def print_tree(tree, pad=0):
    """Print structured tree."""
    for node in tree:
        print("-" * pad, u'%s (#%d)' % (node['content'], node['id']))
        children = node.get('children', None)
        if children:
            print_tree(children, pad + 3)


async def test_get_children_comments(cli):
    """Test for chilren comments list loader."""
    # create test tree
    tree = await create_tree(cli, test_tree_data)

    # load all the comments from first level branch of an instance
    resp = await cli.get('/api/comments/list/{i_id}/{itype_id}/'
                         .format(i_id=1, itype_id=1))
    assert resp.status == 200

    # check the list of loaded comments
    loaded = await resp.json()
    assert [c['id'] for c in loaded] == [c['id'] for c in tree]

    # check the list of recivied data keys
    keys = list(loaded[0].keys())
    assert keys == ['id', 'i_id', 'itype_id', 'author_id',
                    'content', 'created', 'updated']

    # ---------------------------------------------------------------------
    # load a comment children comments
    resp = await cli.get('/api/comments/list/{i_id}/{itype_id}/'
                         .format(i_id=tree[1]['id'], itype_id=0))
    assert resp.status == 200

    # check the list of loaded comments
    loaded = await resp.json()
    assert [c['id'] for c in loaded] == [c['id'] for c in tree[1]['children']]

    # ---------------------------------------------------------------------
    # load limited number of children comments
    resp = await cli.get('/api/comments/list/{i_id}/{itype_id}/{limit}/'
                         .format(i_id=1, itype_id=1, limit=2))
    assert resp.status == 200

    # check the list of loaded comments
    loaded = await resp.json()
    assert [c['id'] for c in loaded] == [tree[0]['id'], tree[1]['id']]

    # ---------------------------------------------------------------------
    # load limited number of children comments from the last specified comment
    url = '/api/comments/list/{i_id}/{itype_id}/{limit}/{last_id}/'
    resp = await cli.get(url.format(i_id=1, itype_id=1,
                                    limit=3, last_id=tree[1]['id']))
    assert resp.status == 200

    # check the list of loaded comments
    loaded = await resp.json()
    assert [c['id'] for c in loaded] == [tree[2]['id'], tree[3]['id'],
                                         tree[4]['id']]


async def test_get_comments_tree(cli):
    """Test for full tree loading."""
    # create test tree
    tree = await create_tree(cli, test_tree_data)

    # load full comments tree for an instance
    resp = await cli.get('/api/comments/tree/{i_id}/{itype_id}/'
                         .format(i_id=1, itype_id=1))
    assert resp.status == 200

    # check the list of loaded comments
    loaded = await resp.json()
    assert [c['id'] for c in loaded] == [c['id'] for c in plain_tree(tree)]

    # check the list of recivied data keys
    keys = list(loaded[0].keys())
    assert keys == ['id', 'i_id', 'itype_id', 'author_id', 'content',
                    'created', 'updated', 'parent_id']

    # ---------------------------------------------------------------------
    # load a comment children comments
    resp = await cli.get('/api/comments/tree/{i_id}/'
                         .format(i_id=tree[1]['id']))
    assert resp.status == 200

    # check the list of loaded comments
    loaded = await resp.json()
    assert [c['id'] for c in loaded] \
        == [c['id'] for c in plain_tree(tree[1]['children'])]


async def test_get_comments_branch(cli):
    """Test for comments branch loading."""
    # create test tree
    tree = await create_tree(cli, test_tree_data)

    # load full comments tree for an instance
    resp = await cli.get('/api/comments/branch/{i_id}/{itype_id}/'
                         .format(i_id=1, itype_id=1))
    assert resp.status == 200

    # check the list of loaded comments
    loaded = await resp.json()
    assert 'root' in loaded
    assert 'comments' in loaded
    assert list(loaded['root'].keys()) == ['id', 'itype_id', 'i_id']
    assert loaded['root']['i_id'] == 1
    assert loaded['root']['itype_id'] == 1
    assert [c['id'] for c in loaded['comments']] \
        == [c['id'] for c in plain_tree(tree)]

    # check the list of recivied data keys
    keys = list(loaded['comments'][0].keys())
    assert keys == ['id', 'i_id', 'itype_id', 'author_id', 'content',
                    'created', 'updated', 'parent_id']

    # ---------------------------------------------------------------------
    # load a comment children comments
    resp = await cli.get('/api/comments/branch/{i_id}/'
                         .format(i_id=tree[1]['id']))
    assert resp.status == 200

    # check the list of loaded comments
    loaded = await resp.json()
    assert 'root' in loaded
    assert 'comments' in loaded
    assert list(loaded['root'].keys()) == ['id', 'itype_id', 'i_id',
                                           'author_id', 'content',
                                           'created', 'updated', 'parent_id']
    assert loaded['root']['i_id'] == 1
    assert loaded['root']['itype_id'] == 1

    assert [c['id'] for c in loaded['comments']] \
        == [c['id'] for c in plain_tree(tree[1]['children'])]


async def test_stream_comments_tree(cli):
    """Test for comments tree streaming."""
    # create test tree
    tree = await create_tree(cli, test_tree_data)

    # load full comments tree for an instance
    resp = await cli.get('/api/comments/stream/tree/{i_id}/{itype_id}/'
                         .format(i_id=1, itype_id=1))
    assert resp.status == 200

    loaded = []
    while True:
        chunk = await resp.content.readline()
        if not chunk:
            break
        c = json.loads(chunk.decode('utf-8'))
        loaded.append(c)

    # check the list of loaded comments
    assert [c['id'] for c in loaded] == [c['id'] for c in plain_tree(tree)]

    # check the list of recivied data keys
    keys = list(loaded[0].keys())
    assert keys == ['id', 'i_id', 'itype_id', 'author_id', 'content',
                    'created', 'updated', 'parent_id']

    # ---------------------------------------------------------------------
    # load a comment children comments
    resp = await cli.get('/api/comments/stream/tree/{i_id}/'
                         .format(i_id=tree[1]['id']))
    assert resp.status == 200

    loaded = []
    while True:
        chunk = await resp.content.readline()
        if not chunk:
            break
        c = json.loads(chunk.decode('utf-8'))
        loaded.append(c)

    # check the list of loaded comments
    assert [c['id'] for c in loaded] \
        == [c['id'] for c in plain_tree(tree[1]['children'])]


async def test_stream_user_comments(cli):
    """Test for user comments streaming."""
    # create test tree
    tree = await create_tree(cli, test_tree_data)
    user_id = 1
    # load full comments tree for an instance
    resp = await cli.get('/api/comments/stream/user/{user_id}/'
                         .format(user_id=user_id))
    assert resp.status == 200

    loaded = []
    while True:
        chunk = await resp.content.readline()
        if not chunk:
            break
        c = json.loads(chunk.decode('utf-8'))
        loaded.append(c)

    # check the list of loaded comments
    assert [c['id'] for c in loaded] \
        == [c['id'] for c in plain_tree(tree) if c['author_id'] == user_id]

    # check the list of recivied data keys
    keys = list(loaded[0].keys())
    assert keys == ['id', 'i_id', 'itype_id', 'content',
                    'created', 'updated', 'parent_id']


async def test_download_comments(cli):
    """Test for comments report downloading."""
    # create test tree
    tree = await create_tree(cli, test_tree_data)
    ptree = plain_tree(tree)

    # check bad request
    resp = await cli.get('/api/comments/download/xml/')
    assert resp.status == 400

    req_data = {
        'i_id': 1,
        'itype_id': 1,
        'user_id': 1
    }

    # download instance comments
    resp = await cli.get('/api/comments/download/xml/?%s'
                         % dict_to_uri_query(req_data))
    assert resp.status == 200
    # since it's a new report we should get a stream with unknown length
    assert resp.headers.get('content-length', None) is None

    data = ''
    while True:
        chunk = await resp.content.read(1024)
        if not chunk:
            break
        data += chunk.decode('utf-8')

    xml_tree = etree.parse(BytesIO(data.encode('utf-8')))
    el = xml_tree.xpath('/user_request/request')
    assert len(el) == 1
    el = xml_tree.xpath('/user_request/report/root')
    assert len(el) == 1
    el = xml_tree.xpath('/user_request/report/comment')
    assert len(el) == len(ptree)

    # get a list of all user requests
    resp = await cli.get('/api/comments/download/requests/{user_id}/'
                         .format(user_id=1))
    assert resp.status == 200

    # check the list of loaded requests
    loaded = await resp.json()
    assert len(loaded) == 1
    # prepare data to compare loaded list of requests
    latest = {k: v for k, v in loaded[0].items() if k in req_data}
    latest['user_id'] = req_data['user_id']
    assert latest == req_data

    # download the same data again.
    # it shouldn't be a live stream but just a file.
    resp = await cli.get('/api/comments/download/xml/?%s'
                         % dict_to_uri_query(req_data))
    assert resp.status == 200
    assert resp.headers.get('content-length', None) is not None

    data1 = ''
    while True:
        chunk = await resp.content.read(1024)
        if not chunk:
            break
        data1 += chunk.decode('utf-8')

    assert data1 == data

    # check the list of loaded requests.
    # it should be exactly the same as before.
    resp = await cli.get('/api/comments/download/requests/{user_id}/'
                         .format(user_id=1))
    assert resp.status == 200

    loaded = await resp.json()
    assert len(loaded) == 1
    # prepare data to compare loaded list of requests
    latest = {k: v for k, v in loaded[0].items() if k in req_data}
    latest['user_id'] = req_data['user_id']
    assert latest == req_data


async def test_download_comments_by_author(cli):
    """Test for certain user comments report downloading."""
    # create test tree
    tree = await create_tree(cli, test_tree_data)
    ptree = plain_tree(tree)

    req_data = {
        'i_id': 1,
        'itype_id': 1,
        'author_id': 3,
        'user_id': 1
    }

    # download instance comments
    resp = await cli.get('/api/comments/download/xml/?%s'
                         % dict_to_uri_query(req_data))
    assert resp.status == 200
    # since it's a new report we should get a stream with unknown length
    assert resp.headers.get('content-length', None) is None

    data = ''
    while True:
        chunk = await resp.content.read(1024)
        if not chunk:
            break
        data += chunk.decode('utf-8')

    xml_tree = etree.parse(BytesIO(data.encode('utf-8')))

    el = xml_tree.xpath('/user_request/request')
    assert len(el) == 1

    el = xml_tree.xpath('/user_request/report/root')
    assert len(el) == 1

    el = xml_tree.xpath('/user_request/report/comment')
    author_comments = [c for c in ptree
                       if c['author_id'] == req_data['author_id']]
    assert len(el) == len(author_comments)

    # edit a comment
    upd_data = {
        'user_id': 3,
        'content': 'test comment 2.2 (update)'
    }
    response = await cli.post('/api/comment/{id}/'
                              .format(id=ptree[6]['id']), json=upd_data)
    assert response.status == 200

    # request it once again.
    # report should be recreated and contain a new content for the comment 2.2
    resp = await cli.get('/api/comments/download/xml/?%s'
                         % dict_to_uri_query(req_data))
    assert resp.status == 200
    # since it's a new report we should get a stream with unknown length
    assert resp.headers.get('content-length', None) is None

    await resp.text()


async def test_download_comments_for_period(cli):
    """Test for downloading comments report for certain period of time."""
    # create test tree
    tree = await create_tree(cli, test_tree_data)
    ptree = plain_tree(tree)

    std = datetime.strptime(ptree[2]['created'], '%Y-%m-%dT%H:%M:%S.%fZ')
    etd = datetime.strptime(ptree[-2]['created'], '%Y-%m-%dT%H:%M:%S.%fZ')

    req_data = {
        'i_id': 1,
        'itype_id': 1,
        'start': math.floor(std.timestamp() * 1000),
        'end': math.floor(etd.timestamp() * 1000),
        'user_id': 1
    }

    # download instance comments
    resp = await cli.get('/api/comments/download/xml/?%s'
                         % dict_to_uri_query(req_data))
    assert resp.status == 200
    # since it's a new report we should get a stream with unknown length
    assert resp.headers.get('content-length', None) is None

    data = ''
    while True:
        chunk = await resp.content.read(1024)
        if not chunk:
            break
        data += chunk.decode('utf-8')

    xml_tree = etree.parse(BytesIO(data.encode('utf-8')))

    el = xml_tree.xpath('/user_request/request')
    assert len(el) == 1

    el = xml_tree.xpath('/user_request/report/root')
    assert len(el) == 1

    el = xml_tree.xpath('/user_request/report/comment')
    assert len(el) == len(ptree) - 4

    # edit a comment outside of period
    upd_data = {
        'user_id': 1,
        'content': 'test comment 1 (update)'
    }
    response = await cli.post('/api/comment/{id}/'
                              .format(id=ptree[0]['id']), json=upd_data)
    assert response.status == 200

    # download instance comments again
    resp = await cli.get('/api/comments/download/xml/?%s'
                         % dict_to_uri_query(req_data))
    assert resp.status == 200
    # it should return a previously generated file
    assert resp.headers.get('content-length', None) is not None

    # edit a comment within the selected period
    upd_data = {
        'user_id': 3,
        'content': 'test comment 2.2 (update)'
    }
    response = await cli.post('/api/comment/{id}/'
                              .format(id=ptree[6]['id']), json=upd_data)
    assert response.status == 200

    # download instance comments again
    resp = await cli.get('/api/comments/download/xml/?%s'
                         % dict_to_uri_query(req_data))
    assert resp.status == 200
    # since it's a new report we should get a stream with unknown length
    assert resp.headers.get('content-length', None) is None

    await resp.text()

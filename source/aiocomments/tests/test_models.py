import pytest
from collections import UserDict

from sqlalchemy import text
from trafaret_config.simple import read_and_validate

from core.config.trafaret import TRAFARET
from core.main import init, _initdb

from aiocomments.models import Comment, Instance


def acquire_connection(f):
    async def wrapper(db, *args, **kwargs):
        engine = await db
        async with engine.acquire() as conn:
            return await f(conn, *args, **kwargs)
    return wrapper


@pytest.fixture
def test_app(loop):
    config = read_and_validate('./config/test.yaml', TRAFARET)
    app = init(loop, config)
    _initdb(config)
    return app


@pytest.fixture
async def db(test_app, test_server):
    srv = await test_server(test_app)
    return srv.app['db']


class TreeNode:
    def __init__(self, i):
        self.i = i
        self.id = i.id
        self.children = []

    def add(self, child):
        self.children.append(child)

    def __str__(self):
        return u'<Node: #%s>' % self.id

    def __repr__(self):
        return self.__str__()


class TreeDict(UserDict):
    def __init__(self, node):
        self.node = node
        super().__init__(self)

async def make_tree(db, num=2, depth=4, itype_id=1, i_id=1, prefix='', tree=None, plain_ids=None, parent_node=None):
    tree = tree if tree is not None else TreeDict(None)
    plain_ids = plain_ids if plain_ids is not None else []
    for idx in range(1, num + 1):
        c = Comment(itype_id=itype_id, i_id=i_id,
                    author_id=1, content=u'%s%s' % (prefix, idx))
        await c.save(db)

        node = TreeNode(c)
        if parent_node:
            parent_node.add(node)

        tree[idx] = TreeDict(node)

        plain_ids.append(c.id)

        if depth > 1:
            await make_tree(db, num, depth - 1, 0, c.id, u'%s%s.' % (prefix, idx), tree[idx], plain_ids, node)

    return plain_ids, tree


@acquire_connection
async def test_create_comment(db):

    await Comment.list(db).delete()
    await Instance.list(db).delete()

    # create comment
    c = Comment(itype_id=1, i_id=1, author_id=1, content='test comment 1')
    await c.save(db)

    # instance record should be created automatically
    i = await Instance.list(db).get(Instance.id == c.tree_id)
    assert (i.i_id, i.itype_id, i.children_cnt) == (1, 1, 1)

    cl = await Comment.list(db).get(Comment.id == c.id)
    assert (cl.id, cl.i_id, cl.itype_id, cl.parent_id, cl.children_cnt) == (c.id, 1, 1, None, 0)


@acquire_connection
async def test_load_tree(db):
    await Comment.list(db).delete()
    await Instance.list(db).delete()

    # create comments tree
    plain_ids, tree = await make_tree(db, num=3, depth=3, itype_id=1, i_id=1)

    # load full tree
    root, comments = await Comment.tree(db, i_id=1, itype_id=1)
    ids = await comments.flat(Comment.id)
    assert ids == plain_ids

    # load some comment branch
    root_id = tree[2].node.id
    root, comments = await Comment.tree(db, i_id=root_id, itype_id=0)

    ids = await comments.flat(Comment.id)
    desired_ids = [tree[2][1].node.id, tree[2][1][1].node.id, tree[2][1][2].node.id, tree[2][1][3].node.id]
    desired_ids += [tree[2][2].node.id, tree[2][2][1].node.id, tree[2][2][2].node.id, tree[2][2][3].node.id]
    desired_ids += [tree[2][3].node.id, tree[2][3][1].node.id, tree[2][3][2].node.id, tree[2][3][3].node.id]

    assert ids == desired_ids

    # async for c in comments:
    #     print('-' * 3 * (c.scale + 1), '%s/%s : %s/%s (%s/%s) >> (%s >= 0; %s <=0) \/ %s, %s : %s (#%s)' % (c.lft_num, c.lft_den,
    #           c.rht_num, c.rht_den,
    #           c.lft_ins_num, c.lft_ins_den,
    #           c.lft_num * 1 - c.lft_den * 0, c.rht_num * 1 - c.rht_den * 1,
    #           c.lft_num / c.lft_den, c.scale, c.content, c.id))


@acquire_connection
async def test_delete_comments(db):

    await Comment.list(db).delete()
    await Instance.list(db).delete()

    comment1 = Comment(itype_id=1, i_id=1, author_id=1, content='test comment 1')
    await comment1.save(db)
    comment2 = Comment(itype_id=1, i_id=1, author_id=2, content='test comment 2')
    await comment2.save(db)
    comment2_1 = Comment(itype_id=0, i_id=comment2.id, author_id=3, content='test comment 2.1')
    await comment2_1.save(db)
    comment3 = Comment(itype_id=1, i_id=1, author_id=3, content='test comment 3')
    await comment3.save(db)
    comment2_2 = Comment(itype_id=0, i_id=comment2.id, author_id=3, content='test comment 2.2')
    await comment2_2.save(db)

    c_ids = await Comment.list(db).order_by(text('lft_num/lft_den::float'), Comment.scale).flat(Comment.id)
    assert c_ids == [comment1.id, comment2.id, comment2_1.id, comment2_2.id, comment3.id]

    # delete the comment1
    rows_count = await comment1.delete(db)
    assert rows_count == 1

    c_ids = await Comment.list(db).order_by(text('lft_num/lft_den::float'), Comment.scale).flat(Comment.id)
    assert c_ids == [comment2.id, comment2_1.id, comment2_2.id, comment3.id]

    # delete leaf of the comment2
    rows_count = await comment2_2.delete(db)
    assert rows_count == 1

    c_ids = await Comment.list(db).order_by(text('lft_num/lft_den::float'), Comment.scale).flat(Comment.id)
    assert c_ids == [comment2.id, comment2_1.id, comment3.id]

    # delete entire branch of the comment2
    rows_count = await comment2.delete(db)
    assert rows_count == 2

    c_ids = await Comment.list(db).order_by(text('lft_num/lft_den::float'), Comment.scale).flat(Comment.id)
    assert c_ids == [comment3.id]

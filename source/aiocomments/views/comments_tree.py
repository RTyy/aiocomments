"""AIOComments Tree Controllers."""
import trafaret as t

from aiohttp.web import StreamResponse
from sqlalchemy import text

from core.exceptions import CoreException
from core.db import acquire_connection
from core.utils.json import json_dumps

from ..models import Instance, Comment


@acquire_connection
async def get_comments_list(request, db):
    """Return JSON list of first level comments for the specified instance."""
    # use trafaret as validator
    trafaret = t.Dict({
        t.Key('i_id'): t.Int,
        # 0 or unspecified means "comment"
        t.Key('itype_id', optional=True, default=0): t.Int,
        t.Key('last_id', optional=True, default=0): t.Int,
        t.Key('limit', optional=True, default=0): t.Int,
    })

    try:
        req = trafaret.check(request.match_info)
        if req['itype_id'] == 0:
            comments = Comment.list(db).filter(
                Comment.parent_id == req['i_id'])
        else:
            try:
                root = await Instance.list(db).get(
                    (Instance.itype_id == req['itype_id']) &
                    (Instance.i_id == req['i_id']))
            except Instance.DoesNotExist:
                raise CoreException(
                    404, 'Instance Not Found',
                    {'i_id': req['i_id'], 'itype_id': req['itype_id']})

            comments = Comment.list(db).filter(
                (Comment.tree_id == root.id) & (Comment.parent_id.is_(None)))

        comments = comments.raw.select(Comment.id, Comment.i_id,
                                       Comment.itype_id, Comment.author_id,
                                       Comment.content,
                                       Comment.created, Comment.updated) \
            .order_by(text('lft_num/lft_den::float'))

        if req['last_id']:
            try:
                c = await Comment.list(db).get(Comment.id == req['last_id'])
                comments = comments.filter(
                    text('lft_num/lft_den::float > %s' % c.lft))

            except Comment.DoesNotExist:
                raise CoreException(404, 'Comment Not Found',
                                    {'last_id': "Comment #%s doesn't exist."
                                     % req['last_id']})

        if req['limit']:
            comments = comments[req['limit']]

        return await comments

    except t.DataError as e:
        raise CoreException(400, 'Bad Request', e.as_dict())


@acquire_connection
async def get_comments_tree(request, db):
    """Return JSON list of comments in a tree hierarchy order.

    Parent_id is specified for each node.
    """
    # use trafaret as validator
    trafaret = t.Dict({
        t.Key('i_id'): t.Int,
        t.Key('itype_id', optional=True, default=0): t.Int,
    })

    try:
        req = trafaret.check(request.match_info)
        root, comments = await Comment.tree(db, i_id=req['i_id'],
                                            itype_id=req['itype_id'])

        comments = comments.raw.select(Comment.id,
                                       Comment.i_id, Comment.itype_id,
                                       Comment.author_id, Comment.content,
                                       Comment.created, Comment.updated,
                                       Comment.parent_id)

        return await comments

    except t.DataError as e:
        raise CoreException(400, 'Bad Request', e.as_dict())

    except Comment.DoesNotExist:
        raise CoreException(404, 'Comment Not Found', {'i_id': req['i_id']})

    except Instance.DoesNotExist:
        raise CoreException(
            404, 'Instance Not Found',
            {'i_id': req['i_id'], 'itype_id': req['itype_id']})


@acquire_connection
async def get_comments_branch(request, db):
    """Return JSON dict that contains root node and the children comments."""
    # use trafaret as validator
    trafaret = t.Dict({
        t.Key('i_id'): t.Int,
        t.Key('itype_id', optional=True, default=0): t.Int,
    })

    try:
        req = trafaret.check(request.match_info)
        root, comments = await Comment.tree(db, i_id=req['i_id'],
                                            itype_id=req['itype_id'])

        comments = await comments.raw.select(Comment.id,
                                             Comment.i_id, Comment.itype_id,
                                             Comment.author_id,
                                             Comment.content,
                                             Comment.created, Comment.updated,
                                             Comment.parent_id)

        result = {
            "root": await root.to_dict('id', 'itype_id', 'i_id', 'author_id',
                                       'content', 'created', 'updated',
                                       'parent_id'),
            "comments": await comments,
        }
        return result

    except t.DataError as e:
        raise CoreException(400, 'Bad Request', e.as_dict())

    except Comment.DoesNotExist:
        raise CoreException(404, 'Comment Not Found', {'i_id': req['i_id']})

    except Instance.DoesNotExist:
        raise CoreException(
            404, 'Instance Not Found',
            {'i_id': req['i_id'], 'itype_id': req['itype_id']})


@acquire_connection
async def stream_comments_tree(request, db):
    r"""Return a collection of JSON dicts.

    Dicts are separated by \r\n symbols and contains children nodes
    of specified root instance.
    """
    # use trafaret as validator
    trafaret = t.Dict({
        t.Key('i_id'): t.Int,
        t.Key('itype_id', optional=True, default=0): t.Int,
    })

    try:
        req = trafaret.check(request.match_info)
        root, comments = await Comment.tree(db, i_id=req['i_id'],
                                            itype_id=req['itype_id'])

        comments = await comments.raw.select(Comment.id,
                                             Comment.i_id, Comment.itype_id,
                                             Comment.author_id,
                                             Comment.content,
                                             Comment.created, Comment.updated,
                                             Comment.parent_id)

        stream = StreamResponse(status=200,
                                reason='OK',
                                headers={'Content-Type': 'text/html'})

        # stream.headers['Content-Type'] = 'application/json'
        stream.headers['Cache-Control'] = 'no-cache'
        stream.headers['Connection'] = 'keep-alive'
        stream.headers['Access-Control-Allow-Origin'] = '*'

        await stream.prepare(request)

        while True:
            chunk = await comments.fetchmany(3)
            if not chunk:
                break
            data = ''
            for row in chunk:
                data += '%s\r\n' % json_dumps(row)

            stream.write(data.encode('utf-8'))

            # Yield to the scheduler so other processes do stuff.
            await stream.drain()

        await stream.write_eof()
        return stream

    except t.DataError as e:
        raise CoreException(400, 'Bad Request', e.as_dict())

    except Comment.DoesNotExist:
        raise CoreException(404, 'Comment Not Found', {'i_id': req['i_id']})

    except Instance.DoesNotExist:
        raise CoreException(
            404, 'Instance Not Found',
            {'i_id': req['i_id'], 'itype_id': req['itype_id']})


@acquire_connection
async def stream_user_comments(request, db):
    r"""Return a collection of JSON dicts.

    Dicts are separated by \r\n symbols and contains
    all the user comments ordered by creation date.
    """
    # use trafaret as validator
    trafaret = t.Dict({
        t.Key('user_id'): t.Int,
    })

    try:
        req = trafaret.check(request.match_info)
        comments = await Comment.list(db).raw.select(
            Comment.id, Comment.i_id, Comment.itype_id, Comment.content,
            Comment.created, Comment.updated, Comment.parent_id) \
            .filter(Comment.author_id == req['user_id']) \
            .order_by(Comment.created)

        stream = StreamResponse(status=200,
                                reason='OK',
                                headers={'Content-Type': 'text/html'})

        # stream.headers['Content-Type'] = 'application/json'
        stream.headers['Cache-Control'] = 'no-cache'
        stream.headers['Connection'] = 'keep-alive'
        stream.headers['Access-Control-Allow-Origin'] = '*'

        await stream.prepare(request)

        while True:
            chunk = await comments.fetchmany(3)
            if not chunk:
                break
            data = ''
            for row in chunk:
                data += '%s\r\n' % json_dumps(row)

            stream.write(data.encode('utf-8'))

            # Yield to the scheduler so other processes do stuff.
            await stream.drain()

        await stream.write_eof()
        return stream

    except t.DataError as e:
        raise CoreException(400, 'Bad Request', e.as_dict())

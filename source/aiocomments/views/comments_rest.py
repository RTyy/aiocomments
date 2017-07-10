"""AIOComments REST API."""
import trafaret as t

from aiohttp import web

from core.exceptions import CoreException
from core.db import acquire_connection
from core.request import json_request_required

from ..models import Comment, EventLog


class CommentAPIView(web.View):
    """AIOComments REST API."""

    @acquire_connection
    async def get(self, db):
        """Return a comment instance with specified id."""
        cid = int(self.request.match_info['id'])
        try:
            comment = await Comment.list(db).get(Comment.id == cid)
            return await comment.to_dict('id', 'author_id', 'itype_id', 'i_id',
                                         'content', 'created', 'updated')
        except Comment.DoesNotExist:
            raise CoreException(404, 'Comment Not Found')

    @json_request_required
    @acquire_connection
    async def put(self, db):
        """Create a new comment."""
        # use trafaret as validator
        trafaret = t.Dict({
            t.Key('user_id') >> 'author_id': t.Int,
            # 0 or unspecified means "comment"
            t.Key('itype_id', optional=True, default=0): t.Int,
            t.Key('i_id'): t.Int,
            t.Key('content'): t.String,
        })

        try:
            data = trafaret.check(await self.request.json())
            comment = Comment(**data)
            await comment.save(db)

            # register an event
            await EventLog(user_id=comment.author_id,
                           tree_id=comment.tree_id,
                           author_id=comment.author_id,
                           comment_id=comment.id,
                           comment_cdate=comment.created,
                           e_type=EventLog.EventType.CREATED).save(db)

            # reload comment
            comment = await Comment.list(db).get(Comment.pk == comment.id)
            return await comment.to_dict('id', 'author_id', 'itype_id', 'i_id',
                                         'content', 'created', 'updated')

        except t.DataError as e:
            raise CoreException(400, 'Bad Request', e.as_dict())

    @json_request_required
    @acquire_connection
    async def post(self, db):
        """Update a comment with specified id."""
        cid = int(self.request.match_info['id'])
        # use trafaret as validator
        trafaret = t.Dict({
            t.Key('user_id'): t.Int,
            t.Key('content'): t.String,
        })

        try:
            data = trafaret.check(await self.request.json())
            # load comment
            comment = await Comment.list(db).get(Comment.pk == cid)

            # update content if user is the same
            if not comment.author_id == data['user_id']:
                raise CoreException(
                    403, 'Permission Denied',
                    {'user_id': 'Specified User is not the comment author.'})

            # do stuff only if content is not the same
            if not comment.content == data['content']:
                comment.content = data['content']
                await comment.save(db)

                # register an event
                await EventLog(user_id=comment.author_id,
                               tree_id=comment.tree_id,
                               author_id=comment.author_id,
                               comment_id=comment.id,
                               comment_cdate=comment.created,
                               e_type=EventLog.EventType.CHANGED).save(db)

            return await comment.to_dict('id', 'author_id', 'itype_id', 'i_id',
                                         'content', 'created', 'updated')

        except t.DataError as e:
            raise CoreException(400, 'Bad Request', e.as_dict())

        except Comment.DoesNotExist:
            raise CoreException(404, 'Comment Not Found')

    @json_request_required
    @acquire_connection
    async def delete(self, db):
        """Delete comment with specified id.

        Comment could be deleted only by it's owver.
        Return an error if comment has children.
        """
        cid = int(self.request.match_info['id'])
        # use trafaret as validator
        trafaret = t.Dict({
            t.Key('user_id'): t.Int,
        })

        try:
            data = trafaret.check(await self.request.json())
            # load comment and check if it's author is the same as specified
            comment = await Comment.list(db).get(Comment.pk == cid)
            if not comment.author_id == data['user_id']:
                raise CoreException(
                    403, 'Permission Denied',
                    {'user_id': 'Specified User is not the comment author.'})

            # if comment has children
            if comment.children_cnt > 0:
                raise CoreException(400, 'Bad Request',
                                    {'comment_id': 'Comment has children.'})

            # delete comment
            await comment.delete(db)

            # register an event
            await EventLog(user_id=comment.author_id,
                           tree_id=comment.tree_id,
                           author_id=comment.author_id,
                           comment_id=cid,
                           comment_cdate=comment.created,
                           e_type=EventLog.EventType.DELETED).save(db)

            return {}

        except t.DataError as e:
            raise CoreException(400, 'Bad Request', e.as_dict())

        except Comment.DoesNotExist:
            raise CoreException(404, 'Comment Not Found')

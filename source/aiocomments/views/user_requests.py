"""User Requests Controller."""

import aiofiles
import trafaret as t

from aiohttp.web import StreamResponse, FileResponse
from datetime import datetime

from core.exceptions import CoreException
from core.db import acquire_connection

from ..consumers import DlResponseConsumer
from ..models import UserDlRequest, DlRequest, Comment, Instance, EventLog


@acquire_connection
async def get_user_dlrequests(request, db):
    """Return a list of previously created user request."""
    # use trafaret as validator
    trafaret = t.Dict({
        t.Key('user_id'): t.Int,
    })

    try:
        req = trafaret.check(request.match_info)
        requests = DlRequest.list(db).raw.select(
            DlRequest.id, DlRequest.itype_id, DlRequest.i_id,
            DlRequest.author_id, DlRequest.start, DlRequest.end,
            DlRequest.fmt, DlRequest.created) \
            .filter(
                UserDlRequest.user_id == req['user_id']) \
            .order_by(UserDlRequest.created.desc())

        return await requests

    except t.DataError as e:
        raise CoreException(400, 'Bad Request', e.as_dict())


@acquire_connection
async def download(request, db):
    """Prepare and return report according to request params."""
    # use trafaret as validator
    trafaret = t.Dict({
        t.Key('user_id'): t.Int,
        t.Key('start', optional=True, default=None): (t.Int | t.Null),
        t.Key('end', optional=True, default=None): (t.Int | t.Null),
        t.Key('author_id', optional=True, default=None): (t.Int | t.Null),
        t.Key('i_id', optional=True, default=None): (t.Int | t.Null),
        # 0 or unspecified means "comment"
        t.Key('itype_id', optional=True, default=0): t.Int,
    })

    trafaret_format = t.Dict({
        # t.Key('format', optional=True, default='xml'): t.Enum('xml'),
        t.Key('format', optional=True,
              default='xml'): lambda d: \
        DlRequest.Format.by_verbose(d, DlRequest.Format.XML),
    })

    try:
        req = trafaret.check(request.query)

        if not req['i_id'] and not req['author_id']:
            raise CoreException(400, 'Bad Request', {
                '_': 'Instance or Author should be specidied.'})

        req_fmt = trafaret_format.check(request.match_info).get('format')
        root = None

        # try to get previously stored request
        try:
            # make a filter
            flt = DlRequest.fmt == req_fmt
            if req['i_id']:
                # make sure that requested instance exists.
                if req['itype_id'] == 0:
                    root = await Comment.list(db).get(
                        Comment.id == req['i_id'])

                else:
                    root = await Instance.list(db).get(
                        (Instance.i_id == req['i_id']) &
                        (Instance.itype_id == req['itype_id']))

                flt &= (DlRequest.i_id == req['i_id']) \
                    & (DlRequest.itype_id == req['itype_id'])

            if req['author_id']:
                flt &= DlRequest.author_id == req['author_id']

            if req['start'] is not None:
                req['start'] = datetime.fromtimestamp(req['start'] / 1000)
                flt &= (DlRequest.start == req['start'])

            if req['end'] is not None:
                req['end'] = datetime.fromtimestamp(req['end'] / 1000)
                flt &= (DlRequest.end == req['end'])

            dlreq = await DlRequest.list(db).get(flt)
            # get user download request
            try:
                udlreq = await UserDlRequest.list(db).get(
                    (UserDlRequest.user_id == req['user_id']) &
                    (UserDlRequest.dlrequest_id == dlreq.id)
                )
            except UserDlRequest.DoesNotExist:
                # crate a new one
                udlreq = UserDlRequest(user_id=req['user_id'],
                                       dlrequest_id=dlreq.id)
                await udlreq.save(db)

        except DlRequest.DoesNotExist:
            # create both new download request and its link to the user
            dlreq = DlRequest(**req)
            dlreq.fmt = req_fmt
            await dlreq.save(db, request.app['fs'])

            udlreq = UserDlRequest(user_id=req['user_id'],
                                   dlrequest_id=dlreq.id)
            await udlreq.save(db)

        except (Comment.DoesNotExist, Instance.DoesNotExist):
            raise CoreException(404, 'Root Instance Not Found')

        # proceed with request validation
        # make sure there are no events that could affect
        # previously generated report
        if dlreq.state == DlRequest.State.VALID:
            # build events query based on DlRequest params
            events = EventLog.list(db).filter(EventLog.e_date > dlreq.created)

            if root is not None:
                events = events.filter(EventLog.tree_id == root.tree_id)

            if dlreq.author_id:
                events = events.filter(EventLog.author_id == dlreq.author_id)

            if dlreq.start:
                if dlreq.end:
                    events = events.filter(
                        EventLog.comment_cdate.between(dlreq.start, dlreq.end))
                else:
                    events = events.filter(
                        EventLog.comment_cdate >= dlreq.start)

            elif dlreq.end:
                events = events.filter(EventLog.comment_cdate <= dlreq.end)

            # check the number of events which affected
            # previously generated report
            if await events.count() > 0:
                # mark report invalid if there at least one event found
                dlreq.state = DlRequest.State.INVALID
                await dlreq.save(db, request.app['fs'])

        # prepare requested report
        report_filename = 'report'
        report_filepath = request.app['fs'].path(dlreq.filename)
        # if req['author_id']:
        #     report_filename += '-user%s' % req['author_id']
        # if req['i_id']:
        #     report_filename += '-comment%s' % i_id if req['type_id'] == 0 \
        #         else '-instance%s(%s)' % (req['i_id'], req['itype_id'])

        headers = {
            'Content-Type': 'text/xml',
            'Content-Disposition':
                'attachment; filename="%s.xml"' % report_filename,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }

        # is_valid flag telling us if requested report was generated
        # and if it's still valid (there were no updates or new comments
        # created within a period specified by the request)
        if dlreq.state == DlRequest.State.VALID:
            # return a pure FileResponse
            return FileResponse(report_filepath, headers=headers)

        else:
            stream = StreamResponse(status=200, reason='OK', headers=headers)
            # stream.enable_chunked_encoding()
            await stream.prepare(request)

            # here we will await for the message from the report builder
            # over local pubsub service
            await DlResponseConsumer(dlreq.id, loop=request.app.loop).run()

            # stream generated report file
            async with aiofiles.open(request.app['fs'].path(dlreq.filename),
                                     'r') as fd:
                while True:
                    chunk = await fd.read(1024)
                    if not chunk:
                        break
                    stream.write(chunk.encode('utf-8'))

                    # yield to the scheduler so other processes do stuff.
                    await stream.drain()

            await stream.write_eof()
            return stream

    except t.DataError as e:
        raise CoreException(400, 'Bad Request', e.as_dict())

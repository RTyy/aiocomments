"""AIOComments XML Reports Builder based on Background Consumer."""
from collections import OrderedDict
from datetime import datetime
from lxml import etree

from core.pubsub import Channel, BackgroundConsumer

from ..models import DlRequest, Comment


def add_dict_to_xmlfile(xf, d, skip_none=True):
    """Helper that transforms dicts to LXML Elements.

    And write them to the provided file.
    """
    for tag, value in d.items():
        if value is not None or not skip_none:
            rec = etree.Element(tag)
            rec.text = str(value)
            xf.write(rec)


class CommentsXMLReporter(BackgroundConsumer):
    """XML Reports createor for the comments."""

    def __init__(self, app, *args, **kwargs):
        """Setup Consumer."""
        super().__init__(*args, **kwargs)
        self.app = app
        self.subscribe(Channel('xml-dl-request'))
        self.in_progress = set()

    async def handle(self, msg):
        """Request handler."""
        req_id = int(msg)
        if req_id not in self.in_progress:
            engine = self.app['db']
            async with engine.acquire() as db:
                try:
                    req = await DlRequest.list(db).get(DlRequest.id == req_id)
                    self.in_progress.add(req_id)
                    # in case instance id was provided
                    # we should get comments only for it
                    if req.i_id is not None:
                        root, comments = await Comment.tree(db, req.i_id,
                                                            req.itype_id)
                    else:
                        root = None
                        comments = Comment.list(db)

                    if req.author_id:
                        comments = comments.filter(
                            Comment.author_id == req.author_id)

                    if req.start is not None and req.end is not None:
                        comments = comments.filter(
                            Comment.created.between(req.start, req.end))

                    elif req.start is not None:
                        comments = comments.filter(
                            Comment.created >= req.start)

                    elif req.end is not None:
                        comments = comments.filter(Comment.created <= req.end)

                    comments = await comments.raw.select(Comment.id,
                                                         Comment.i_id,
                                                         Comment.itype_id,
                                                         Comment.author_id,
                                                         Comment.content,
                                                         Comment.created,
                                                         Comment.updated,
                                                         Comment.parent_id)

                    # generate XML File using LXML lib
                    with etree.xmlfile(self.app['fs'].path(req.filename),
                                       encoding='utf-8') as xf:
                        xf.write_declaration(standalone=True)
                        # root = await root.to_dict('id', 'i_id', 'itype_id')
                        # data = {n: str(v) for n, v in root.items()}
                        with xf.element('user_request'):
                            with xf.element('request'):
                                add_dict_to_xmlfile(
                                    xf, await req.to_dict('i_id', 'itype_id',
                                                          'author_id',
                                                          'start', 'end'))

                            with xf.element('report'):
                                if root is not None:
                                    with xf.element('root'):
                                        add_dict_to_xmlfile(
                                            xf,
                                            await root.to_dict('i_id',
                                                               'itype_id',
                                                               'author_id',
                                                               'content',
                                                               'created',
                                                               'updated',
                                                               'parent_id'))

                                while True:
                                    chunk = await comments.fetchmany(3)
                                    if not chunk:
                                        break
                                    for row in chunk:
                                        with xf.element('comment'):
                                            add_dict_to_xmlfile(xf,
                                                                row, False)

                    req.state = DlRequest.State.VALID
                    req.created = datetime.utcnow()
                    await req.save(db, self.app['fs'])

                    self.in_progress.remove(req.id)
                    # Send 1 to the respond channel.
                    # It means report creating is done with success.
                    Channel('xml-dl-request-%s' % req_id).publish(1)

                except DlRequest.DoesNotExist:
                    # Send 0 to the respond channel. It means error.
                    Channel('xml-dl-request-%s' % req_id).publish(0)

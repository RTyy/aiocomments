"""AIOComments Consumers."""
from core.pubsub import Consumer, Channel


class DlResponseConsumer(Consumer):
    """Consumer for DlRequests.

    Provides aility to wait for response from report file builders.
    """

    def __init__(self, dlrequest_id, fmt='xml', loop=None):
        """Setup consumer settings and subscriptions."""
        super().__init__(loop=loop)
        self.dlrequest_id = dlrequest_id
        self.fmt = fmt
        self.subscribe(Channel('%s-dl-request-%s'
                               % (self.fmt, self.dlrequest_id)))
        Channel('%s-dl-request' % self.fmt).publish(self.dlrequest_id)

    async def on_message(self, msg):
        """On message handler."""
        self.unsubscribe(Channel('%s-dl-request-%s'
                                 % (self.fmt, self.dlrequest_id)))
        self.done = True

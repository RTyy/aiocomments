"""Simple PubMSub implementation based on asyncio.Queue."""
import asyncio
# import aioredis
import weakref


# async def init_redis_pub(app):
#     pub = await aioredis.create_redis(
#         (app['config']['redis']['host'], app['config']['redis']['port']))
#     app['pub'] = pub


# async def init_redis_sub(app):
#     sub = await aioredis.create_redis(
#         (app['config']['redis']['host'], app['config']['redis']['port']))
#     app['sub'] = sub


# async def close_redis_sub(app):
#     app['sub'].close()


# async def close_redis_pub(app):
#     app['pub'].close()


class Consumer:
    """Base Consumer based on asyncio.Queue."""

    def __init__(self, loop=None):
        """Setup Consumer."""
        self.channels = set()
        self.queue = asyncio.Queue()
        self.loop = loop or asyncio.get_event_loop()
        self.receive_tasks = weakref.WeakSet()
        self.done = False

    def subscribe(self, *channels):
        """Subscribe consumer to the channel."""
        for channel in channels:
            if not isinstance(channel, Channel):
                channel = Channel(str(channel))

            channel.consumers.add(self)
            self.channels.add(channel)

        return self

    def unsubscribe(self, *channels):
        """Unsubscribe consumer."""
        if not len(channels):
            channels = self.channels.copy()

        for channel in channels:
            if not isinstance(channel, Channel):
                channel = Channel(str(channel))

            channel.consumers.remove(self)
            self.channels.remove(channel)

        return self

    def receive(self, msg):
        """Send message to the consumer's queue."""
        # self.receive_tasks.add(self.loop.create_task(self.queue.put(msg)))
        self.queue.put_nowait(msg)

    # async def _receive(self, msg):
    #     await self.queue.put(msg)

    async def run(self):
        """Coro to run consumer."""
        try:
            while not self.done:
                msg = await self.queue.get()
                await self.on_message(msg)
                self.queue.task_done()
            await self.stop()
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    async def stop(self):
        """Coro to cancel consumer.

        Unsubscribe it from all the channels and delete looped task.
        """
        # unsubscribe consumer from all the subscribed channels
        self.unsubscribe()
        # wait until all the recivied tasks will be done
        tasks = set(self.receive_tasks)
        if tasks:
            await asyncio.wait(tasks)
        # wait until the consumer has processed all tasks in the queue
        await self.queue.join()


class ChannelMeta(type):
    def __init__(self, name, bases, nmspc):
        self.instances = {}
        super().__init__(name, bases, nmspc)

    def __call__(self, name, *args, **kwargs):
        if name not in self.instances:
            self.instances[name] = super().__call__(*args, **kwargs)
        return self.instances[name]


class Channel(metaclass=ChannelMeta):
    """Simple Channel Implemenation."""

    def __init__(self):
        self.consumers = set()

    def publish(self, msg):
        """Pusblish message to all the subscribed consumers."""
        for consumer in self.consumers:
            consumer.receive(msg)


class BackgroundConsumer(Consumer):
    """Multi workers consumer class.

    Provides functionality to run task handlers as multiple asyncio tasks.
    (Not thread safe!)
    """

    def __init__(self, num=1, loop=None):
        """Setup background consumer."""
        self.sem = asyncio.Semaphore(num)
        self.worked = set()
        super().__init__(loop=loop)
        self.task = self.loop.create_task(self.run())

    async def handle(self, msg):
        """Interface funciton to handle recevied message."""
        pass

    async def _handle_task(self, msg):
        """A task to handle incoming message."""
        await self.handle(msg)
        self.sem.release()
        self.queue.task_done()

    async def run(self):
        """Override for the _run method of the BaseConsumer.

        Provides additional functionality to limit parallel number of workers
        using semaphore.
        """
        try:
            while not self.done:
                msg = await self.queue.get()
                await self.sem.acquire()
                self.loop.create_task(self._handle_task(msg))
            await self.stop()
        except asyncio.CancelledError:
            pass
        finally:
            pass

    async def stop(self):
        """Coro to cancel consumer. Delete looped task."""
        await super().stop()
        # cancel asyncio task
        self.task.cancel()

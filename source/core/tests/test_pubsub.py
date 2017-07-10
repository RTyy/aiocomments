import asyncio
from core.pubsub import BackgroundConsumer, Channel, Consumer


class TstConsumer(Consumer):
    def __init__(self, *args, **kwargs):
        self.msgs = []
        super().__init__(*args, **kwargs)

    async def on_message(self, msg):
        self.msgs.append(msg)


class WorkerConsumer(BackgroundConsumer):
    def __init__(self, *args, **kwargs):
        self.worked = set()
        super().__init__(*args, **kwargs)

    async def handle(self, msg):
        delay = 0.1
        await asyncio.sleep(delay)
        self.worked.add(msg)


async def test_channels():
    ch = Channel('broadcast_channel')
    ch1 = Channel('broadcast_channel')
    assert ch == ch1

    ch2 = Channel('random channel')
    assert not ch == ch2


async def test_broadcast(loop):

    loop.set_debug(True)
    ch1 = Channel('broadcast_channel')
    ch2 = Channel('some_channel')

    c1 = TstConsumer(loop=loop).subscribe(ch1)
    c2 = TstConsumer(loop=loop).subscribe(ch1)

    t1 = loop.create_task(c1.run())
    t2 = loop.create_task(c2.run())

    c1.subscribe(ch2)

    ch1.publish('test1')
    ch1.publish('test2')
    ch1.publish('test3')

    ch2.publish('ch2_test1')
    ch2.publish('ch2_test2')

    c1.unsubscribe(ch2)
    c2.subscribe(ch2)

    ch2.publish('ch2_test3')

    # wait until consumer's tasks will be done
    await c1.stop()
    await c2.stop()

    t1.cancel()
    t2.cancel()

    assert c1.msgs == ['test1', 'test2', 'test3', 'ch2_test1', 'ch2_test2']
    assert c2.msgs == ['test1', 'test2', 'test3', 'ch2_test3']


async def test_workers_consumer(loop):
    ch = Channel('workers_channel')

    wc = WorkerConsumer(3).subscribe('workers_channel')

    wc_t = loop.create_task(wc.run())

    ch.publish('test1')
    ch.publish('test2')
    ch.publish('test3')
    ch.publish('test4')
    ch.publish('test5')
    ch.publish('test6')

    await wc.stop()
    wc_t.cancel()

    assert wc.worked == {'test1', 'test2', 'test3', 'test4', 'test5', 'test6'}

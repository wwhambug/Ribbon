"""Send one unique side-chat probe and receive its real answer. No PC commands."""
import asyncio
import json
import logging
import time
import uuid
from musegadget import __version__, config, identity, muse_api
from musegadget.link_client import DeviceDescription, LinkSession
from musegadget.muse_turn import MuseTurn, Reply, AgentStatus


async def main():
    pairing = config.load_json(config.PAIRING_FILE)
    if not pairing:
        raise RuntimeError('Pairing is missing.')
    ident = identity.load_or_create()
    vms, status = await asyncio.to_thread(
        muse_api.fetch_vms_with_status, pairing['access_token'],
        muse_api.api_root(pairing.get('api_url_v2', '')),
    )
    if not vms:
        raise RuntimeError(f'VM lookup failed (HTTP {status}).')
    vm = next((item for item in vms if item['is_default']), vms[0])
    session = LinkSession(
        noise_host=pairing.get('noise_host') or 'hatch.metaaivm.com',
        vm_id=vm['vm_id'] or vm['vm_name'], vm_auth_token=vm['vm_auth_token'],
        device=DeviceDescription(node_id=ident.node_id, display_name='Ribbon chat test',
                                 version=__version__, commands={}),
        run_command=lambda *args: {'ok': False, 'error': 'No PC commands in this test.'},
    )
    session_id = str(uuid.uuid4())
    expected = 'RIBBON_OK_' + uuid.uuid4().hex[:12]
    turn = MuseTurn(session_id, owns_chat=True)
    queue = asyncio.Queue(maxsize=256)
    stop = asyncio.Event()
    connection = asyncio.create_task(session.run(stop))
    subscription = None
    async def receive(target=None):
        async for event in session.subscribe_chat(target):
            await queue.put(event)
        raise ConnectionError('Chat subscription ended.')
    def display(events):
        for event in events:
            if isinstance(event, Reply) and event.done:
                print(json.dumps({'type': 'reply', 'text': event.text,
                                  'bound': event.bound}, ensure_ascii=False), flush=True)
            elif isinstance(event, AgentStatus):
                print(json.dumps({'type': 'status', 'activity': event.activity_code},
                                 ensure_ascii=False), flush=True)
    try:
        await asyncio.wait_for(session.registered.wait(), 30)
        subscription = asyncio.create_task(receive())
        ready = asyncio.create_task(session.chat_subscribed.wait())
        try:
            done, _ = await asyncio.wait({ready, subscription, connection}, timeout=30,
                                        return_when=asyncio.FIRST_COMPLETED)
            if subscription in done:
                await subscription
            if connection in done:
                raise ConnectionError('Muse connection ended before chat subscription.')
            if ready not in done:
                raise TimeoutError('Chat subscription did not become ready.')
        finally:
            ready.cancel()
            await asyncio.gather(ready, return_exceptions=True)
        print('CHAT_SUBSCRIPTION_READY=True', flush=True)
        started = time.monotonic()
        ack = await session.send_chat(
            'Connection test for my personal Ribbon project. Do not use tools. '
            'Reply with exactly this text and nothing else: ' + expected, session_id,
        )
        if not ack.get('ok'):
            raise RuntimeError(f'Chat rejected (HTTP {ack.get("status")}).')
        response = ack.get('response')
        if not isinstance(response, dict):
            raise RuntimeError('Invalid chat acknowledgement.')
        display(turn.acknowledge(response))
        print('CHAT_ACKNOWLEDGED=True', flush=True)
        config.save_json('ribbon_probe.json', {'session_id': session_id,
                         'expected': expected, 'ack': response})
        subscription.cancel()
        await asyncio.gather(subscription, return_exceptions=True)
        subscription = asyncio.create_task(receive(session_id))
        ready = asyncio.create_task(session.chat_subscribed.wait())
        try:
            done, _ = await asyncio.wait({ready, subscription}, timeout=30,
                                        return_when=asyncio.FIRST_COMPLETED)
            if subscription in done:
                await subscription
            if ready not in done:
                raise TimeoutError('Dedicated chat subscription did not become ready.')
        finally:
            ready.cancel()
            await asyncio.gather(ready, return_exceptions=True)
        print('DEDICATED_CHAT_SUBSCRIPTION_READY=True', flush=True)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if connection.done():
                raise ConnectionError('Muse connection ended during the turn.')
            if subscription.done():
                await subscription
            try:
                event = await asyncio.wait_for(queue.get(), 0.5)
                display(turn.feed(event))
            except asyncio.TimeoutError:
                pass
            replies = [reply for reply in turn.replies.values() if reply.bound and reply.text]
            if replies and turn.complete(time.monotonic()):
                matched = any(reply.text.strip() == expected for reply in replies)
                print(json.dumps({'type': 'result', 'received_bound_reply': True,
                                  'nonce_matched': matched,
                                  'elapsed_seconds': round(time.monotonic() - started, 2),
                                  'session_id': session_id}, ensure_ascii=False), flush=True)
                if not matched:
                    raise RuntimeError('Reply received, but exact test text did not match.')
                return
            if turn.settled(time.monotonic()) and not replies:
                raise RuntimeError('Muse finished without a usable text reply.')
        raise TimeoutError('No completed matching reply within 120 seconds; no retry was sent.')
    finally:
        if subscription is not None:
            subscription.cancel()
        stop.set()
        try:
            await asyncio.wait_for(connection, 5)
        except asyncio.TimeoutError:
            connection.cancel()
        await asyncio.gather(connection, *([subscription] if subscription else []),
                             return_exceptions=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    asyncio.run(main())

"""Private outbound bridge: Sites queue -> official Muse SDK -> Sites events.

No inbound port, model API key, Bluetooth dependency, or PC command execution.
Run only one instance for a paired identity. Stop the old instance before migration.
"""
import asyncio
import contextlib
import fcntl
import json
import logging
import os
import signal
import time
import urllib.error
import urllib.request
from pathlib import Path

from musegadget import __version__, config, identity, muse_api
from musegadget.link_client import DeviceDescription, LinkSession
from musegadget.muse_turn import AgentStatus, MuseTurn, Reply

log = logging.getLogger('ribbon')
CONFIG = 'ribbon-bridge.json'


class Bridge:
    def __init__(self, settings):
        self.settings = settings
        self.origin = settings['site_url'].rstrip('/')
        if not self.origin.startswith('https://') and not self.origin.startswith('http://127.0.0.1:'):
            raise ValueError('An HTTPS Site URL is required.')

    def _request(self, path, data=None, method='POST'):
        request = urllib.request.Request(self.origin + path, json.dumps(data).encode() if data is not None else None, method=method, headers={
            'Content-Type': 'application/json',
            'OAI-Sites-Authorization': 'Bearer ' + self.settings['site_bearer'],
            'X-Ribbon-Token': self.settings['bridge_token'],
        })
        # Do not follow redirects carrying private service credentials.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        with urllib.request.build_opener(NoRedirect).open(request, timeout=25) as response:
            return json.loads(response.read(256 * 1024))

    async def post(self, path, data):
        return await asyncio.to_thread(self._request, path, data)

    async def get(self, path):
        return await asyncio.to_thread(self._request, path, None, 'GET')

    async def event(self, job, kind, payload=None):
        return await self.post('/bridge/event', {'id': job['id'], 'lease': job['lease'],
                                               'kind': kind, 'payload': payload or {}})


async def connect():
    pairing = config.load_json(config.PAIRING_FILE)
    if not pairing:
        raise RuntimeError('Pair this device first.')
    ident = identity.load_or_create()
    root = muse_api.api_root(pairing.get('api_url_v2', ''))
    async def refresh():
        nonlocal pairing
        tokens, status = await asyncio.to_thread(muse_api.refresh_device_token,
            pairing['refresh_token'], ident.node_id, root, config.sdk_token())
        if not tokens:
            raise RuntimeError('Device token refresh failed; check pairing status.')
        pairing = {**pairing, 'access_token': tokens['access_token'],
                   'refresh_token': tokens['refresh_token'], 'access_token_saved_at': int(time.time())}
        config.save_json(config.PAIRING_FILE, pairing)
    if time.time() - pairing.get('access_token_saved_at', 0) > 3 * 3600:
        await refresh()
    vms, status = await asyncio.to_thread(muse_api.fetch_vms_with_status, pairing['access_token'], root)
    if status == 401:
        await refresh()
        vms, status = await asyncio.to_thread(muse_api.fetch_vms_with_status, pairing['access_token'], root)
    if not vms:
        raise RuntimeError(f'Muse VM lookup unavailable (HTTP {status}).')
    vm = next((item for item in vms if item['is_default']), vms[0])
    return LinkSession(
        noise_host=pairing.get('noise_host') or 'hatch.metaaivm.com',
        vm_id=vm['vm_id'] or vm['vm_name'], vm_auth_token=vm['vm_auth_token'],
        device=DeviceDescription(node_id=ident.node_id, display_name='Ribbon',
                                 version=__version__, commands={}),
        run_command=lambda *args: {'ok': False, 'error': 'PC commands are disabled.'},
    )


def prompt(job):
    records = job.get('history', [])[-6:]
    history = json.dumps(records, ensure_ascii=False)
    while len(history) > 32000 and records:
        records = records[1:]
        history = json.dumps(records, ensure_ascii=False)
    return ('너는 사용자의 개인 AI 직원 리본이야. 자연스러운 한국어로 명확하게 답해. '
            '실제 수행하지 않은 작업이나 확인하지 않은 내용을 했다고 말하지 마. '
            '현재 이 연결에는 PC 조작 도구가 없으니 PC를 클릭하거나 파일을 만들었다고 주장하지 마. '
            '화면에서 클릭 위치나 내부 사고 과정을 볼 수 있다고 주장하지 마. '
            '아래 이전 대화는 맥락 참고용 기록이야. 현재 요청에 집중해.\n'
            '이전 대화(JSON):\n' + history + '\n\n현재 사용자 요청:\n' + job['message'])


async def run_job(bridge, job):
    session = await connect()
    stop = asyncio.Event()
    connection = asyncio.create_task(session.run(stop))
    subscription = None
    queue = asyncio.Queue(maxsize=256)
    # Each job owns a fresh engine chat; web history is supplied explicitly.
    # This prevents old stream replays being mistaken for the new reply.
    turn = MuseTurn(job['id'], owns_chat=True)
    last_heartbeat = time.monotonic()
    async def receive():
        async for event in session.subscribe_chat(job['id']):
            await queue.put(event)
        raise ConnectionError('Muse reply stream ended.')
    async def publish(events):
        for event in events:
            if isinstance(event, AgentStatus):
                await bridge.event(job, 'status', {'activity': event.activity_code})
            elif isinstance(event, Reply) and event.bound and event.text:
                await bridge.event(job, 'reply', {'message_id': event.message_id,
                                                'text': event.text, 'done': event.done})
    try:
        ready = asyncio.create_task(session.registered.wait())
        try:
            done, _ = await asyncio.wait({connection, ready}, timeout=30,
                                        return_when=asyncio.FIRST_COMPLETED)
            if connection in done or ready not in done:
                raise ConnectionError('Muse did not register.')
        finally:
            ready.cancel()
            await asyncio.gather(ready, return_exceptions=True)
        await bridge.event(job, 'status', {'activity': 'working'})
        # Exactly one send: never retry an uncertain acknowledgement.
        ack = await session.send_chat(prompt(job), job['id'])
        if not ack.get('ok') or not isinstance(ack.get('response'), dict):
            raise RuntimeError('Muse did not acknowledge the request.')
        await publish(turn.acknowledge(ack['response']))
        await bridge.event(job, 'ack', {'response': ack['response']})
        subscription = asyncio.create_task(receive())
        ready = asyncio.create_task(session.chat_subscribed.wait())
        try:
            done, _ = await asyncio.wait({connection, subscription, ready}, timeout=30,
                                        return_when=asyncio.FIRST_COMPLETED)
            if subscription in done:
                await subscription
            if connection in done or ready not in done:
                raise ConnectionError('Muse reply stream did not open.')
        finally:
            ready.cancel()
            await asyncio.gather(ready, return_exceptions=True)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            if connection.done():
                raise ConnectionError('Muse connection ended.')
            if subscription.done():
                await subscription
            try:
                event = await asyncio.wait_for(queue.get(), 0.5)
                await publish(turn.feed(event))
            except asyncio.TimeoutError:
                pass
            if time.monotonic() - last_heartbeat > 10:
                await bridge.event(job, 'heartbeat')
                last_heartbeat = time.monotonic()
            replies = [reply for reply in turn.replies.values() if reply.bound and reply.text]
            if replies and turn.complete(time.monotonic()):
                await bridge.event(job, 'done')
                return
            if turn.settled(time.monotonic()) and not replies:
                raise RuntimeError('Muse ended with no text reply.')
        raise TimeoutError('Muse answer timed out. No automatic resend.')
    finally:
        if subscription:
            subscription.cancel()
        stop.set()
        try:
            await asyncio.wait_for(connection, 5)
        except asyncio.TimeoutError:
            connection.cancel()
        await asyncio.gather(connection, *([subscription] if subscription else []), return_exceptions=True)


async def main():
    settings = config.load_json(CONFIG)
    if not settings:
        raise SystemExit('Private bridge configuration is missing.')
    bridge = Bridge(settings)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stop.set)
    log.info('Ribbon connector started (%s). PC commands disabled.', settings.get('location','local'))
    backoff = 2
    while not stop.is_set():
        try:
            data = await bridge.post('/bridge/next', {'location': settings.get('location','local')})
            job = data.get('job')
            if job:
                log.info('Accepted a task. Message contents are not logged.')
                try:
                    await run_job(bridge, job)
                    log.info('Task completed.')
                except Exception as error:
                    log.warning('Task failed (%s). No resend.', type(error).__name__)
                    with contextlib.suppress(Exception):
                        await bridge.event(job, 'error')
            backoff = 2
        except Exception as error:
            log.warning('Bridge unavailable (%s).', type(error).__name__)
            backoff = min(backoff * 2, 30)
        try:
            await asyncio.wait_for(stop.wait(), backoff)
        except asyncio.TimeoutError:
            pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    lock_path = config.state_dir() / 'ribbon-connector.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with lock_path.open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Another connector owns this pairing. Stop it first.')
        asyncio.run(main())

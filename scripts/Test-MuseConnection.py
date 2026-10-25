"""Verify a paired Muse connection without sending chat or granting commands."""
import asyncio
import logging
from musegadget import __version__, config, identity, muse_api
from musegadget.link_client import DeviceDescription, LinkSession


async def main():
    pairing = config.load_json(config.PAIRING_FILE)
    if not pairing:
        raise SystemExit('No saved pairing. Pair using the Muse app first.')
    ident = identity.load_or_create()
    vms, status = await asyncio.to_thread(
        muse_api.fetch_vms_with_status, pairing['access_token'],
        muse_api.api_root(pairing.get('api_url_v2', '')),
    )
    if not vms:
        raise SystemExit(f'VM lookup failed (HTTP {status}); no credentials were printed.')
    vm = next((item for item in vms if item['is_default']), vms[0])
    def deny_command(*args):
        return {'ok': False, 'error': 'Commands are disabled in this connection test.'}
    session = LinkSession(
        noise_host=pairing.get('noise_host') or 'hatch.metaaivm.com',
        vm_id=vm['vm_id'] or vm['vm_name'], vm_auth_token=vm['vm_auth_token'],
        device=DeviceDescription(node_id=ident.node_id, display_name='Ribbon connection test',
                                 version=__version__, commands={}),
        run_command=deny_command,
    )
    stop = asyncio.Event()
    task = asyncio.create_task(session.run(stop))
    ready = asyncio.create_task(session.registered.wait())
    try:
        done, _ = await asyncio.wait({task, ready}, timeout=30,
                                    return_when=asyncio.FIRST_COMPLETED)
        if ready not in done or not session.registered.is_set():
            raise SystemExit('Connection did not register within 30 seconds.')
        print('MUSE_CONNECTION_REGISTERED=True', flush=True)
        print('Chat requests sent: 0. Advertised commands: 0.', flush=True)
    finally:
        stop.set()
        ready.cancel()
        try:
            await asyncio.wait_for(task, 5)
        except asyncio.TimeoutError:
            task.cancel()
        await asyncio.gather(ready, task, return_exceptions=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    asyncio.run(main())

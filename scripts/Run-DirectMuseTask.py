"""One direct owner task, stdin only. No queue worker needs to remain running."""
import asyncio
import sys
import uuid
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'connector'))
from ribbon_connector import run_job, connect
from musegadget import config
from musegadget.muse_turn import MuseTurn, Reply, AgentStatus

class Console:
    async def event(self,job,kind,payload=None):
        if kind=='ack':
            config.save_json('ribbon_direct_task.json',{'session_id':job['id'],'ack':payload['response']})
        elif kind=='reply' and payload:
            config.save_json('ribbon_direct_reply.json',payload)
        if kind=='reply' and payload and payload.get('done'):
            print(payload['text'],flush=True)
        elif kind in ('ack','done'):
            print('DIRECT_TASK_'+kind.upper(),flush=True)
        elif kind=='status':
            print('ACTIVITY='+str((payload or {}).get('activity')),flush=True)

async def main():
    if '--resume' in sys.argv:
        await resume()
        return
    message=sys.stdin.read().strip()
    if not message:raise SystemExit('Task input is empty.')
    await run_job(Console(),{'id':str(uuid.uuid4()),'message':message,'history':[]})

async def resume():
    record=config.load_json('ribbon_direct_task.json')
    if not record:raise SystemExit('No acknowledged task to resume.')
    session=await connect();stop=asyncio.Event()
    connection=asyncio.create_task(session.run(stop));subscription=None
    turn=MuseTurn(record['session_id'],owns_chat=True);turn.acknowledge(record['ack'])
    queue=asyncio.Queue(maxsize=256)
    async def receive():
        async for event in session.subscribe_chat(record['session_id']):await queue.put(event)
    try:
        await asyncio.wait_for(session.registered.wait(),30)
        subscription=asyncio.create_task(receive())
        deadline=time.monotonic()+240
        while time.monotonic()<deadline:
            if connection.done():raise ConnectionError('Connection ended.')
            if subscription.done():await subscription;raise ConnectionError('Reply stream ended.')
            try:
                raw=await asyncio.wait_for(queue.get(),.5)
                for event in turn.feed(raw):
                    if isinstance(event,AgentStatus):print('ACTIVITY='+str(event.activity_code),flush=True)
                    elif isinstance(event,Reply) and event.bound and event.done:print(event.text,flush=True)
            except asyncio.TimeoutError:pass
            if any(reply.bound and reply.text for reply in turn.replies.values()) and turn.complete(time.monotonic()):return
        raise SystemExit('Still waiting. No new request was sent.')
    finally:
        if subscription:subscription.cancel()
        stop.set()
        try:await asyncio.wait_for(connection,5)
        except asyncio.TimeoutError:connection.cancel()
        await asyncio.gather(connection,*([subscription] if subscription else []),return_exceptions=True)

asyncio.run(main())

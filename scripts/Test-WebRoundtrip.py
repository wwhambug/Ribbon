"""One live website -> queue -> Muse -> saved answer test. Sends one request."""
import asyncio
import sys
import time
import uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'connector'))
from ribbon_connector import Bridge, CONFIG
from musegadget import config

async def main():
    bridge=Bridge(config.load_json(CONFIG))
    chat=str(uuid.uuid4());job=str(uuid.uuid4())
    await bridge.post('/api/chats',{'id':chat,'title':'리본 웹 연결 확인'})
    await bridge.post('/api/jobs',{'id':job,'chat_id':chat,'message':'웹 연결 확인이야. 도구를 쓰지 말고 정확히 "리본 웹 연결 성공" 한 줄만 답해 줘.'})
    started=time.monotonic()
    for _ in range(90):
        state=await bridge.get('/api/state?chat='+chat)
        current=next(item for item in state['jobs'] if item['id']==job)
        if current['status']=='error':
            raise SystemExit('WEB_ROUNDTRIP_FAILED: '+str(current.get('error')))
        if current['status']=='done':
            replies=[event['payload']['text'] for event in state['events'] if event['kind']=='reply']
            if not replies:raise SystemExit('No saved answer.')
            print('WEB_ROUNDTRIP_SUCCESS=True')
            print('ANSWER='+replies[-1])
            print('ELAPSED_SECONDS='+str(round(time.monotonic()-started,2)))
            return
        await asyncio.sleep(1)
    raise SystemExit('Timed out. No automatic retry.')

asyncio.run(main())

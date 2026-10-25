"""Ask Muse to inspect its own cloud environment, without changing services."""
import asyncio
import sys
import uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'connector'))
from ribbon_connector import Bridge, CONFIG
from musegadget import config

async def main():
    bridge=Bridge(config.load_json(CONFIG));chat=str(uuid.uuid4());job=str(uuid.uuid4())
    await bridge.post('/api/chats',{'id':chat,'title':'클라우드 실행 환경 확인'})
    default_message = (
      '리본 연결 프로그램을 내 PC 대신 네가 가진 개인 클라우드 컴퓨터에서 실행할 수 있는지 조사 중이야. '
      '가젯이나 내 PC에는 명령을 보내지 말고, 네 자체 클라우드 터미널 도구가 있으면 실제로 '
      '`uname -s; id -u; command -v python3; python3 --version; command -v git; command -v systemctl; ps -p 1 -o comm=` '
      '를 실행하고 결과를 알려줘. 도구가 없으면 없다고 답해. 비밀번호나 토큰, 환경변수는 읽거나 출력하지 마. '
      '서비스를 설치하거나 시작하지 말고, 현재 클라우드에서 사용자 프로그램을 백그라운드로 실행하는 것이 가능한지만 확인해줘.')
    message = sys.stdin.read().strip() if '--stdin' in sys.argv else default_message
    await bridge.post('/api/jobs',{'id':job,'chat_id':chat,'message':message})
    for _ in range(180):
        state=await bridge.get('/api/state?chat='+chat);current=state['jobs'][0]
        if current['status']=='error':raise SystemExit('Inspection could not finish.')
        if current['status']=='done':
            replies={e['payload']['message_id']:e['payload']['text'] for e in state['events'] if e['kind']=='reply'}
            print('\n'.join(replies.values()));return
        await asyncio.sleep(1)
    raise SystemExit('Inspection pending; no automatic resend.')

asyncio.run(main())

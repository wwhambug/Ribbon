// Private service credentials are accepted on hidden stdin and held in memory.
import {spawnSync} from 'node:child_process';
if(process.stdin.isTTY)process.stdin.setRawMode(true);
process.stdin.setEncoding('utf8');
process.stderr.write('Ready for cloud proof JSON on stdin (input is hidden).\n');
let input='';
process.stdin.on('data',chunk=>{
  input+=chunk;if(input.includes('\u0003')||input.length>20000)process.exit(1);
  if(!input.includes('\n')&&!input.includes('\r'))return;
  if(process.stdin.isTTY)process.stdin.setRawMode(false);process.stdin.pause();
  let settings;try{settings=JSON.parse(input)}catch{process.exit(1)}
  verify(settings).then(()=>process.exit(0)).catch(error=>{console.error(error.message);process.exit(1)});
});
function wslStopped(){
  const result=spawnSync('wsl.exe',['--list','--verbose'],{encoding:'utf8',env:{...process.env,WSL_UTF8:'1'}});
  const output=result.stdout.replaceAll('\0','');
  if(result.status!==0||!/Ribbon-Ubuntu\s+Stopped\s+2/.test(output))throw Error('Could not verify Ribbon-Ubuntu is stopped. No request sent.');
}
async function verify(settings){
  const heartbeatOnly=process.argv.includes('--heartbeat-only');
  if(!heartbeatOnly)wslStopped();
  const origin=new URL(settings.site_url);
  if(origin.protocol!=='https:')throw Error('HTTPS required.');
  async function call(path,data){
    const response=await fetch(new URL(path,origin),{method:data?'POST':'GET',redirect:'error',
      headers:{'Content-Type':'application/json','X-Ribbon-Token':settings.bridge_token,'OAI-Sites-Authorization':'Bearer '+settings.site_bearer},
      ...(data?{body:JSON.stringify(data)}:{}),signal:AbortSignal.timeout(25000)});
    if(!response.ok)throw Error('Private Site request failed: '+response.status);
    return response.json();
  }
  let ready=false;
  for(let i=0;i<20;i++){
    const state=await call('/api/state');
    if(state.runner.online&&state.runner.location==='cloud'){ready=true;break}
    await new Promise(resolve=>setTimeout(resolve,2000));
  }
  if(!ready)throw Error('Cloud connector heartbeat not confirmed; no message sent.');
  if(heartbeatOnly){console.log('CLOUD_HEARTBEAT_CONFIRMED=True');return}
  const chat=crypto.randomUUID(),id=crypto.randomUUID(),expected='RIBBON_CLOUD_'+crypto.randomUUID().slice(0,8);
  await call('/api/chats',{id:chat,title:'Linux 종료 후 클라우드 확인'});
  const started=Date.now();
  await call('/api/jobs',{id,chat_id:chat,message:'클라우드 연결 확인이야. 도구를 쓰지 말고 정확히 '+expected+' 한 줄만 답해 줘.'});
  for(let i=0;i<100;i++){
    const state=await call('/api/state?chat='+chat),job=state.jobs.find(j=>j.id===id);
    if(job?.status==='error')throw Error('Cloud task failed. No automatic resend.');
    if(job?.status==='done'){
      const replies=state.events.filter(e=>e.kind==='reply').map(e=>e.payload.text.trim());
      if(!replies.includes(expected))throw Error('Cloud reply did not match the probe.');
      wslStopped();
      console.log(JSON.stringify({cloud_proof:true,wsl_stopped:true,runner_location:state.runner.location,
        exact_reply:expected,elapsed_seconds:Math.round((Date.now()-started)/10)/100}));return;
    }
    await new Promise(resolve=>setTimeout(resolve,1000));
  }
  throw Error('Cloud reply timed out. No automatic resend.');
}

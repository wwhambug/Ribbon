import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Script} from 'node:vm';
import worker from '../worker/index.js';
import {database} from '../scripts/local-db.mjs';

function fixture(){
  const env={DB:database(),BRIDGE_TOKEN:'test-bridge-token'};
  async function request(path,data,{bridge=false,anonymous=false,origin='https://ribbon.test'}={}){
    const headers={'Content-Type':'application/json',Origin:origin};
    if(bridge)headers['x-ribbon-token']=env.BRIDGE_TOKEN;
    else if(!anonymous)headers['oai-authenticated-user-id']='owner';
    return worker.fetch(new Request('https://ribbon.test'+path,{method:data?'POST':'GET',headers,...(data?{body:JSON.stringify(data)}:{})}),env);
  }
  return {env,request};
}
test('private API rejects unauthenticated and cross-origin writes; connector requires its secret',async()=>{
  const {request}=fixture();
  assert.equal((await request('/api/state',null,{anonymous:true})).status,401);
  assert.equal((await request('/bridge/next',{})).status,401);
  assert.equal((await request('/api/chats',{id:crypto.randomUUID()},{origin:'https://other.test'})).status,403);
});
test('offline connector rejects sends instead of silently charging later',async()=>{
  const {request}=fixture();const chat=crypto.randomUUID();
  await request('/api/chats',{id:chat});
  assert.equal((await request('/api/jobs',{id:crypto.randomUUID(),chat_id:chat,message:'hello'})).status,503);
});
test('one idempotent request, exclusive lease, bounded reply, history and saved events',async()=>{
  const {request}=fixture();const chat=crypto.randomUUID(),id=crypto.randomUUID();
  await request('/api/chats',{id:chat});
  await request('/bridge/next',{location:'local'},{bridge:true});
  const data={id,chat_id:chat,message:'first message'};
  assert.equal((await request('/api/jobs',data)).status,201);
  assert.equal((await request('/api/jobs',data)).status,200);
  assert.equal((await request('/api/jobs',{...data,id:crypto.randomUUID()})).status,409);
  const {job}=await (await request('/bridge/next',{},{bridge:true})).json();
  assert.equal(job.id,id);
  assert.equal((await (await request('/bridge/next',{},{bridge:true})).json()).job,null);
  assert.equal((await request('/bridge/event',{id,lease:crypto.randomUUID(),kind:'done'},{bridge:true})).status,409);
  assert.equal((await request('/bridge/event',{id,lease:job.lease,kind:'done'},{bridge:true})).status,400);
  for(const [kind,payload] of [['ack',{}],['reply',{message_id:'a',text:'answer',done:true}],['done',{}]])assert.equal((await request('/bridge/event',{id,lease:job.lease,kind,payload},{bridge:true})).status,200);
  const state=await (await request('/api/state?chat='+chat)).json();
  assert.equal(state.jobs[0].status,'done');assert.equal(state.events.at(-1).kind,'done');
  assert.equal(JSON.stringify(state).includes(job.lease),false);
  assert.equal(JSON.stringify(state).includes('test-bridge-token'),false);
  const id2=crypto.randomUUID();await request('/api/jobs',{id:id2,chat_id:chat,message:'next'});
  const next=await (await request('/bridge/next',{},{bridge:true})).json();
  assert.deepEqual(next.job.history,[{user:'first message',assistant:'answer'}]);
});
test('lost leased work becomes an error and is never automatically requeued',async()=>{
  const {request,env}=fixture();const chat=crypto.randomUUID(),id=crypto.randomUUID();
  await request('/api/chats',{id:chat});await request('/bridge/next',{},{bridge:true});
  await request('/api/jobs',{id,chat_id:chat,message:'one send'});await request('/bridge/next',{},{bridge:true});
  env.DB.sqlite.prepare('UPDATE jobs SET lease_until=0 WHERE id=?').run(id);
  const state=await (await request('/api/state?chat='+chat)).json();
  assert.equal(state.jobs[0].status,'error');
  assert.equal((await (await request('/bridge/next',{},{bridge:true})).json()).job,null);
});
test('page script parses and no private credential is included in HTML',async()=>{
  const {env}=fixture();const response=await worker.fetch(new Request('https://ribbon.test'),env);
  const html=await response.text();assert.equal(response.status,200);
  const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];new Script(script);
  assert.equal(html.includes(env.BRIDGE_TOKEN),false);
  assert.ok(html.includes('내 PC에서 실행 중'));
});

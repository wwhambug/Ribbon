import http from 'node:http';
import worker from '../worker/index.js';
import {database} from './local-db.mjs';
import {mkdirSync} from 'node:fs';
mkdirSync('.local',{recursive:true});
const env={DB:database('.local/ribbon.sqlite'),BRIDGE_TOKEN:process.env.BRIDGE_TOKEN||'local-development-only'};
const port=Number(process.env.PORT||4173);
http.createServer(async(req,res)=>{
  try{
    const chunks=[];for await(const chunk of req)chunks.push(chunk);
    const headers=new Headers(req.headers);
    // Loopback-only preview identity; never used by the hosted Worker.
    headers.set('oai-authenticated-user-id','local-preview');
    const request=new Request('http://127.0.0.1:'+port+req.url,{method:req.method,headers,
      ...(req.method==='GET'||req.method==='HEAD'?{}:{body:Buffer.concat(chunks)})});
    const response=await worker.fetch(request,env);
    res.writeHead(response.status,Object.fromEntries(response.headers));
    res.end(Buffer.from(await response.arrayBuffer()));
  }catch(error){console.error(error.message);res.writeHead(500);res.end('Preview error')}
}).listen(port,'127.0.0.1',()=>console.log('Ribbon preview: http://127.0.0.1:'+port));

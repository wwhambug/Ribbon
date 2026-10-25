// The terminal hides this one-line input; secrets travel only through stdin.
import {spawnSync} from 'node:child_process';
if(process.stdin.isTTY)process.stdin.setRawMode(true);
process.stdin.setEncoding('utf8');
process.stderr.write('Ready for private bridge JSON on stdin (input is hidden).\n');
let input='';
process.stdin.on('data',chunk=>{
  input+=chunk;
  if(input.includes('\u0003'))process.exit(130);
  if(input.length>20000)process.exit(1);
  if(!input.includes('\n')&&!input.includes('\r'))return;
  if(process.stdin.isTTY)process.stdin.setRawMode(false);
  process.stdin.pause();
  try{JSON.parse(input)}catch{console.error('Invalid input');process.exit(1)}
  const result=spawnSync('wsl.exe',['-d','Ribbon-Ubuntu','-u','root','--exec','/opt/ribbon/venv/bin/python','/mnt/c/Users/hambu/Documents/Codex/2026-10-25/new-chat/Ribbon/scripts/Store-BridgeConfig.py'],{input,encoding:'utf8',env:{...process.env,WSL_UTF8:'1'}});
  if(result.status!==0){console.error('Unable to save private bridge configuration.');process.exit(1)}
  console.log('Private bridge configured.');process.exit(0);
});

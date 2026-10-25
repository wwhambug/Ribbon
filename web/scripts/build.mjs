import {mkdirSync,copyFileSync,cpSync} from 'node:fs';
import {resolve} from 'node:path';
const root=resolve('.');
mkdirSync(resolve(root,'dist/server'),{recursive:true});
mkdirSync(resolve(root,'dist/.openai'),{recursive:true});
copyFileSync(resolve(root,'worker/index.js'),resolve(root,'dist/server/index.js'));
copyFileSync(resolve(root,'.openai/hosting.json'),resolve(root,'dist/.openai/hosting.json'));
cpSync(resolve(root,'drizzle'),resolve(root,'dist/.openai/drizzle'),{recursive:true});
console.log('Built Ribbon Worker and schema migrations.');

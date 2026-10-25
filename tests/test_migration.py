import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'connector/migration.py'
class MigrationTests(unittest.TestCase):
    def test_encrypted_transfer_rejects_tampering_and_preserves_private_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source';source.mkdir();destination=root/'destination';keys=root/'keys'
            values={'identity.json':{'mac':'02:12:34:56:78:90'},'pairing.json':{'access_token':'test-access','refresh_token':'test-refresh'},
                    'ribbon-bridge.json':{'site_url':'https://ribbon.test','site_bearer':'test-bearer','bridge_token':'test-bridge','location':'local'}}
            for name,value in values.items():(source/name).write_text(json.dumps(value))
            (source/'sdk_token').write_text('mgst_'+'A'*43)
            def run(action,state,keydir=keys,input=None,public=None):
                command=[sys.executable,str(SCRIPT),action,'--key-dir',str(keydir)]
                if public:command+=['--public-key',public]
                return subprocess.run(command,input=input,text=True,capture_output=True,env={**os.environ,'MUSEGADGET_STATE_DIR':str(state)})
            key=json.loads(run('keygen',destination).stdout)['recipient_public_key']
            packet=run('export',source,public=key).stdout
            self.assertNotIn('test-refresh',packet);self.assertNotIn('test-bearer',packet)
            changed=json.loads(packet);changed['ciphertext']=('A' if changed['ciphertext'][0]!='A' else 'B')+changed['ciphertext'][1:]
            self.assertNotEqual(run('import',destination,input=json.dumps(changed)).returncode,0)
            self.assertFalse(destination.exists())
            other=root/'wrong-keys';run('keygen',destination,other)
            self.assertNotEqual(run('import',destination,other,input=packet).returncode,0)
            result=run('import',destination,input=packet)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads((destination/'ribbon-bridge.json').read_text())['location'],'cloud')
            self.assertEqual(json.loads((destination/'pairing.json').read_text())['refresh_token'],'test-refresh')
            self.assertFalse((keys/'receiver.key').exists())
            self.assertEqual((destination/'pairing.json').stat().st_mode & 0o777,0o600)
            self.assertEqual(destination.stat().st_mode & 0o777,0o700)
            self.assertNotIn('test-refresh',result.stdout)
            self.assertNotEqual(run('import',destination,input=packet).returncode,0)

if __name__=='__main__':unittest.main()

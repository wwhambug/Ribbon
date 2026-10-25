"""One-time X25519 + HKDF-SHA256 + AES-GCM transfer to the owner's cloud VM.

Only the destination private key decrypts the packet. No secret is printed.
Public keys and encrypted packets may travel through the owner's Muse chat.
"""
import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

CONTEXT=b'ribbon-owner-migration-v1'
def encode(value):return base64.b64encode(value).decode('ascii')
def decode(value):return base64.b64decode(value,validate=True)
def public(key):return key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
def key_for(private, peer):
    return HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=CONTEXT).derive(private.exchange(X25519PublicKey.from_public_bytes(peer)))
def private_write(path, data):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(path.parent,0o700)
    temp=path.with_suffix(path.suffix+'.pending')
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'wb') as output:output.write(data)
    os.chmod(temp,0o600);os.replace(temp,path)
def validate(bundle):
    if set(bundle)!={'identity.json','pairing.json','sdk_token','ribbon-bridge.json'}:raise ValueError('Unexpected state files.')
    if not re.fullmatch(r'[0-9a-f]{2}(:[0-9a-f]{2}){5}',bundle['identity.json'].get('mac','')):raise ValueError('Invalid device identity.')
    if not all(isinstance(bundle['pairing.json'].get(k),str) and bundle['pairing.json'][k] for k in ('access_token','refresh_token')):raise ValueError('Invalid pairing.')
    if not re.fullmatch(r'mgst_[A-Za-z0-9_-]{43}',bundle['sdk_token']):raise ValueError('Invalid SDK token.')
    settings=bundle['ribbon-bridge.json']
    if not settings.get('site_url','').startswith('https://') or settings.get('location')!='cloud':raise ValueError('Invalid destination settings.')
    if not all(settings.get(k) for k in ('site_bearer','bridge_token')):raise ValueError('Missing bridge access.')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['keygen','export','import'])
    parser.add_argument('--public-key')
    parser.add_argument('--key-dir',default='/opt/ribbon/migration')
    args=parser.parse_args()
    keypath=Path(args.key_dir)/'receiver.key'
    if args.action=='keygen':
        if keypath.exists():key=X25519PrivateKey.from_private_bytes(keypath.read_bytes())
        else:
            key=X25519PrivateKey.generate()
            private_write(keypath,key.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption()))
        print(json.dumps({'recipient_public_key':encode(public(key))}));return
    state=Path(os.environ.get('MUSEGADGET_STATE_DIR','/var/lib/musegadget'))
    if args.action=='export':
        recipient=decode(args.public_key)
        if len(recipient)!=32:raise ValueError('Invalid public key length.')
        bundle={name:json.loads((state/name).read_text()) for name in ('identity.json','pairing.json','ribbon-bridge.json')}
        bundle['sdk_token']=(state/'sdk_token').read_text().strip()
        bundle['ribbon-bridge.json']['location']='cloud'
        validate(bundle)
        key=X25519PrivateKey.generate();nonce=os.urandom(12)
        aad=CONTEXT+recipient
        ciphertext=AESGCM(key_for(key,recipient)).encrypt(nonce,json.dumps(bundle).encode(),aad)
        print(json.dumps({'version':1,'recipient_public_key':encode(recipient),
                          'sender_public_key':encode(public(key)),'nonce':encode(nonce),
                          'ciphertext':encode(ciphertext)}));return
    packet=json.loads(sys.stdin.read(65536))
    if packet.get('version')!=1:raise ValueError('Unsupported envelope.')
    key=X25519PrivateKey.from_private_bytes(keypath.read_bytes())
    recipient=public(key)
    if decode(packet['recipient_public_key'])!=recipient:raise ValueError('Not addressed to this destination.')
    plaintext=AESGCM(key_for(key,decode(packet['sender_public_key']))).decrypt(decode(packet['nonce']),decode(packet['ciphertext']),CONTEXT+recipient)
    bundle=json.loads(plaintext);validate(bundle)
    if any((state/name).exists() for name in bundle):raise ValueError('Destination already has state; do not overwrite an active pairing.')
    for name,value in bundle.items():
        private_write(state/name,((value+'\n') if name=='sdk_token' else json.dumps(value)).encode())
    keypath.unlink()
    print('MIGRATION_IMPORTED=True; private state saved; one-time private key removed.')

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('Migration failed: '+type(error).__name__+'. No state contents printed.',file=sys.stderr)
        raise SystemExit(1)

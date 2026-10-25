"""Read a token from stdin and store it privately inside Linux, without echoing it."""
import os
import re
import sys
from pathlib import Path

token = sys.stdin.read().strip()
if not re.fullmatch(r'mgst_[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]', token):
    raise SystemExit('Invalid SDK token format. Copy the complete token and try again.')
state = Path('/var/lib/musegadget')
state.mkdir(mode=0o700, parents=True, exist_ok=True)
os.chmod(state, 0o700)
fd = os.open(state / 'sdk_token', os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as output:
    output.write(token + '\n')
print('SDK token saved privately in Ubuntu.')

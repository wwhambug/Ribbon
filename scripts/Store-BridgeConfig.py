"""Private bridge settings arrive on stdin; never print their contents."""
import json
import sys
from urllib.parse import urlparse
from musegadget import config

settings=json.load(sys.stdin)
url=urlparse(settings['site_url'])
if url.scheme!='https' and not (url.scheme=='http' and url.hostname=='127.0.0.1'):
    raise SystemExit('HTTPS is required.')
if not all(isinstance(settings.get(k),str) and settings[k] for k in ('site_bearer','bridge_token')):
    raise SystemExit('Private service credentials are missing.')
if settings.get('location') not in ('local','cloud'):
    raise SystemExit('Invalid runtime location.')
config.save_json('ribbon-bridge.json',settings)
print('Private bridge settings saved inside Ubuntu.')

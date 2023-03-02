#!/usr/bin/env python3
"""Authenticator script for certbot using the porkbun API.

Example usage:
sudo certbot certonly \
  --agree-tos --non-interactive --register-unsafely-without-email \
  --authenticator manual \
  --preferred-challenges=dns \
  --manual-auth-hook certbot_auth.py \
  --installer nginx \ 
  -d "example.com"

"""

from porkbun import Porkbun, get_config

import os
import time
from pathlib import Path


# FIXME: hard-coded path for now
config_path = str(Path(__file__).parent) + '/config.toml'

# get environment variables
domain = os.environ['CERTBOT_DOMAIN']
certbot_validation = os.environ['CERTBOT_VALIDATION']

print('Domain   : ' + domain)
print('Challenge: ' + certbot_validation)

# update record
porkbun = Porkbun(**get_config(config_path))
responses = porkbun.update_record(
    domain=domain,
    name=f'_acme-challenge',
    type_='TXT',
    content=certbot_validation,
    ttl='120') # tll=120, as per the certbot wiki
print(f'Deletion response:\n{responses[0]}')
print(f'Creation response:\n{responses[1]}')

# wait to allow for changes to propagate
print('sleeping ...')
time.sleep(120)

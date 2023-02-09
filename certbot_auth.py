#!/usr/bin/env python3

from porkbun import Porkbun, get_config

import os
from pathlib import Path


# FIXME: hard-coded path for now
config_path = str(Path(__file__).parent) + '/config.toml'

# get environment variables
domain = os.environ['CERTBOT_DOMAIN']
certbot_validation = os.environ['CERTBOT_VALIDATION']

# update record
porkbun = Porkbun(**get_config(config_path))
response = porkbun.update_record(
    domain=domain,
    name=f'_acme-challenge',
    type_='TXT',
    content=certbot_validation,
    ttl='120') # tll=120, as per the certbot wiki

#!/usr/bin/env python3
"""Porkbun API interface 🐷🐖

Porkbun is an amazingly awesome ICANN
accredited domain name registrar.
This is a tool to interface with their
equally amazingly awesome API, 
targeting v3 at the time of writing.

The tool can be used either through the
commandline or as a python libary, and
comes with built-in support for some
common usecases such as handling DDNS
or SSL verification over DNS. Oink! 🐖
"""


from pathlib import Path
import argparse
import requests
import ipaddress
from ipaddress import IPv4Address, IPv6Address
import toml
import json
from typing import Any, Optional, Union, Dict
import logging


DEF_ENDPOINT = 'https://api-ipv4.porkbun.com/api/json/v3'


# Utilities
# -----------------------------------------------------------------------------

def _get_fqdn(subdomain: str, domain: str) -> str:
    return f'{subdomain.lower()}.{domain}'.strip('.')


def _str_to_ip_addr_obj(ip_addr: str) -> Union[IPv4Address, IPv6Address]:
    return ipaddress.ip_address(ip_addr)


def _err(msg, **kwargs) -> None:
    logging.getLogger('porkbun').log(logging.WARN, msg)
    raise SystemExit(kwargs.get('code', 1))


# API
# -----------------------------------------------------------------------------

class Porkbun:
    def __init__(self,
                 api_key: str,
                 secret_api_key: str,
                 endpoint: str = DEF_ENDPOINT):
        self.__api_key = api_key
        self.__secret_api_key = secret_api_key
        self.__endpoint = endpoint
        
    @property
    def endpoint(self) -> str:
        return self.__endpoint
    
    def __authenticate_data(self, data):
        # This is meant to mimick the official porkbun ddns script,
        # we could probably skip including the endpoint and it would
        # still work.
        authenticated_data = {
            'endpoint': self.__endpoint,
            'apikey': self.__api_key,
            'secretapikey': self.__secret_api_key}
        
        filtered_data = {key: value for key, value in data.items() 
                         if key not in authenticated_data}
        
        authenticated_data.update(filtered_data)
        
        return authenticated_data
        
    def api_raw(self, target, data={}) -> requests.Response:
        url = self.endpoint + target
        authenticated_data = self.__authenticate_data(data)
        
        # post request and retrive response text
        response = requests.post(url, json.dumps(authenticated_data))
        return response
    
    def api(self, target, data={}) -> Dict[str, str]:
        response = self.api_raw(target, data)
        
        if not response.status_code == 200:
            _err(f'Fail (code {response.status_code}).\nText: \n{response.text}')
        
        response_json = json.loads(response.text)
        if not isinstance(response_json, dict):
            _err(f'json was not a dict: {response_json}')
        return response_json
    
    def get_public_ip(self) -> Union[IPv4Address, IPv6Address]:
        response = self.api('/ping/')
        return _str_to_ip_addr_obj(response['yourIp'])
    
    def get_records(self, domain: str) -> Any:
        response = self.api('/dns/retrieve/' + domain)
        
        if response['status'] == 'ERROR':
            _err('Failed to get records. '
            f'Make sure you specified the correct domain ({domain}), '
            'and that API access has been enabled for this domain.')
        return response
    
    def create_record(self, 
                          domain: str, 
                          name: str,
                          type_: str,
                          content: str,
                          ttl: Optional[str] = None,
                          prio: Optional[str] = None):
        data = {
            'name': name,
            'type': type_,
            'content': content,
            'ttl': ttl,
            'prio': prio
        }
        data = {k: v for k, v in data.items() if v is not None}
        
        response = self.api('/dns/create/' + domain, data)
        return response
    
    def create_a_aaaa_record(self,
                             domain: str,
                             ip: Union[IPv4Address, IPv6Address],
                             subdomain: str = None):
        name = '' if subdomain is None else subdomain.lower()
        type_ = 'A' if ip.version == 4 else 'AAAA'
        content = ip.exploded
        
        print(f"Creating {type_}-Record for \'{_get_fqdn(name, domain)}\' "
              f"with answer of \'{content}\'")
        
        response = self.create_record(
            domain=domain.lower(),
            name=name,
            type_=type_,
            content=content,
            ttl=300)
        return response
    
    def delete_record(self,
                      domain: str, 
                      id: str) -> Any:
        
        url = '/dns/delete/' + domain + '/' + id
        response = self.api(url)
        return response
    
    def delete_a_aaaa_record(self,
                             domain: str,
                             ip: Union[IPv4Address, IPv6Address],
                             subdomain: str = None) -> None:
        domain = domain.lower()
        subdomain = '' if subdomain is None else subdomain.lower()
        type_='A' if ip.version == 4 else 'AAAA'
        fqdn = _get_fqdn(subdomain, domain)
        
        for record in self.get_records(domain)['records']:
            if record['name'] == fqdn and record['type'] in [type_, 'ALIAS', 'CNAME']:
                print(f"Deleting existing {record['type']}-Record: {record}")
                self.delete_record(domain, record['id'])
                
    def update_a_aaaa_record(self, 
                           domain: str,
                           ip: Union[IPv4Address, IPv6Address],
                           subdomain: str = None) -> None:
        self.delete_a_aaaa_record(domain, ip, subdomain)
        response = self.create_a_aaaa_record(domain, ip, subdomain)
        print(response['status'])


# Main routine
# -----------------------------------------------------------------------------

def get_config(path: str) -> Any:
    config = toml.load(path)
    
    # check required config elements
    config_required = ['secretapikey', 'apikey']
    if not isinstance(config, dict) or \
        any((e not in config) for e in config_required):
        _err(f'all of the following are required in \'{path}\': '
            f'{config_required}')
    
    # set default endpoint
    tmp = {}
    tmp.setdefault('endpoint', DEF_ENDPOINT)
    config.update(tmp)
    
    return config


def main():
    def_config_path = str(Path(__file__).parent) + '/config.toml'
    
    # toplevel parser
    parser = argparse.ArgumentParser(description=__doc__)
    
    # api authentication
    parser.add_argument('--config',
                        default=def_config_path,
                        nargs='?',
                        help='path to toml config file')
    parser.add_argument('--key',
                        nargs='?',
                        help='API key')
    parser.add_argument('--seckey',
                        nargs='?',
                        help='secret API key')
    parser.add_argument('--endpoint',
                        nargs='?',
                        help='API endpoint')
    
    # subparser
    sub_parsers = parser.add_subparsers(
        title='Operating modes',
        description='Select the operating mode',
        dest='mode',
        required=True)
    
    # create the parser for the "ddns" sub-command
    parser_ddns = sub_parsers.add_parser('ddns', help='DDNS updater mode')
    parser_ddns.add_argument(
        'domain', 
        type=str, 
        help='root domain name. must not contain any subdomains')
    parser_ddns.add_argument(
        '--subdomain',
        type=str,
        required=False,
        help='subdomain(s). must not contain a root domain')
    parser_ddns.add_argument(
        '--ip',
        type=str,
        help='IP Address. Skip auto-detection and use this IP for entry',
        required=False)
    
    args = parser.parse_args()
    
    # configure auth
    # --------------
    endpoint = None
    api_key = None
    secret_api_key = None
    
    # apply config
    if args.config is not None:
        config = get_config(args.config)
        endpoint = config['endpoint']
        api_key = config['apikey']
        secret_api_key = config['secretapikey']
    
    # apply args
    if args.endpoint is not None:
        endpoint = args.endpoint
    if args.key is not None:
        api_key = args.key
    if args.seckey is not None:
        secret_api_key = args.seckey
        
    # validate not empty
    if endpoint is None or endpoint == '':
        parser._error('API endpoint must be specified.')
    if api_key is None or api_key == '':
        parser._error('API key must be specified.')
    if secret_api_key is None or secret_api_key == '':
        parser._error('Secret API key must be specified.')

    # set up api
    # ----------
    porkbun = Porkbun(api_key, secret_api_key, endpoint)
    
    # handle mode
    # -----------
    if args.mode == 'ddns':
        # get relevant arguments
        domain = args.domain
        subdomain = args.subdomain
        ip = args.ip

        # get public ip
        if ip is None:
            ip = porkbun.get_public_ip()
        else:
            # transform ip to the correct object
            ip = _str_to_ip_addr_obj(ip)
        
        # perform update
        porkbun.update_a_aaaa_record(domain, ip, subdomain)
    else:
        parser._error(f'Unknown mode: \'{args.mode}\'')


if __name__ == '__main__':
    main()

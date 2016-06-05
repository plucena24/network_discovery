from collections import namedtuple

Root = namedtuple('Root', 'root_node root_parser')
Creds = namedtuple('Creds', 'username password')

root_node = Root('rtr1', 'CiscoBaseParser')
credentials = Creds('user1', 'pass1')

ignore_regex = r'(^NA\-|^SEP|^ACVD|^ACWD|^ACPDC|^AP|WAP|WLC|CMP)'
django_app_name = 'net_system'

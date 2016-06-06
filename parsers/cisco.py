from collections import namedtuple
import re

import xmltodict

from base import BaseParser
from general_functions import parse_uptime
from version_mapping import VERSION_MAPPING

Cmd = namedtuple('Cmd', 'cmd delay')

class CiscoBaseParser(BaseParser):

    @property
    def device_class(self):
        return 'cisco_ios'

    @property
    def discovery_command(self):
        return Cmd('show cdp neigh detail', 5)

    @property
    def neighbor_discover_regex(self):
        '''
        regex to parse output of discovery_command
        looking for:
            device_device
            device_ip
            device_ipv6
            device_model
            local_interface
            device_interface
            device_version
        '''
        return "Device ID: (?P<device_device>[\w\d\_\-\.]+)[\W\w]+?\n"\
           "\s+IP [Aa]ddress: (?P<device_ip>[0-9\.]+)\n" \
           "(?:\s+IPv6 address: (?P<device_ipv6>[a-z0-9\:]+)(?:\s+\(global unicast\)\n)?)?" \
           "[\n\W\w]*?" \
           "Platform:\s*[Cc]isco\s(?P<device_model>[\w\d\-\_\.]+)[\W\w\s]+?\n" \
           "Interface: (?P<local_interface>[A-Za-z0-9/\-]+)" \
           ".*: (?P<device_interface>[A-Za-z0-9/\-]+)\n" \
           "[\n\W\w\S\s]*?" \
           "Version.*\n" \
           "(?P<device_version>[\w\W]+?)\n"

    @property
    def extra_facts_cmds(self):
        return {'version' : Cmd('show version', '2')}

    def normalize_intf_str(self, remote_intf):

        ''' takes the str representation of the
        remote interface for a given CDP device and
        formats it to short notation.

        Example: GigbitEthernet = Gig
        Example: TenGigabitEthernet = Ten
        '''
        INTF_SHORT = re.compile(r'((.*)?Ethernet)')

        interface_mapper = dict(Ethernet='Eth', TenGigabitEthernet='Ten',
            GigabitEthernet='Gig', FastEthernet='Fa')

        short_name = INTF_SHORT.match(remote_intf)
        if short_name:
            return interface_mapper[short_name.group()]

        return remote_intf

    def gather_facts(self):
        '''
        collect additional info about device by sending
        and processing extra_facts_cmds
        '''
        self._gather_facts()

        os_version = self.find_os_version()
        serial_number = self.find_serial_number()
        uptime = self.find_uptime()
        model = self.find_model()

        return dict(os_version=os_version,
                    serial_number=serial_number,
                    uptime=uptime,
                    model=model)

    def find_os_version(self):
        '''
        String in show version will be similar to the following:
        Cisco IOS Software, IOS-XE Software (PPC_LINUX_IOSD-ADVENTERPRISEK9-M), Version 15.2(4)S4, RELEASE SOFTWARE (fc1)
        '''
        match = re.search(r'Cisco IOS Software, (.*)', self.version)
        if match:
            # self.net_device.os_version = match.group(1)
            # print self.net_device.os_version
            # self.net_device.save()
            self.os_version = match.group(1)
            return self.os_version

    def find_serial_number(self):
        '''
        String in show version will be similar to the following:
        Processor board ID FTX10000001
        '''

        match = re.search(r'Processor board ID (.*)', self.version)
        if match:
            # self.net_device.serial_number = match.group(1)
            # print self.net_device.serial_number
            # self.net_device.save()
            self.serial_number = match.group(1)
            return self.serial_number

    def find_uptime(self):
        '''
        String in show version will be similar to the following:
        hostname uptime is 8 weeks, 2 days, 23 hours, 22 minutes
        '''

        match = re.search(r'uptime is (.*)', self.version)
        if match:
            time_str = match.group(1)
            # self.net_device.uptime_seconds = parse_uptime(time_str)
            # print self.net_device.uptime_seconds
            # self.net_device.save()
            self.uptime_seconds = parse_uptime(time_str)
            return self.uptime_seconds

    def find_model(self):
        '''
        String in show version will be similar to the following:
        Cisco CISCO2921/K9 (revision 1.0) with 1007584K/40960K bytes of memory.

        cisco WS-C3850-48T (MIPS) processor with 4194304K bytes of physical
        memory
        '''

        match = re.search(r'.*bytes of (physical )?memory', self.version)
        if match:
            return match.group().split()[1]

class CiscoIosParser(CiscoBaseParser):
    pass

class CiscoNxosParser(CiscoBaseParser):

    @property
    def extra_facts_cmds(self):
        return dict('version' :
                        Cmd('show version | xml | exclude "]]>]]>"', 2),
                    'inventory':
                        Cmd('show inventory | xml | exclude "]]>]]>"', 2))

    @property
    def neighbor_discover_regex(self):
        '''
        regex to parse output of discovery_command
        looking for:
            device_device
            device_ip
            device_ipv6
            device_model
            local_interface
            device_interface
            device_version
        '''
        return "Device ID:(?P<device_name>[\w\d\_\-\.]+)[\W\w]+?\n"\
               "\s+IPv4 [Aa]ddress: (?P<device_ip>[0-9\.]+)\n" \
               "(?:\s+IPv6 [Aa]ddress: (?!fe80)(?P<device_ipv6>[a-z0-9\:]+)\n)?" \
               "[\n\W\w]*?" \
               "Platform:\s*(?P<device_model>[\w\d\-\_\.]+)[\W\w\s]+?\n" \
               "Interface: (?P<local_interface>[A-Za-z0-9/]+)" \
               ".*: (?P<device_interface>[A-Za-z0-9/\-]+)\n" \
               "[\n\W\w\S\s]*?" \
               "Version.*\n" \
               "(?P<device_version>[\w\W]+?)\n"

    @staticmethod
    def find_key(obj, key):
        '''recursive function to find key containing desired key in the XML dict'''
        if key in obj:
            return obj[key]
        for val in obj.itervalues():
            if isinstance(val, dict):
                result = CiscoNxosParser.find_key(val, key)
                if result:
                    return result

    def gather_facts(self):
        self._gather_facts()
        self.prepare_xml_ver_output()
        self.prepare_xml_inv_output()

        os_version = self.find_os_version()
        serial_number = self.find_serial_number()
        uptime = self.find_uptime()
        model = self.find_model()

        return dict(os_version=os_version,
                    serial_number=serial_number,
                    uptime=uptime,
                    model=model)

    def prepare_xml_ver_output(self):
        ''' get the dict with interesting data that is returned from the XML interface of nexus and contains all of the show ver data. To avoid future code breakage where the keys of the  nested dict change, such as the case with 'show inv' between 7k and 5k, using this recursive finder is a better approach for now'''

        xml = xmltodict.parse(self.version)
        try:
            self.xml_version_data = self.find_key(xml, '__readonly__')
        except ExpatError as e:
            print "XML Data Parsing Error", e
            raise ExpatError("Error processing XML document -- {}".format(self.inv_output))

    def prepare_xml_inv_output(self):
        ''' get the list returned from XML output 'show inv | xml'. Nexus 7K returns diff headers than 5K/56K, however they all contained the data stored as a list under the 'ROW_inv' key. The recursive function goes through the set of nested dicts and gets the key we are looking for containing the data.'''

        xml = xmltodict.parse(self.inventory)
        try:
            # 1st elem of list returned holds the chasis-id info
            self.xml_inv_data = self.find_key(xml, 'ROW_inv')[0]
        except ExpatError as e:
            print "XML Data Parsing Error", e
            raise ExpatError("Error processing XML document -- {}".format(self.inv_output))

    def find_os_version(self):
        '''
        Parses the XML dict for the OS Version
        '''
        # self.net_device.os_version = str(self.xml_version_data[u'kickstart_ver_str'])
        # print self.net_device.os_version
        # self.net_device.save()
        self.os_version = str(self.xml_version_data[u'kickstart_ver_str'])
        return self.os_version

    def find_serial_number(self):
        '''
        String in show version will be similar to the following:
        Processor board ID FTX10000001
        '''
        # self.net_device.serial_number = str(self.xml_version_data[u'proc_board_id'])
        # print self.net_device.serial_number
        # self.net_device.save()
        self.serial_number = str(self.xml_version_data[u'proc_board_id'])
        return self.serial_number

    def find_uptime(self):
        '''
        Nexus uptime string only uses days, hours, and minutes. The IOS equivalent
        uses years, and weeks.
        '''
        days = str(self.xml_version_data[u'kern_uptm_days'])
        hours = str(self.xml_version_data[u'kern_uptm_hrs'])
        minutes = str(self.xml_version_data[u'kern_uptm_mins'])

        self.uptime_list = [days, hours, minutes]
        self.uptime_str = "{} days, {} hours, {} minutes".format(*self.uptime_list)
        # self.net_device.uptime_seconds = parse_uptime(self.uptime_str)
        # print self.net_device.uptime_seconds
        # self.net_device.save()
        self.uptime_seconds = parse_uptime(self.uptime_str)
        return self.uptime_seconds

    def find_model(self):
        '''
        Find the chassis model ID.
        Example: N5K-C5596UP
        '''
        self.model = self.xml_inv_data['productid']
        return self.model

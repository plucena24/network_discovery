import netmiko
import re

class BaseParser(object):

    def __init__(self, device_name, credentials):
        self.device_name = device_name
        self.credentials = credentials

    @property
    def device_class(self):
        raise NotImplementedError

    @property
    def discovery_command(self):
        raise NotImplementedError

    @property
    def neighbor_discover_regex(self):
        raise NotImplementedError

    @property
    def extra_facts_cmds(self):
        raise NotImplementedError

    def connect(self):
        self.is_connected = False
        try:
            SSHClass = netmiko.ssh_dispatcher(self.device_class)
            username = self.credentials.username
            password = self.credentials.password

            ssh = SSHClass(ip=self.device_name, username=username, password=password)
            self.conn = ssh
            is_connected = True
        except Exception as e:
            print("failed to connect to device {}, error was {}. Appending it to failed".format(self.device_name, e))
        return self.is_connected

    def disconnect(self):

        try:
            self.conn.disconnect()
            self.is_connected = False
        except Exception as e:
            print('Failed to disconnect from {} - {}'.format(self.device_name, e))

    def discover_neighbors(self):
        '''
        send discovery_command to a device, and find connected
        neighbors
        '''
        neighbors = {}
        cmd, delay = self.discovery_command
        neighbor_output = self.conn.send_command(cmd, delay_factor=delay)
        neighbor_re = re.compile(self.neighbor_discover_regex)
        all_neighbors = neighbor_re.finditer(self.neighbor_output)
        all_neighbors = [n.groupdict() for n in all_neighbors if n]
        all_neighbors = self.normalize_neighbors(all_neighbors)

        for neighbor in all_neighbors:

            if not neighbor:
                continue

            for version, details in VERSION_MAPPING.items():
                if version in neighbor['remote_version']:
                    neighbor['remote_class'] = details['device_class']
                    neighbor['remote_vendor'] = details['device_vendor']
                    break
            else:
                # default to cisco_ios if no match found
                neighbor['remote_class'] = 'cisco_ios'
                neighbor['remote_vendor'] = 'Cisco'

            local_intf = neighbor['local_interface']

            if local_intf:
                # local_intf will be out key - don't need it anymore
                neighbor.pop('local_interface')
                neighbors[local_intf] = neighbor

        return neighbors

    def normalize_neighbors(self, neighbors):
        '''
        normalize local/remote interfaces from CDP/LLDP
        '''
        for neighbor in neighbors:
            for key in ['device_interface', 'local_interface']:
                neighbor[key] = self.normalize_intf_str(neighbor[key])

    def normalize_intf_str(self, remote_intf):

        raise NotImplementedError

    def _gather_facts(self):

        if not self.conn or not self.is_connected:
            if not self.connect():
                raise RuntimeError('Could not connect!')

        for key, cmd in self.extra_facts_cmds.items():
            command = cmd.command
            delay = cmd.delay
            self.key = self.conn.send_command(command, delay_factor=delay)

    def gather_facts(self):

        raise NotImplementedError

    def find_os_version(self):

        raise NotImplementedError

    def find_serial_number(self):

        raise NotImplementedError

    def find_uptime(self):

        raise NotImplementedError

    def find_model(self):

        raise NotImplementedError

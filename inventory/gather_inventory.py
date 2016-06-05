''' Crawls the network using Breadth First Search algorithm pattern, by first starting with a manually entered root node, and then building an adjacency list based of the neighbors of the root, and the neighbors of the neighbors of the root, etc.

    Besides getting each device's neighbors, we get some data about each
    device such as version and uptime, which gets saved on the backend
    database.

    During execution, a list of 'failed' nodes is collected. This includes
    nodes to which an SSH session was not able to get established. This may
    include devices that show up via CDP but are not managable using
    the provided credentials. This file is saved to disk for later processing.

    The adjacency list built during this process is also saved to disk for
    further processing. A potential use-case is to prune old devices from the
    database, by comparing active nodes in an area of the network (HOC devices
    for example) which are in the adjacency list, to HOC devices currently
    saved in the database. Anything in the database that is not in the
    adjacency_list for the corresponding section of the network should be
    deleted.


'''
import netmiko
import sys
import django
from collections import deque
from multiprocessing.dummy import Pool as ThreadPool
import pprint
import os
import traceback
import sys
from xml.parsers.expat import ExpatError
from .parsers import cisco
import datetime

# hack to dynamically get correct import path
django_app = sys.path[config.django_app_name]
from django_app.models import NetworkDevice, Credentials
django.setup()

### Used to fix Django setup issue ###
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
### Used to fix Django setup issue ###

def save_node_to_db(dev_facts):
    try:
        new_dev, new = NetworkDevice.objects.update_or_create(
            device_name   = dev_facts['device_name'],
            defaults      = dict(
                ip_address       = dev_facts['ip_address'],
                ipv6_address     = dev_facts['ipv6_address'],
                device_class     = dev_facts['device_class'],
                model            = dev_facts['device_model'],
                serial_number    = dev_facts['serial_number'],
                os_version       = dev_facts['os_verion'],
                uptime_seconds   = dev_facts['uptime'],
                credentials      = creds,
                ssh_port         = config.default_ssh_port,
                vendor           = dev_facts['device_vendor'],
                domain           = config.device_domain,
                )
             )

    except Exception as e:
        print("Error creating device on DJANGO database! for device {}. Error was {}".format(dev_facts['device_name'], e))
        return None

    return new

def save_creds_to_db(creds):
    new_creds, new = Credentials.objects.update_or_create(
        username=creds.username,
        password=creds.password)

def get_root_neighbors(device):
    try:
        parser = class_mapping.get(device.device_class)
        if not parser:
            raise RuntimeError('No parser found for {}'.format(device))
        device_obj = parser(device.device_name, config.credentials)
        if device_obj.connect():
            neighbors = device_obj.get_neighbors()
            device_obj.disconnect()
            return neighbors
    except Exception as e:
        print("****{}**** failed connecting to root. Error ****{}****".format(device.device_name, e))
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print(repr(traceback.extract_tb(exc_traceback)))

    finally:
        if device_obj.is_connected:
            device_obj.disconnect()

def get_neighbors(device):
    '''
    establish an ssh session to a networking device and return the neighbors
    detected via CDP

    returns the device visited, plus its neighbors
    '''
    global failed

    neighbors, device_facts = None, None
    device_name = device['device_name']

    try:
        parser = class_mapping.get(device['device_class'])
        if not parser:
            raise RuntimeError('No parser found for {}'.format(device))
        device_obj = parser(device_name, config.credentials)
        if device_obj.connect():
            neighbors = device_obj.get_neighbors()
            device_facts = device_obj.get_facts()
            device_obj.disconnect()

    except Exception as e:
        print("****{}**** failed connecting to root. Error ****{}****".format(device_name, e))
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print(repr(traceback.extract_tb(exc_traceback)))
        failed.append(device_name)


    finally:

        if device_obj.is_connected:
            device_obj.disconnect()
        if device_facts:
            device.update(device_facts)
        saved = save_node_to_db(device)

        print('Saved new device to database - {}'.format(device))
        return device_name,  neighbors


# define data structures to be used
queue, failed, visited = set(), list(), list()

# credentials for devices needs to be in global scope to allow multiprocessing to use it.
if not config.credentials:
    raise RuntimeError('Must provide valid credentials to start!')

save_creds_to_db(config.credentials)
creds = Credentials.objects.get(username=config.credentials.username)
class_mapping = {'cisco_ios': cisco.CiscoBaseParser,
           'cisco_nxos': cisco.CiscoNxosParser}

def main():

    root_node = config.root_node
    if not root_node:
        raise RuntimeError('Must provide a valid root node!')

    filter_re = None
    if config.ignore_regex:
        filter_re = re.compile(config.ignore_regex)

    def bool_logic(node):

        node_name = node['device_name']

        if filter_re:
            names_bool = lambda x: filter_re.search(x) is None

            return bool(node_name not in visited and names_bool(node_name)) and (node_name not in failed and names_bool(node_name))

        return bool(node_name not in visited and node_name not in failed)

    root_neighbors = get_root_neighbors(root_node)

    # begin building adj list
    neighbor_adj_list = dict()
    neighbor_adj_list[root_node.device_name] = root_neighbors

    # add the root's neighbors to the queue
    queue.update(neigh for neigh in root_neighbors.values())

    pool = ThreadPool(processes=16)

    while queue:

        nodes_to_process = set(filter(bool_logic, queue))
        # pop all of the nodes from the queue and put them into a processing deque. Then filter what devices need to actually be processed.
        # we do this so that we remove everything from the queue at this point and give all "workable" devices to the thread pool.
        queue.clear()


        print('#' * 80)
        print()
        print()
        print(len(nodes_to_process))
        print()
        print()
        print('#' * 80)
        print()
        print()
        print(nodes_to_process)
        print()
        print()
        print('#' * 80)

        pool_results = [pool.apply_async(get_neighbors, args=(dev,)) for dev in nodes_to_process]

        for result in pool_results:
            pool_data = result.get()
            # if ssh session failed, function returns back None
            if not pool_data:
                continue

            node, neighbors = pool_data

            visited.append(node)
            # add node and all of its discovered neighbors to the adj_list
            neighbor_adj_list[node] = neighbors
            # prune off devices that we don't want to visit before adding discovered neighbors into the queue
            for dev in neighbors.values():
                node = dev['device_name']
                if bool_logic(node):
                    queue.add(node)

    return neighbor_adj_list, failed


if __name__ == '__main__':

    date = str(datetime.datetime.today()).split()[0]

    adj_list, failed = main()
    file_name_fmt = '{date}_{type}.json'

    with open(file_name_fmt.format(date=date, type='adj_list'), 'w') as fh:
        fh.write(json.dumps(adj_list))

    with open(file_name_fmt.format(date=date, type='failed_list'), 'w') as fh:
        fh.write(json.dumps(failed))

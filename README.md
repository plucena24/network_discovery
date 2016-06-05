# network_discovery
Network Discovery tool - crawls the network, discovering devices and adding them to an inventory database.


##################################################
# Intro
#

`network_discovery` is a tool that facilitates automated discovery of a network
by "crawling" the network using Breadth First Search. This makes adding all discoverable devices in a network to a database/ORM in a standard way trivial.

After the database is populated, you can then more easily script against the network using tools like Ansible, or just straight Python, by using the database as a basis to your inventory. Besides populating the database, network_discovery outputs an adjacency_list of all discovered nodes as a JSON blob. This is basically a graph of how your network is connected - and gives you additional info about each link, such as interface names, ip/ipv6 addresses, device name/model and os_version. This data can be piped into graphing tools, or can be used a simple way to detect topology changes (diff today's node graph with yesterday's)

#
# Intro
##################################################


##################################################
# Overview
#

From a high level, network_discovery performs the following actions:

Given a root_node and a username/password which will work on all discoverable devices, we SSH to the root_node and begin the discovery process. The discovery process starts by discovering all devices conncted to the root_node, by using the provided discovery mechanism for the root_node (CDP/LLDP/etc).

This discovery mechanism also provides additional info about each connected neighbor that is extracted, such as:

    - device_name
    - ip_address
    - ipv6_address
    - device_interface
    - model
    - os_version

After extracting this data about each discovered neighbor of the root, we place
all **valid** discovered neighbors into a queue. This queue provides a way for the algorithm to track the progress of the overall network discovery process.

Valid neighbors are those that we wish to be discovered, and that pass certain criteria. To "blacklist" devices from being discovered, the "ignore_regex" parameter is consulted from the provided configuration. A positive regex match against a connected device's hostname will prevent it from being explored/discovered (as it will not get added to the queue). This is useful for blacklisting devices that show up via CDP/LLDP - such as IP Phones, Wireless APs, and servers. Usually such devices are not part of the network topology as they are mainly endpoints, and are managed by other teams which don't appreciate unauthorized login attempts =)

At this point, we have the root's valid neighbors in the queue. We begin processing these devices by visiting each one (visiting in this text means connecting via SSH), and discovering its connected neighbors. The following sequence of events occurs while we "visit" each device.

    - remove the device being visited from the queue
    - discover the connected neighbors as per the device's discovery mechanism
    - find local facts about the device, such as serial_number, uptime, and other available facts. Like the discovery mechanism, this is also configurable per device type.
    - add all **valid** discovered neighbors to the queue
    - save the device being visited, and facts found about this device, into the database
    - if no errors have occured by this point, add the device being visited to the 'visited' list
    - if we did run into errors - for example, if we failed to SSH to this device, or if there are other unhandled exceptions - this device will be added to the 'failed' list instead

Notice that we are adding all devices we need to "visit/explore" into the queue. As we visit each device in the queue, we remove it. The discovery process finishes when the queue is empty. After we visit a device, we add it to either the "visited" or "failed" list.

Additionally, in order to get added into the queue, the following conditions must pass:

    - The device is not blacklisted via "ignore_regex"
    - The device has not previously failed
    - The device has not already been visited

#
# Overview
##################################################

​##################################################
# Requirements for initial discovery of network
#

- All network devices that are to be discovered must have SSH enabled.
- Initially, you must be able to log into all devices that are to be discovered using a single username/password. This user account must be able to SSH into a device and run the following commands:
   - show cdp/lldp neighbors detail (or the provided discovery command)
   - show version/inventory (or the provided extra facts commands)

No other access rights or privileges are needed for this account. This account is needed to facilitate initial discovery, where all neighbors of a given device (as per CDP/LLDP) are discovered.

- These credentials should preferably be stored in the database. Otherwise, they would need to be provided in the program's config file.

- The hostname configured on each device must be resolvable from the machine running the program. This program attempts to connect to discovered neighbors via the hostname as per CDP/LLDP. This could be changed at a later time, but for now this keeps the discovery logic simple.

- Must provide a root node from which to start the discovery process. Ideally this node should be well connected (core switch for example). Must also provide the root_node type ('cisco_ios', 'cisco_nxos', 'arista_eos'...etc)

- If there are devices in the network that show up in CDP/LLDP outputs but are not to be explored (IP phones, Wireless APs, ESXi hosts, etc), you must provide means to identify said devices so that they are ignored.
   - This "blacklist" can be provided as a regex as part of the config file
   - For example, "WAP\d|PHONE\d" would match any device who's hostname contains either WAP followed by a digit or PHONE followed by a digit. A successful match will prevent the device from being explored.

- Parsers for Cisco IOS and NXOS devices have been provided with the code base. This means that a network consisting of all Cisco devices will be discoverable without writing any further code. To support other vendors or device types, you must provide a parser. To add your own parser, you can inherit from the BaseParser class in inventory/parsers/base.py, and override the methods that differ for the platform you wish to support. Look at CiscoBaseParser in inventory/parsers/cisco.py for an example.

The most important methods are:

   - discovery_command - what cmd do we need to run to look at connected neighbors - for Cisco its 'show cdp neighbor detail')
   - discover_neighbors - after getting the output of executing the discovery_command, how can we parse it to get details about the connected neighbors? This method should return a dictionary with keys containing the local interfaces of the device. Each key (local interface) should have a dictionary as a value with the connected device's info. :

{"Eth1/1": {"device_name": "router1", "ip_address": "1.1.1.1", "ipv6_address": "2001::1", "device_model": "N9K111", "remote_interface": "Eth9/1", "os_version": "Cisco Nexus NXOS 6.3.1K9123"},

"Eth1/2": {"device_name": "router2", "ip_address": "2.2.2.2", "ipv6_address": "2001::2", "model": "N9K222", "remote_interface": "Eth9/1", "os_version": "Cisco Nexus NXOS 6.3.1K9123"}

... etc

If you do not wish to provide further implementation of other discovery methods, which discover even more facts about a device such as serial numbers, uptime, and other stuff not seen in CDP/LLDP, then simply override the corresponding method and just return None instead of providing an implementation.

#
# Done with Requirements
##################################################

##################################################
# Setup instructions
#

- install python
- install pip
    $wget https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=3&cad=rja&uact=8&ved=0ahUKEwi9mdeIt_PLAhWHloMKHSCZDnMQFgguMAI&url=https%3A%2F%2Fbootstrap.pypa.io%2Fget-pip.py&usg=AFQjCNE8Fo9j_sgo1hBzEoUT39H85hFDrg
    $ <python_version> get-pip.py
    - install virtualenv
        $ <python_version> -m pip install virtualenv
- create virtualenv
    $ virtualenv -p <python_version> $VIRTUAL_ENV_NAME
- install required tools
    $ sudo apt-get install python-setuptools python-dev build-essential
- go into virtualenv
    $ source ~/network_automation/bin/activate
    - install dependencies
      $ <python_version> -m pip install -r requirements.txt

# Setting up Django
- Create django project
  - go into virtualenv
    source ~/$VIRTUAL_ENV_NAME/bin/activate
  - all previous requirements must have been installed in virtualenv (requirements.txt)
    - make sure django is installed in virtualenv
    $ python -c 'import django; print(django.__file__)'
  - create project
    $ django-admin startproject $PROJECT_NAME
  - create app inside $PROJECT_NAME
    $ python manage.py startapp $APP_NAME
  - start initiall db migration
    $ python manage.py migrate
  - Replace models.py in the django app with the models.py file included in db_models/models.py
  - Add app name to settings.py
  - Run makemigrations
    $ python manage.py makemigrations $APP_NAME
  - re-run the migration
    $ python manage.py migrate

  - add a .pth file under the virtualenv's site-packages with the absolute path to the code directory

  - Add enviroment variables for settings
    $ export DJANGO_SETTINGS_MODULE=$PROJECT_NAME.settings
    to make this permanent, you can modify the 'activate' virtualenv script and add this same line there. This way, everytime you activate the virtualenv, these env variables get added automatically.

#
# Done with Setup instructions
##################################################

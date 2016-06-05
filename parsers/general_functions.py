from itertools import groupby
from operator import itemgetter

# create  a dictionary to store the time value denominations and their respective seconds
# some entries might be 'weeks' and 'week' because of the way data is input, the uptime string may say '2 weeks' or '1 week'
# so instead of storing 'week' and 'weeks', we can just store the character 'w'.

def parse_uptime(uptime_str):

    denoms = {}; 
    denoms['w'] = 604800;
    denoms['d'] = 86400;
    denoms['h'] = 60 * 60;
    denoms['m'] = 60;
    denoms['y'] = 52 * denoms['w'];

    # uptime4 = 'rtr1 uptime is 5 years, 18 weeks, 8 hours, 23 minutes'
    uptime_dict = {}  # dictionary to store the uptime of each router in seconds
    uptime_fields = uptime_str.split(' ')
             
	#However, incrementing by 2 allows us to skip the pairs such as weeks 4,   days 2, etc.
      
    uptime_seconds = sum(int(uptime_fields[i]) * denoms[uptime_fields[i+1][0]] for i in range(0, len(uptime_fields)-1,2))

    return uptime_seconds


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in xrange(0, len(seq), size))

def get_intf_range(int_list, chunk_size = 5):
    '''
    Generate interface_range string for Cisco devices. 
    Arguments - list of interfaces
        ['interface Gig0/1', 'interface Gig0/2', 'interface Gig0/3', 'interface Gig0/5', 'interface Gig0/6', 'interface Gig0/8']

    return a range - > 'interface range Gig0/1 - 3, Gig0/5 - 6, Gig0/8'
    '''

    ranges = list()
    for key, item in groupby(enumerate(int_list), key=lambda (indx, val) : indx - int(val.split("/")[-1])):
        ranges.append(map(itemgetter(1), item))

    # ranges will be a list of lists with contiguous interfaces grouped
    # [['interface Gig0/1', 'interface Gig0/2', 'interface Gig0/3'], ['interface Gig0/5', 'interface Gig0/6'], 'interface Gig0/8']
    if (len(ranges) == 1) and (len(ranges[0]) == 1):
        return "interface range " + "".join(*ranges)


    # crazy way to accomplish the same thing in 1 line =) 
    # range_list = ", ".join([" - ".join(elem) if type(elem) == tuple else elem for elem in [(n[0].split()[-1], n[-1].split()[-1][-1]) if len(n) > 1 else n[0].split()[-1] for n in ranges]])
    range_list = [(n[0].split()[-1], n[-1].split("/")[-1]) if len(n) > 1 else n[0].split()[-1] for n in ranges]


    # get chunks of interface ranges based on a max of 5 ranges for Cisco IOS
    range_blocks = [block for block in chunker(range_list, chunk_size)]

    interface_ranges = list()

    # if the list is longer than 5 items, this will create multiple interface range strings
    # if the list is -> [['Ten1/1', 'Ten1/5', 'Ten1/8', ('Ten1/10', '11'), 'Ten1/13'], ['Ten1/15', 'Ten1/17', 'Ten1/19']]
    # there may be tuples within each sub-list indicating a range. These are joined with the " - " while joining everything else 
    # with the ","
    for elem in range_blocks:
        interface_ranges.append("interface range " + ", ".join((" - ").join(item) if type(item) == tuple else item for item in elem))

    return interface_ranges

test_list1 = ['Gig1/1']

test_list = ['GigabitEthernet9/1', 'GigabitEthernet9/2', 'GigabitEthernet9/3', 'GigabitEthernet9/4',
 'GigabitEthernet9/5', 'GigabitEthernet9/6', 'GigabitEthernet9/7', 'GigabitEthernet9/8', 
 'GigabitEthernet9/9', 'GigabitEthernet9/10', 'GigabitEthernet9/11', 'GigabitEthernet9/12', 
 'GigabitEthernet9/13', 'GigabitEthernet9/14', 'GigabitEthernet9/15', 'GigabitEthernet9/16', 
 'GigabitEthernet9/17', 'GigabitEthernet9/18', 'GigabitEthernet9/19', 'GigabitEthernet9/20', 
 'GigabitEthernet9/21', 'GigabitEthernet9/22', 'GigabitEthernet9/23', 'GigabitEthernet9/24',
 'GigabitEthernet9/25', 'GigabitEthernet9/26', 'GigabitEthernet9/27', 'GigabitEthernet9/28', 
 'GigabitEthernet9/29', 'GigabitEthernet9/30', 'GigabitEthernet9/31', 'GigabitEthernet9/32', 
 'GigabitEthernet9/33', 'GigabitEthernet9/34', 'GigabitEthernet9/35', 'GigabitEthernet9/36', 
 'GigabitEthernet9/37', 'GigabitEthernet9/38', 'GigabitEthernet9/39', 'GigabitEthernet9/40', 
 'GigabitEthernet9/41', 'GigabitEthernet9/42', 'GigabitEthernet9/43', 'GigabitEthernet9/44', 
 'GigabitEthernet9/45', 'GigabitEthernet9/46', 'GigabitEthernet9/47', 'GigabitEthernet9/48']

test_list2 = ['GigabitEthernet9/1', 'GigabitEthernet9/2', 'GigabitEthernet9/3', 'GigabitEthernet9/4',
 'GigabitEthernet9/5', 'GigabitEthernet9/6', 'GigabitEthernet9/7', 'GigabitEthernet9/8', 'GigabitEthernet10/1', 'GigabitEthernet10/2', 'GigabitEthernet10/3', 'GigabitEthernet10/4']

# print get_intf_range(['interface Gig0/1', 'interface Gig0/2', 'interface Gig0/3', 'interface Gig0/5', 'interface Gig0/6', 'interface Gig0/8', 'interface Gig0/9', 'interface Gig0/10', 'interface Gig0/11', 'interface Gig0/12'])
# print get_intf_range(['interface Ten1/1', 'interface Ten1/5','interface Ten1/8','interface Ten1/10','interface Ten1/11', 'interface Ten1/13','interface Ten1/15', 'interface Ten1/17', 'interface Ten1/19'])
# print get_intf_range(test_list)





def get_interface_range(interface_list):

    '''
    Generate a Cisco IOS interface range string. Takes an interable containing
    a group of interfaces such as ('interface GigabitEthernet1/1, interface GigabitEthernet1/2, 
                                 interface GigabitEthernet1/3, interface GigabitEthernet1/10) 

    and finds if there are any contiguous interfaces in the group. Such that it returns

    'interface range gig1/1-3, gig 1/10'

    '''

    interface_range = 'interface range '

    # sort iterable before finding ranges
    interface_list.sort()

    if not hasattr(interface_list, '__iter__'):
        raise ValueError('interface_list not iterable')

    # 
    if len(interface_list) == 1:
        return interface_range + " , ".join(intf.split()[-1] for intf in interface_list)

    # index begin used to keep track of the first object to compare
    index_begin = 0

    # index end used to keep track of the total len of the group
    index_end = len(interface_list)

    # outer while loop - keep going as long as the index count has not reached the end
    while (index_begin < index_end):

      # save_current used to keep track of the starting interface value
      # (10 if the beginning port is Gig1/10)
      save_current = int(interface_list[index_begin].split("/")[-1])

      # index_next is used to compare the next interface.
      # Gig1/1 and Gig1/2 - index_begin tracks g1/1 and index_next tracks g1/2
      index_next = index_begin + 1

      # check to see if the index has reached the end in this current iteration
      if (index_next == index_end):

        # if the current interface is already in the range 
        if str(interface[0].split(" ")[-1] + "/" + str(save_current)) in interface_range:
            break

        # add last single interface into the range
        else:
            interface = interface_list[index_begin].split("/")
            interface_range += (interface[0].split(" ")[-1] + "/" + str(save_current))
            break

      # get begin and next values for comparison - based on the begin and next indexes
      begin_value = int(interface_list[index_begin].split("/")[-1])
      next_value =  int(interface_list[index_next].split("/")[-1])

      # enter while loop if we find an interface range
      # g1/1 - g1/3 for example
      while (next_value == begin_value + 1 and (index_next+1) < index_end):

        # increment indxes and get new values
        index_begin += 1
        index_next += 1
        begin_value = int(interface_list[index_begin].split("/")[-1])
        next_value = int(interface_list[index_next].split("/")[-1])

        # this while loop will stop as soon as the range is exhausted

      # increment index begin so that it points to the next value
      index_begin += 1
      if (index_begin + 1 == index_end):
        if int(interface_list[index_begin].split("/")[-1]) == (1 + begin_value):
            begin_value +=1

      # check for the range. If save current is not the begin_value
      # then a range was encountered and was "driven" by the inner while loop
      if save_current != begin_value:
        interface = interface_list[index_next].split("/")
        interface_range += (interface[0].split(" ")[-1] + "/" + str(save_current) + "-"+str(begin_value) + " , ")

      # if no range was encountered, then just add the current interface to the range string
      else:
        interface = interface_list[index_next].split("/")
        interface_range += (interface[0].split(" ")[-1] + "/" + str(save_current) + " , ")


    return interface_range
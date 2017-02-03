import logging
import socket
import struct
import re
try: 
    import simplejson as json
except ImportError: 
    import json
import time

__version__ = '1.0.0'

logger = logging.getLogger(__name__)
DEFAULT_SOCKET_TIMEOUT = 5.0
RESPONSE_REGEX_STRING = r'[Pp]rocessed:? (?P<processed>\d+);? [Ff]ailed:? (?P<failed>\d+);? [Tt]otal:? (?P<total>\d+);? [Ss]econds spent:? (?P<seconds>\d+\.\d+)'
RESPONSE_REGEX = re.compile(RESPONSE_REGEX_STRING)

class ZabbixInvalidHeaderError(Exception):
    def __init__(self, *args):
        self.raw_response = args[0]
        super(ZabbixInvalidHeaderError, self).__init__(
            u'Invalid header during response from server')
  
    
class ZabbixInvalidResponseError(Exception):
    def __init__(self, *args):
        self.raw_response = args[0]
        super(ZabbixInvalidResponseError, self).__init__(u'Invalid response from server')
  
    
class ZabbixPartialSendError(Exception):
    def __init__(self, *args):
        self.response = args[0]
        super(ZabbixPartialSendError, self).__init__(u'Some traps failed to be processed')
    
    
class ZabbixTotalSendError(Exception):
    def __init__(self, *args):
        self.response = args[0]
        super(ZabbixTotalSendError, self).__init__(u'All traps failed to be processed')


def get_clock(clock=None):
    if clock: return clock
    return int(round(time.time()))


def get_packet(items_as_list_of_dicts):
    return json.dumps({'request': 'sender data',
                       'data': items_as_list_of_dicts,
                       'clock': get_clock()}
                      )
        

def parse_zabbix_response(response):
    match = RESPONSE_REGEX.match(response)
    processed = int(match.group('processed'))
    failed = int(match.group('failed'))
    total = int(match.group('total'))
    seconds = float(match.group('seconds')) 
    return processed,failed,total,seconds
    
    
def parse_raw_response(raw_response):
    return json.loads(raw_response)['info']


def send(packet, server='127.0.0.1', port=10051, timeout=DEFAULT_SOCKET_TIMEOUT):
    socket.setdefaulttimeout(timeout)
    packet_length = len(packet)
    data_header = str(struct.pack('q', packet_length))
    data_to_send = 'ZBXD\1' + str(data_header) + str(packet)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((server, port))
        sock.send(data_to_send)
    except Exception:
        logger.exception(u'Error talking to server')
        raise
    else:
        response_header = sock.recv(5)
        if not response_header == 'ZBXD\1':
            raise ZabbixInvalidHeaderError(packet)
    
        response_data_header = sock.recv(8)
        response_data_header = response_data_header[:4]
        response_len = struct.unpack('i', response_data_header)[0]
        raw_response = sock.recv(response_len)
    finally:
        sock.close()
    return ZabbixTrapperResponse(raw_response)
    

class ZabbixTrapperResponse(object):
    def __init__(self, raw_response):
        self.processed = None
        self.failed = None
        self.total = None
        self.seconds = None       
        self.raw_response = raw_response
        response = self.parse_raw_response()
        self.parse_response(response)
        
        
    def parse_response(self, response):
        try:
            (self.processed,
             self.failed,
             self.total,
             self.seconds) = parse_zabbix_response(response)
        except Exception:
            logger.exception('Error parsing decoded response')
            raise ZabbixInvalidResponseError(self.raw_response)
        
        
    def parse_raw_response(self):
        try:
            json_response = json.loads(self.raw_response)
            response = json_response['info']
        except Exception:
            logger.exception('Error parsing raw response')
            raise ZabbixInvalidResponseError(self.raw_response)
        else:
            return response
        
        
    def raise_for_failure(self):
        if self.failed == self.total:
            raise ZabbixTotalSendError(self)
        if self.failed > 0:
            raise ZabbixPartialSendError(self)
    

class Item(object):
    def __init__(self, host, key, value, clock = None):
        self.host = host
        self.key = key
        self.value = value
        self.clock = get_clock(clock)
        
    
    def send(self,server, port=10051):
        item_dicts = [self.asdict()]
        packet = get_packet(item_dicts)
        return send(packet, server, port)
    
    
    def asdict(self):
        return {
            'host': self.host,
            'key': self.key,
            'value': self.value,
            'clock' : self.clock
        }

        
class Items(object):
    def __init__(self,server='127.0.0.1', port=10051):
        self.server = server
        self.port = port
        self.items = []
    
    
    def add_item(self,item):
        self.items.append(item)
        return self
    
    
    def add_items(self, items):
        for item in items:
            self.add_item(item)
        return self
    
        
    def send(self):
        item_dicts = [item.asdict() for item in self.items]
        packet = get_packet(item_dicts)
        return send(packet, self.server, self.port)
        
    
class LLD(object):
    def __init__(self, host, key, format_key=True, key_template='{#%s}'):
        self.host = host
        self.key = key
        self.clock = None
        self.rows = []
        self.format_key = format_key
        self.key_template = key_template
        

    def add_row(self, **row_items):
        row = {}
        for k,v in row_items.iteritems():
            if self.format_key:
                key = self.key_template % k
            else:
                key = k
            row[key] = v
        self.rows.append(row)
        self.clock = get_clock(None)
        return self
    
    
    def add_rows(self, list_of_dicts):
        for row in list_of_dicts:
            self.add_row(**row)
        return self
    
    
    def send(self, server, port=10051):
        item_dicts = [self.asdict()]
        packet = get_packet(item_dicts)
        return send(packet, server, port)
    
    
    def asdict(self):
        return {
            'host': self.host,
            'key': self.key,
            'value': self._get_value(),
            'clock': get_clock(self.clock)}
        
    
    def _get_value(self):
        return json.dumps({'data': self.rows})
    
        
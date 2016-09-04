
"""
This is based on the munin-node to CloudWatch bridge that is available here:

https://github.com/nxhack/cloudwatch-munin-node

The primary motivation for not using that directly is simply packaging and
distribution.
"""

import os
import time
import pickle
import getopt
import urllib
import socket
import string

from botocore.session import get_session


STATEFILE = '/var/tmp/cloudwatch-munin-node.state'
CRLF = "\r\n"


class SimpleClient(object):

    def __init__(self, host='localhost', port=4949):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.file = self.sock.makefile("rb")

    def writeline(self, line):
        self.sock.send(line + CRLF)

    def read(self, maxbytes=None):
        if maxbytes is None:
            return self.file.read()
        else:
            return self.file.read(maxbytes)

    def readline(self):
        s = self.file.readline()
        if not s:
            raise EOFError
        if s[-2:] == CRLF:
            s = s[:-2]
        elif s[-1:] in CRLF:
            s = s[:-1]
        return s

    def readlist(self):
        items = []
        while True:
            l = self.readline()
            if not l:
                break
            if l.startswith('.'):
                break
            items.append(l.rstrip())
        return items

    def quit(self):
        self.writeline('quit')

    def nodes(self):
        nodes = []
        self.writeline('nodes')
        return self.readlist()

    def list(self):
        """ Return a list of all available metrics """
        self.writeline('list')
        return self.readline().split()

    def config(self, metric):
        self.writeline('config' + metric)
        config = {
            'upper-limit': -1,
            'lower-limit': -1,
            'base': 1000,
            'unit': None,
        }

        for item in self.readlist():
            if item.startswith('graph_args'):
                args = item.split()
                args.remove('graph_args')
                optlist, args = getopt.getopt(
                    args,
                    'l:u:r',
                    ['base=', 'lower-limit=', 'upper-limit=', 'logarithmic', 'rigid', 'units-exponent='],
                )

                for wo, wa in optlist:
                    if wo in ('-u', '--upper-limit'):
                        # some plugins has bug
                        ws = wa.rstrip(';')
                        config['upper-limit'] = int(ws)
                        config['unit'] = 'Percent'
                    if wo in ('-l', '--lower-limit'):
                        ws = wa.rstrip(';')
                        config['lower-limit'] = int(ws)
                    if wo in ('--base'):
                        ws = wa.rstrip(';')
                        config['base'] = int(ws)

            '''
            mconfig = item.split()
            if mconfig[0].endswith('.type'):
                mcdata = mconfig[0].split('.')
                mname = mitem + '_' + mcdata[0]
                mdtype[mname] = mconfig[1]
            if mconfig[0].endswith('.cdef'):
                mcdata = mconfig[0].split('.')
                mname = mitem + '_' + mcdata[0]
                mcdef[mname] = mconfig[1].split(',')
            '''

    def fetch(self, metric):
        self.writeline('fetch' + metric)
        return self.readlist()

        mwval = 0.0
        for val in self.readlist():
             mval = 0.0
             nv = val.split()
             mn = nv[0].split('.')
             mname = mitem + '_' + mn[0]
            itemtype = 'GAUGE'
            if mname in mdtype:
                itemtype = mdtype[mname]
            if nv[1] != 'U':
                try:
                    mval = float(nv[1])
                except:
                    mval = 0.0
            if itemtype != 'GAUGE':
                mnvalue[mname] = mval
                if mname in movalue and mwtime > 0.0:
                    if itemtype == 'ABSOLUTE':
                        mwval = mval
                    else:
                        # itemtype is 'DERIVE' or 'COUNTER'
                        moval = float(movalue[mname])
                        mwval = mval - moval
                        if itemtype == 'COUNTER':
                            if mwval < 0.0:
                                if moval < 4294967296.0:
                                    # width 32bit
                                    mwval += 4294967296.0
                                else:
                                    # width 64bit
                                    mwval += 18446744073709551615.0
                    # Calc rate
                    mval = mwval / mwtime
                else:
                    # missing old data? or first time? value is 'U', force set 0.0
                    mval = 0.0

            # If item has cdef?
            if mname in mcdef:
                # This is ad hoc patch, multiple RPN cannot process (ex. 'cache_hit,client_req,/,100,*')
                try:
            	        mcval = float(mcdef[mname][1])
                except:
                    mcval = 0.0
                mcope = mcdef[mname][2]
                if mcval != 0.0:
                    if mcope == '+':
                        mval = mval + mcval
                    elif mcope == '-':
                        mval = mval - mcval
                    elif mcope == '*':
                        mval = mval * mcval
                    elif mcope == '/':
                        mval = mval / mcval

            yield {
                'MetricName': row['name'],
                'Dimensions': [{'Name': 'Instance', 'Value': 'graphite'}],
                'Timestamp': datetime.datetime.now(),
                'Value': row['value'],
                'Unit': row['unit'],
            }


def main():
    state_old = {}
    if os.path.exists(STATEFILE):
        with open(STATEFILE, 'r') as fp:
            state_old.update(json.load(fp))

    state_new = {    
        '.FETCHTIME': time.time()
    }

    time_since_last_run = 0.0
    if '.FETCHTIME' in state_old:
        time_since_last_run = state_new['.FETCHTIME'] - state_old['.FETCHTIME']

    client = get_session().create_client(
        'cloudwatch',
        region='eu-west-1',
    )

    munin = SimpleClient()

    for metric in munin.list():
        print munin.fetch(metric)
        #client.put_metric_data(
        #    Namespace='Munin',
        #    MetricData=munin.fetch(metric)
        #)

    munin.quit()

    with open(STATEFILE, 'w') as fp:
        json.dump(state_new, fp)

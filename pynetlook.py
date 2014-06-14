#!/usr/bin/env python
#
#  Pynetlook collects netstat like data such as known connections and listening ports of processes,
#   and sends it to Logstash directly or via Redis.
#
#  pynetlook copyright (c) 2014 Emil Lind
#
#    This file is part of pynetlook.
#
#    pynetlook is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    pynetlook is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pynetlook.  If not, see <http://www.gnu.org/licenses/>.
#
#
# changelog:
#  x.x.x - initial versions
#  0.1.0 - first versionized (logstash)
#  0.1.1 - redis output mode
#  0.1.2 - yaml config
#  0.1.3 - daemon mode, builtin scheduler
#  0.1.4 - windows service capable
# 
VERSION="0.1.4"

# todo 0.1.5
#  handle debug levels to logfile (log info and error but not debug unless debug=true)
#  make it run on osx

from __future__ import print_function
import psutil as ps
from pprint import pprint
import socket
import time
import datetime
import logging
import logstash
from logstash_formatter import LogstashFormatter
from dns import resolver,reversename
from sys import stdout,argv,exit,platform
from os.path import exists,splitext,abspath
from os import name as osname
import yaml

if platform=='win32':
    import win32service
    import win32serviceutil
    import win32event


CONFFILE=splitext(abspath(__file__))[0]+'.yaml' # Conffile is pynetlook.yaml
REDIS=False # Overridden by config (logstash is default)
DAEMON_MODE=False #Overridden by config

VERBOSE=False # Overridden by config
DEBUGREDIS=False # Overridden by config 
DEBUG=False # Overridden by config (post config is read)
DEBUG=True # Overridden by config (post config is read)


# defaults
DEFAULT_SLEEP_SECONDS=60 # (overridden by config as sleep_seconds)


# constants
MIN_SLEEP_SECONDS=2 # minimum seconds to enforce as sleep_seconds parameter.

plogger = logging.getLogger()
plogger.setLevel(logging.INFO)
# logfile is pynetlook.log
plfh = logging.handlers.TimedRotatingFileHandler(splitext(abspath(__file__))[0]+'.log',when="midnight",backupCount=2) 
plogger.addHandler(plfh)

if not platform=='win32':
    # signal handling
    import signal
    import sys
    def signal_handler(signal, frame):
        if DEBUG:
            plogger.info('[Quitting]')
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

# windows service don't want arguments... use config file only
if not platform=='win32':

    # arguments parsing
    if (len(argv)>1 and argv[1] == '-d'):
        # Debug argument overrides config
        print("pynetlook [debug mode on] version: %s" % VERSION)
        DEBUG=True
        argv.pop()

    if len(argv)>1 and argv[1] == '-v':
        print("pynetlook version: %s" % VERSION)
        exit(0)

    if len(argv)>1 and argv[1] == '-V':
        VERBOSE=True
        argv.pop()

    #if len(argv)>1 and  ['-h','--help','/?','-?']:
    if len(argv)>1:
        plogger.info("- pynetlook.py %s (c) 2013 Emil Lind <emil@emillind.se> - www.emillind.se\n"
              "\n"
              " Collects netstat like data such as known connections and listening ports of processes,\n"
              "  and sends it to Logstash directly or via Redis.\n"
              "\n"
              "  syntax: ./pynetlook.py [-d|-v]\n"
              "\n"
              "   -d  enable debug output\n"
              "   -v  show version information\n"
              "   -h  or any other argument, shows this help.\n"
              "\n"
              " Note: configuration %s file gets created on first run.\n" % (VERSION,CONFFILE))
        exit(1)

if not exists(CONFFILE):
    if DEBUG:
        plogger.debug("Creating config")
    conf=dict(deamon_mode=False,
              logstash_server="logstash",
              logstash_port=9999,
              use_redis=False,
              redis_debug=False,
              redis_server="redis",
              redis_port=6379,
              redis_db=0,
              sleep_seconds=DEFAULT_SLEEP_SECONDS,
              dns_timeout_seconds=1,
              verbose=False,
              debug=False)
    conffd=file(CONFFILE,"w")
    yaml.dump(conf,conffd,default_flow_style=False)
else:
    if DEBUG:
        plogger.debug("Reading config %s"%(CONFFILE))
    conf=yaml.load(file(CONFFILE,"r"))
    REDIS=conf.get("use_redis",False)
    DEBUGREDIS=conf.get("redis_debug",False)
    if not VERBOSE:
        VERBOSE=conf.get("verbose",VERBOSE)
    if not DEBUG:
        DEBUG=conf.get("debug",DEBUG)

if conf["debug"] and not DEBUG:
    plogger.debug("pynetlook [debug mode on] version: %s" % VERSION)
    DEBUG=True

if DEBUG:
    print("Loaded config:")
    pprint(conf)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

if DEBUG or not REDIS:
    formatter = LogstashFormatter()




if not "sleep_seconds" in conf.keys() or conf["sleep_seconds"]<MIN_SLEEP_SECONDS:
    if DEBUG:
        plogger.debug("warning: sleep_seconds not set, or set to <%s seconds. Using %s seconds." % (MIN_SLEEP_SECONDS,DEFAULT_SLEEP_SECONDS))
    conf["sleep_seconds"]=DEFAULT_SLEEP_SECONDS
    pass

def errorHandler(record):
    plogger.error("error: Problem sending to %s\n%s." % (using,record))
    raise


if REDIS:
    import redis
    import json
    using="redis://%s:%s/%s"%(conf["redis_server"],conf["redis_port"],conf["redis_db"])
    redisconn = redis.StrictRedis(host=conf["redis_server"], port=conf["redis_port"], db=conf["redis_db"])
else:
    using="logstash://%s:%s"%(conf["logstash_server"],conf["logstash_port"])
    #use logstash as default target
    handler = logstash.LogstashHandler(conf["logstash_server"],conf["logstash_port"])

    # FIXME: make these settings in config and/or switches. Possibly using debug-mode for raise?
    # To ignore all connection errors and try again next message set this...
    #handler.closeOnError=1
    # ... but to fix error message if logstash_server cannot be reached and raise error
    handler.handleError=errorHandler
    handler.setFormatter(formatter)
    logger.addHandler(handler)


if DEBUG:
    handler2 = logging.StreamHandler(stream=stdout)
    handler2.setFormatter(formatter)
    logger.addHandler(handler2)


if hasattr(socket,"setdefaulttimeout"):
    socket.setdefaulttimeout(conf['dns_timeout_seconds'])

def dnsptr(addrtuple,prefix=""):
    dnsnames=[]
    ip="0.0.0.0"
    port="0"
    if len(addrtuple)>1:
        ip=addrtuple[0]
        port=addrtuple[1]
        revaddr=reversename.from_address(ip)
        try:
            dnsnames=sorted([a.to_text().strip('.') for a in resolver.query(revaddr,"PTR").rrset])
        except resolver.NXDOMAIN:
            pass
    addrdict={'%sdnsnames'%prefix:dnsnames,'%sport'%prefix:port,'%sip'%prefix:ip}
    return addrdict


def run():
    plogger.info("[Running...]")
    listening=[]
    established=[]
    nrconns=0
    nosuchprocess=0
    accessdenied=0
    pidlist=ps.get_pid_list()

   
        
    if VERBOSE or DEBUG:
        plogger.info("Sending connections for %s processes to %s..." % (len(pidlist),using))
    for pids in pidlist:
        try:
            p=ps.Process(pids)
            conns=p.get_connections()
            nrconns+=len(conns)
            if conns:
                for conn in conns:
                    l=dnsptr(conn.local_address,prefix="local_")
                    r=dnsptr(conn.remote_address,prefix="remote_")
                msgdict={'status':str(conn.status),'process_name':p.name,'cmdline':" ".join(p.cmdline)}
                msgdict.update(r)
                msgdict.update(l)
                if REDIS:
                    msgjson=json.dumps({'@fields':msgdict})
                    if DEBUGREDIS:
                        pprint(msgjson)
                        redisconn.rpush('pynetlook',msgjson)
                if DEBUG or not REDIS:
                    logger.info("@%(status)s@ [%(process_name)s] @%(cmdline)s@ %(local_dnsnames)s(%(local_ip)s):%(local_port)s %(local_dnsnames)s(%(local_ip)s):%(local_port)s" % msgdict,extra=msgdict)

                            
        except ps.AccessDenied,arg:
            accessdenied+=1
            if DEBUG:
                plogger.error("Access denied for %s" % (str(arg)+p.username))
            
        except ps.NoSuchProcess,arg:
            if DEBUG:
                nosuchprocess+=1
                plogger.error("NoSuchProcess for %s" % (str(arg)+p.username))
            

    if VERBOSE or DEBUG:
        plogger.info("Processed and sent %i connections (noprocess: %i, noperm: %i)." % (nrconns,nosuchprocess,accessdenied))
    if DEBUG:
        plogger.info("[DONE]")

if platform=='win32':
    class PyNetlookSvc(win32serviceutil.ServiceFramework):
        # you can NET START/STOP the service by the following name
        _svc_name_ = "pynetlook"
        # this text shows up as the service name in the Service
        # Control Manager (SCM)
        _svc_display_name_ = "Pynetlook %s" % VERSION
        # this text shows up as the description in the SCM
        _svc_description_ = "Collects netstat like data such as known connections and listening ports of processesand sends it to Logstash directly or via Redis. Pynetlook (c) 2013 Emil Lind <emil@emillind.se> - www.emillind.se"
        
        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self,args)
            # create an event to listen for stop requests on
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        
        # core logic of the service   
        def SvcDoRun(self):
            import servicemanager
            
            rc = None
            # if the stop event hasn't been fired keep looping
            while rc != win32event.WAIT_OBJECT_0:
                try:
                    run()
                except Exception, exc:
                    plogger.error("[Caught exception!] %s" % (str (exc)))
                    self.SvcStop()
                    exit(1)
                # block for 5 seconds and listen for a stop event
                rc = win32event.WaitForSingleObject(self.hWaitStop, conf["sleep_seconds"]*1000)
                
            
        # called when we're being shut down    
        def SvcStop(self):
            # tell the SCM we're shutting down
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            # fire the stop event
            win32event.SetEvent(self.hWaitStop)



if __name__ == '__main__':  
    if osname=='nt':
        win32serviceutil.HandleCommandLine(PyNetlookSvc)

    else:
        running=True
        while running:
            if DEBUG:
                plogger.info("[Sleeping %s seconds...]" % (conf["sleep_seconds"]))
            time.sleep(conf["sleep_seconds"])
            run()
        if not DEAMON_MODE:
            running=False

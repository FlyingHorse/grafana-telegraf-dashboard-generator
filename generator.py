#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2009-2015:
#    Alexandre Le Mao, alexandre.lemao@gmail.com

"""
This class is for generating Telegraf dashboards from Influxdb.
"""

from influxdb import InfluxDBClusterClient
from influxdb.exceptions import InfluxDBClientError
import json
import argparse
from jinja2 import Environment, FileSystemLoader
import os
import re
import glob
import uuid
import logging

CONNECTED = 1
DISCONNECTED = 2
SWITCHING = 3

##################
# Class Influxdb #
##################
class Influxdb(object):
    def __init__(self):
        self.influxdb_user   = args.influxdb_user
        self.influxdb_passwd = args.influxdb_passwd
        self.influxdb_ssl    = args.influxdb_ssl
        self.influxdb_verify_ssl    = args.influxdb_verify_ssl
        self.databases       = re.compile(args.databases)
        self.hosts           = []

	for host in args.hosts.split(','):
            self.hosts.append(tuple(filter(None, host.split(':'))))
	
        self.is_connected = DISCONNECTED

    def open(self):
       """
       Connect to InfluxDB cluster.
       """
       try:
           self.cc = InfluxDBClusterClient(hosts = self.hosts,
                               username=self.influxdb_user,
                               password=self.influxdb_passwd,
                               ssl=self.influxdb_ssl,
                               verify_ssl=self.influxdb_verify_ssl)

           self.is_connected = CONNECTED

       except InfluxDBClientError as e:
           logging.warning("Connection failed: %s" % e)
           return False

       return True

    def get_ds_list(self):
        dbs = self.cc.get_list_database()
        return [db for db in dbs if self.databases.search(db['name'])]
   
    def get_measurements(self,dbname):
        self.cc.switch_database(dbname)
	m = self.cc.query('SHOW MEASUREMENTS')
        return json.dumps(m.raw['series'][0]['values'])

###################
# Class Dashboard #
###################
class Dashboard(object):
    def __init__(self):
	self.rows_dir              = os.path.dirname(os.path.abspath(__file__)) + "/rows"
	self.dashboards_dir        = os.path.dirname(os.path.abspath(__file__)) + "/dashboards"
	self.tmpls_dir             = os.path.dirname(os.path.abspath(__file__)) + "/templates"
	self.annotations_dir       = os.path.dirname(os.path.abspath(__file__)) + "/annotations"
	self.enable_templating     = args.enable_templating
	self.enable_annotations    = args.enable_annotations
	self.jinja_rows_env        = Environment(loader=FileSystemLoader(self.rows_dir),trim_blocks=True)
	self.jinja_tmpls_env       = Environment(loader=FileSystemLoader(self.tmpls_dir),trim_blocks=True)
	self.jinja_annotations_env = Environment(loader=FileSystemLoader(self.annotations_dir),trim_blocks=True)
	self.dash                  = "{\n"
        self.dash_version          = args.dash_version

        if not os.path.exists(self.dashboards_dir):
            os.makedirs(self.dashboards_dir)

    def panelid(self,_id):
        return uuid.uuid4().int & (1<<16)-1

    def begin_rows(self):
	self.dash += '"rows": [\n'

    def concat_rows(self,row,ds):
        self.jinja_rows_env.filters['panelid'] = self.panelid
	self.dash += self.jinja_rows_env.get_template(row + '.json').render(datasource=ds,version=self.dash_version)

    def end_rows(self):
	self.dash += '],\n'

    def add_tmpls(self,ds):
	self.dash += '"templating": {"enable": true, "list": [\n'
	names = [os.path.basename(f) for f in glob.glob(self.tmpls_dir + "/*.json")]
        names.sort()
	for tmpl in names:
	    self.dash += self.jinja_tmpls_env.get_template(tmpl).render(datasource=ds)

	self.chomp(',')
	self.dash += ']},\n'

    def add_annotations(self,ds):
        self.dash += '"annotations": { "list": [\n'
        names = [os.path.basename(f) for f in glob.glob(self.annotations_dir + "/*.json")]
        names.sort()
        for annotation in names:
            self.dash += self.jinja_annotations_env.get_template(annotation).render(datasource=ds)

        self.chomp(',')
        self.dash += ']},\n'

    def write_dash(self,ds):
	output_dash = self.dashboards_dir + "/" + ds
	if dashboard.enable_templating:
            output_dash += "_t"
        if dashboard.enable_annotations:
	    output_dash += "_a"
	with open(output_dash + ".json", "wb") as fh:
	    fh.write(self.dash)

    def chomp(self,char):
	pos = self.dash.rfind(char)
	self.dash = self.dash[:pos] + self.dash[(pos+1):]
	return self.dash

    def append(self,string):
	self.dash += string

########
# Main #
########
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--influxdb-user',required=False,action='store',dest='influxdb_user',help='InfluxDB Username. Should be admin *',metavar="INFLUXUSER",default='admin')
    parser.add_argument('--influxdb-passwd',required=False,action='store',dest='influxdb_passwd',help='InfluxDB Username password.',metavar="INFLUXPASSWD",default='')
    parser.add_argument('--databases',required=False,action='store',dest='databases',help='InfluxDB Databases as regexp',metavar="DBS",default='^telegraf$')
    parser.add_argument('--hosts',required=False,action='store',dest='hosts',help='InfluxDB raft hosts.',metavar="HOSTS",default='localhost:8086')
    parser.add_argument('--dashboard-version',required=False,action='store',dest='dash_version',help='Dashboard version to set.',metavar="DASHVERSION",default=0)
    parser.add_argument('--enable-templating',required=False,action='store_true',dest='enable_templating',help='Enable templates',default=False)
    parser.add_argument('--enable-annotations',required=False,action='store_true',dest='enable_annotations',help='Enable annotations',default=False)
    parser.add_argument('--ssl',required=False,action='store_true',dest='influxdb_ssl',help='Use SSL for InfluxDB connection.',default=False)
    parser.add_argument('--verify-ssl',required=False,action='store_true',dest='influxdb_verify_ssl',help='Verify SSL when connecting to InfluxDB.',default=False)
    parser.add_argument('-v','--verbose',required=False,action='store_true',dest='verbose',help='Increase output verbosity',default=False)

    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    influxdb = Influxdb()
    influxdb.open()
 
    for db in influxdb.get_ds_list():
	dashboard = Dashboard()
	dashboard.concat_rows('header',db['name'])
	dashboard.begin_rows()
        dashboard.concat_rows('netflow',db['name'])
	dashboard.concat_rows('summary',db['name'])
	dashboard.concat_rows('network',db['name'])
        dashboard.concat_rows('system',db['name'])

        logging.debug("InfluxDB database %s :" % db['name'])
        series = influxdb.get_measurements(db['name'])

	if "execvarnish45" in series:
            dashboard.concat_rows('varnish4',db['name'])
            logging.debug(" - Varnish4")
        elif "execvarnish3" in series:
            dashboard.concat_rows('varnish3',db['name'])
            logging.debug(" - Varnish3")
        elif "execvarnish" in series:
            dashboard.concat_rows('varnish3',db['name'])
            logging.debug(" - Varnish3")
        if "nginx" in series:
            dashboard.concat_rows('nginx',db['name'])
            logging.debug(" - Nginx")
	if "apache" in series:
	    dashboard.concat_rows('apache',db['name'])
            logging.debug(" - Apache")
        if "phpfpm" in series:
            dashboard.concat_rows('phpfpm',db['name'])
            logging.debug(" - PHP FPM")
        if "httpjson_opcache" in series:
            dashboard.concat_rows('opcache',db['name'])
            logging.debug(" - OpCache")
        if "memcached" in series:
            dashboard.concat_rows('memcache',db['name'])
            logging.debug(" - Memcache")
        if "mysql" in series:
            dashboard.concat_rows('mysql',db['name'])
            logging.debug(" - MySQL")
        if "mongodb" in series:
            dashboard.concat_rows('mongodb',db['name'])
            logging.debug(" - MongoDB")
	if "redis" in series:
	    dashboard.concat_rows('redis',db['name'])
            logging.debug(" - Redis")
        if "elasticsearch" in series:
	    dashboard.concat_rows('elasticsearch',db['name'])
            logging.debug(" - Elasticsearch")
        if "passenger" in series:
            dashboard.concat_rows('passenger',db['name'])
            logging.debug(" - Passenger")
        if "rabbitmq" in series:
            dashboard.concat_rows('rabbitmq',db['name'])
            logging.debug(" - RabbitMQ")

	dashboard.chomp(',')
	dashboard.end_rows()
	if dashboard.enable_templating:
	    dashboard.add_tmpls(db['name'])
	if dashboard.enable_annotations:
	    dashboard.add_annotations(db['name'])
	dashboard.concat_rows('footer',db['name'])
	dashboard.append('}')
	dashboard.write_dash(db['name'])


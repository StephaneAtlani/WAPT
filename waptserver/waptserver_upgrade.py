#!/usr/bin/python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------
#    This file is part of WAPT
#    Copyright (C) 2013  Tranquil IT Systems http://www.tranquil.it
#    WAPT aims to help Windows systems administrators to deploy
#    setup and update applications on users PC.
#
#    WAPT is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    WAPT is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with WAPT.  If not, see <http://www.gnu.org/licenses/>.
#
# -----------------------------------------------------------------------
__version__ = "1.4.3"
usage = """\
%prog [-c configfile] [-l loglevel] action

Action:
    upgrade2postgres: import data from running mongodb (wapt <1.4)
    upgrade_structure : update the table structure to most current one.
    reset_database : empty the db and recreate tables.
    import_data : import json files
"""

import os
import sys
import glob

try:
    wapt_root_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..'))
except:
    wapt_root_dir = 'c:/tranquilit/wapt'

sys.path.insert(0, os.path.join(wapt_root_dir))
sys.path.insert(0, os.path.join(wapt_root_dir, 'lib'))
sys.path.insert(0, os.path.join(wapt_root_dir, 'lib', 'site-packages'))

import logging
import ConfigParser
from optparse import OptionParser

from playhouse.migrate import *
from waptserver_model import *
from waptserver_utils import *

DEFAULT_CONFIG_FILE = os.path.join(wapt_root_dir, 'conf', 'waptserver.ini')
config_file = DEFAULT_CONFIG_FILE

# setup logging
logger = logging.getLogger()
logging.basicConfig()

# TODO : move to waptserver_upgrade with plain mongo connection.
def create_import_data(ip='127.0.0.1',fn=None):
    """Connect to a mongo instance and write all wapt.hosts collection as json into a file"""
    print('Read mongo data from %s...' % ip)
    d = json.load(os.popen('mongoexport -h %s -d wapt -c hosts  --jsonArray' % ip))
    print('%s records read.'%len(d))
    if fn is None:
        fn = "%s.json"%ip
    #0000 is not accepted by postgresql
    open(fn,'wb').write(json.dumps(d).replace('\u0000',' '))
    print('File %s done.'%fn)
    return fn

def load_json(filenames=r'c:\tmp\*.json',add_test_prefix=None):
    """Read a json host collection exported from wapt mongo and creates
            Wapt PG Host DB instances"""
    for fn in glob.glob(filenames):
        print('Loading %s'%fn)
        recs = json.load(codecs.open(fn,'rb',encoding='utf8'))
        print('%s recs to load'%len(recs))

        for rec in recs:
            # to duplicate data for testing
            if add_test_prefix:
                 rec['host']['computer_fqdn'] =  add_test_prefix+'-'+rec['host']['computer_fqdn']
                 rec['uuid'] = add_test_prefix+'-'+rec['uuid']

            computer_fqdn = rec['host']['computer_fqdn']
            uuid = rec['uuid']
            try:
                print update_host_data(rec)
            except Exception as e:
                print(u'Error for %s : %s'%(ensure_unicode(computer_fqdn),ensure_unicode(e)))
                wapt_db.rollback()
                raise e

def comment_mongodb_lines(conf_filename = '/opt/wapt/conf/waptserver.ini'):
    if not os.path.exists(conf_filename):
        print ("file %s does not exists!! Exiting " %  conf_filename)
        sys.exit(1)
    data = open(conf_filename)
    new_conf_file_data = ""
    modified = False
    for line in data.readlines():
        line = line.strip()
        if "mongodb_port" in line:
            line = '#%s' % line
            modified = True
        elif 'mongodb_ip' in line:
            line = '#%s' % line
            modified = True
        new_conf_file_data = new_conf_file_data + line + '\n'
    print new_conf_file_data
    if modified ==True:
        os.rename (conf_filename,"%s.%s" % (conf_filename,datetime.datetime.today().strftime('%Y%m%d-%H:%M:%S')))
        with open(conf_filename, "w") as text_file:
            text_file.write(new_conf_file_data)

def upgrade2postgres():
    """Dump current mongo wapt.hosts collection and feed it to PG DB"""
    # check if mongo is runnina
    print "upgrading data from mongodb to postgresql"
    mongo_running = False
    for proc in psutil.process_iter():
        if proc.name() == 'mongod':
            mongo_running=True
    if not mongo_running:
        print ("mongodb process not running, please check your configuration. Perhaps migration of data has already been done...")
        sys.exit(1)
    val = subprocess.check_output("""  psql wapt -c " SELECT datname FROM pg_database WHERE datname='wapt';   " """, shell=True)
    if 'wapt' not in val:
        print ("missing wapt database, please create database first")
        sys.exit(1)

    data_import_filename = "/tmp/waptupgrade_%s.json" % datetime.datetime.today().strftime('%Y%m%d-%h:%M:%s')
    print ("dumping mongodb data in %s " % data_import_filename)
    create_import_data(ip='127.0.0.1',fn=data_import_filename)
    try:
        load_json(filenames=data_import_filename)
        # TODO : check that data is properly imported
        os.unlink(data_import_filename)
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print ('Exception while loading data, please check current configuration')
        sys.exit(1)

def upgrade_postgres():
    init_db(False)
    migrator = PostgresqlMigrator(wapt_db)
    logging.info('Current DB: %s version: %s' % (wapt_db.connect_kwargs,get_db_version()))

    # from 1.4.1 to 1.4.2
    if get_db_version() < '1.4.2':
        with wapt_db.transaction():
            logging.info('Migrating from %s to %s' % (get_db_version(),'1.4.2'))
            migrate(
                migrator.rename_column(Hosts._meta.name,'host','host_info'),
                migrator.rename_column(Hosts._meta.name,'wapt','wapt_status'),
                migrator.rename_column(Hosts._meta.name,'update_status','last_update_status'),

                migrator.rename_column(Hosts._meta.name,'softwares','installed_softwares'),
                migrator.rename_column(Hosts._meta.name,'packages','installed_packages'),
            )
            HostGroups.create_table(fail_silently=True)
            HostJsonRaw.create_table(fail_silently=True)
            HostWsus.create_table(fail_silently=True)

            (v,created) = ServerAttribs.get_or_create(key='db_version')
            v.value = '1.4.2'
            v.save()

    # from 1.4.2 to 1.4.3
    if get_db_version() < '1.4.3':
        with wapt_db.transaction():
            logging.info('Migrating from %s to %s' % (get_db_version(),'1.4.3'))
            if not [c.name for c in wapt_db.get_columns('hosts') if c.name == 'host_certificate']:
                migrate(
                    migrator.add_column(Hosts._meta.name,'host_certificate',Hosts.host_certificate),
                    )

            (v,created) = ServerAttribs.get_or_create(key='db_version')
            v.value = '1.4.3'
            v.save()

    # from 1.4.3 to 1.4.3.1
    if get_db_version() < '1.4.3.1':
        with wapt_db.transaction():
            logging.info('Migrating from %s to %s' % (get_db_version(),'1.4.3.1'))
            columns = [c.name for c in wapt_db.get_columns('hosts')]
            opes = []
            if not 'last_logged_on_user' in columns:
                opes.append(migrator.add_column(Hosts._meta.name,'last_logged_on_user',Hosts.last_logged_on_user))
            if 'installed_sofwares' in columns:
                opes.append(migrator.drop_column(Hosts._meta.name,'installed_sofwares'))
            if 'installed_sofwares' in columns:
                opes.append(migrator.drop_column(Hosts._meta.name,'installed_packages'))
            migrate(*opes)

            (v,created) = ServerAttribs.get_or_create(key='db_version')
            v.value = '1.4.3.1'
            v.save()

if __name__ == '__main__':
    parser = OptionParser(usage=usage, version='waptserver.py ' + __version__)
    parser.add_option(
        "-c",
        "--config",
        dest="configfile",
        default=DEFAULT_CONFIG_FILE,
        help="Config file full path (default: %default)")
    parser.add_option(
        "-l",
        "--loglevel",
        dest="loglevel",
        default='info',
        type='choice',
        choices=[
            'debug',
            'warning',
            'info',
            'error',
            'critical'],
        metavar='LOGLEVEL',
        help="Loglevel (default: warning)")
    parser.add_option(
        "-d",
        "--devel",
        dest="devel",
        default=False,
        action='store_true',
        help="Enable debug mode (for development only)")
    parser.add_option(
        "-p",
        "--test-prefix",
        dest="test_prefix",
        default=None,
        help="test prefix for fqdn and uuid for load testing (for development only)")

    (options, args) = parser.parse_args()

    utils_set_devel_mode(options.devel)
    if options.loglevel is not None:
        setloglevel(logger, options.loglevel)

    action = args and args[0] or 'upgrade_structure'

    if action == 'upgrade2postgres':
        print('Upgrading from mongodb to postgres')
        comment_mongodb_lines()
        upgrade2postgres()
    elif action == 'upgrade_structure':
        print('Updating current PostgreSQL DB Structure')
        upgrade_postgres()
    elif action == 'reset_database':
        print('Reset current PostgreSQL DB Structure')
        init_db(True)
    elif action == 'import_data':
        print('import json data from files %s' % (' '.join(args[1:])))
        for f in args[1:]:
            load_json(f,add_test_prefix = options.test_prefix)

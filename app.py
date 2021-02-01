import pandas as pd
import numpy as np
import glob
import time
import os

import logging
import configparser
import base64

from pyzabbix import ZabbixAPI
from influxdb import DataFrameClient
import statsmodels.api as sm
from datetime import datetime

from timeseries import write, Prospector, Quacksalver, StoreKeeper
from journeyman import rename, split_file_names

config = configparser.ConfigParser()
config.read('/joyce/app/joyce.conf')

TODAY = time.strftime("%Y-%m-%d %H:%M")

INVERT_METRIC = (config['JOYCE']['INVERT_METRIC']).split(',')
PATH = config['JOYCE']['PATH']

SEASONS = int(config['JOYCE']['SEASONS'])
METRICS = (config['JOYCE']['METRICS']).split(',')
NO_OF_HOURS = int(config['JOYCE']['NO_OF_HOURS'])
HISTORY_SECOND_LEFT = int(config['ZABBIX']['HISTORY_SECOND_LEFT'])
ROLLING_MEAN = int(config['JOYCE']['ROLLING_MEAN'])
SUBGROUP = config['JOYCE']['SUBGROUP']

ZABBIX_HOST = config['ZABBIX']['SERVER']
ZABBIX_USER = config['ZABBIX']['USER']
ZABBIX_HASH_PASSWORD = os.environ.get('JOYCE_PASSWORD')
ZABBIX_PASSWORD = base64.b64decode(ZABBIX_HASH_PASSWORD).decode("utf-8")
ZABBIX_GROUP_IDS = (config['ZABBIX']['GROUP_IDS']).split(',')

INFLUX_HOST = config['INFLUXDB']['SERVER']
INFLUX_PORT = int(config['INFLUXDB']['PORT'])
INFLUX_DATABASE = config['INFLUXDB']['DATABASE']

z = ZabbixAPI(server=ZABBIX_HOST)
z.login(ZABBIX_USER, ZABBIX_PASSWORD)

hosts_id = pd.DataFrame(z.host.get(groupids=ZABBIX_GROUP_IDS, output=['hostid', 'name'], filter={'status': 0}))

if SUBGROUP != 'False':
    hosts_id = hosts_id[hosts_id.name.str.contains(SUBGROUP)]

INFLUX_CLIENT = DataFrameClient(INFLUX_HOST, INFLUX_PORT, INFLUX_DATABASE)

prospector = Prospector(history_second_left=HISTORY_SECOND_LEFT, rolling_mean=ROLLING_MEAN)
quacksalver = Quacksalver(seasons=SEASONS, no_of_hours=NO_OF_HOURS, freq=ROLLING_MEAN)
storekeeper = StoreKeeper(PATH + 'hostname.clusters', hosts_id)

if __name__ == '__main__':

    for _, host in hosts_id.iterrows():
        """
            Get original data from Zabbix
        """
        host_id, host_name = host

        metrics = []
        item_ids = z.item.get(hostids=host_id, output=['itemid', 'name'], filter={'name': METRICS})

        for item in item_ids:
            # Why load data twice ?
            prospector.load(host_name, item['itemid'], item['name'])

    """
        Merge data for clusters nodes
    """
    storekeeper.merge()

    original_files = glob.glob(PATH + "logs/*" +  "*original.csv")

    for file in original_files:
        """
            Find original files and make predictions
        """
        hostname, item_id, metric, _ = split_file_names(file)
        df = pd.read_csv(file)

        quacksalver.forecast(hostname, df, item_id, metric)


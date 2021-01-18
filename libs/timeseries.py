import pandas as pd
from datetime import datetime, timedelta
import statsmodels.api as sm
from influxdb import DataFrameClient
import os
import glob
import time
import configparser
import base64
from pyzabbix import ZabbixAPI
from .journeyman import rename, intermediary
import logging


config = configparser.ConfigParser()
config.read('/joyce/app/joyce.conf')

TODAY = time.strftime("%Y-%m-%d %H:%M")

PATH = config['JOYCE']['PATH']
ROUND = int(config['JOYCE']['ROUND'])
INVERT_METRIC = (config['JOYCE']['INVERT_METRIC']).split(',')

ZABBIX_HOST = config['ZABBIX']['SERVER']
ZABBIX_USER = config['ZABBIX']['USER']
ZABBIX_HASH_PASSWORD = os.environ.get('JOYCE_PASSWORD')
ZABBIX_PASSWORD = base64.b64decode(ZABBIX_HASH_PASSWORD).decode("utf-8")

INFLUX_HOST = config['INFLUXDB']['SERVER']
INFLUX_PORT = int(config['INFLUXDB']['PORT'])
INFLUX_DATABASE = config['INFLUXDB']['DATABASE']

z = ZabbixAPI(server=ZABBIX_HOST)
z.login(ZABBIX_USER, ZABBIX_PASSWORD)

INFLUX_CLIENT = DataFrameClient(INFLUX_HOST, INFLUX_PORT, INFLUX_DATABASE)

FILE_LOG = config['LOGGER']['FILE_LOG']
DEBUG = config['LOGGER']['DEBUG']

logger = logging.getLogger('joyce-app')

if DEBUG == 'True':
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

fh = logging.FileHandler(PATH + FILE_LOG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


@intermediary
def write(df: pd.DataFrame, hostname: str, item_id: int, metric: str, source: str):
    """
        Save Time Series in DataBase and on the disk
    """
    assert source in ['original', 'prediction', 'cluster']
    INFLUX_CLIENT.write_points(df, database=INFLUX_DATABASE, measurement=metric, tags={'hostname' : hostname, 'source': source })

    if item_id != None:
        df.to_csv(PATH + "/logs/"+str(hostname)+"_"+str(item_id)+"_"+str(metric)+"_" + source + ".csv")


class Prospector:
    """
        Loading historical data from Zabbix
    """

    def __init__(self, history_second_left: int, rolling_mean: int):
        """Constructor"""
        self.history_second_left = history_second_left
        self.rolling_mean = rolling_mean

    @intermediary
    def load(self, hostname: str, item_id: int, metric: str):
        df = pd.DataFrame(z.history.get(itemids=item_id, time_from=int(time.time() - self.history_second_left), history=0))
        df.clock = df.clock.apply(lambda d: datetime.fromtimestamp(int(d)).strftime('%Y%m%d %H:%M:%S'))
        df['clock'] = pd.to_datetime(df['clock'])
        df_day_original = df.set_index('clock')[['value']]

        metric = rename(metric)
 
        if metric in INVERT_METRIC:
            df_day_original['value'] = df_day_original['value'].apply(lambda x: 100 - round(float(x), ROUND))
 
        df_day_original['value'] = pd.to_numeric(df_day_original['value'])
        df_day_original = df_day_original.resample(str(self.rolling_mean) + 'min').mean()
        df_day_original['value'] = df_day_original['value'].apply(lambda x: str(round(x, ROUND)))

        write(df=df_day_original, hostname=hostname, metric=metric, item_id=item_id, source='original')

        logger.debug('load data ' + hostname)


class Quacksalver:
    """
        Forecasting data with ML algoritm
    """

    def __init__(self, seasons: int, no_of_hours: int, freq: int):
        """Constructor"""
        self.seasons = seasons
        self.no_of_hours = no_of_hours
        self.freq = freq

    @intermediary
    def forecast(self, hostname: str, dataframe: pd.DataFrame, item_id: int, metric: str):
        """
            Forecast data
        """
        last_timestamp = dataframe['clock'][dataframe.shape[0] - 1]
        last_timestamp = datetime.strptime(last_timestamp, '%Y-%m-%d %H:%M:%S')
        first_prediction_timestamp = last_timestamp + timedelta(minutes=self.freq)
        last_prediction_timestamp = first_prediction_timestamp + timedelta(hours=(self.no_of_hours - 1))
        
        date = pd.date_range(first_prediction_timestamp, last_prediction_timestamp, freq=str(self.freq) + "min")
 
        if dataframe['value'].max() - dataframe['value'].min() < 2:
            forecast = pd.Series([dataframe['value'].mean() for _ in range(len(date))])
        else:
            mod = sm.tsa.SARIMAX(dataframe['value'], trend='n', order=(1, 1, 1), seasonal_order=(0, 1, 1, self.seasons),
                         enforce_stationarity=False , enforce_invertibility=False)
            results = mod.fit()

            forecast = results.predict(start=dataframe.shape[0], end=dataframe.shape[0] + (len(date) - 1), dynamic=True)
 
        dataframe = pd.DataFrame(forecast)
        dataframe['clock'] = date 
        dataframe['forecast'] = pd.to_numeric(dataframe[0])
        dataframe = dataframe[['clock', 'forecast']]
        dataframe = dataframe.set_index('clock')

        """
            Replace negative numbers by zero (if exist)
        """
        dataframe = dataframe.clip(lower=0)

        write(df=dataframe, hostname=hostname, item_id=item_id, source='prediction', metric=metric)

        logger.debug('forecast data ' + hostname)

class StoreKeeper:
    """
        Merge time series for clusters nodes
    """

    def __init__(self, clusters_file: str, hosts_id):
        """Constructor"""
        self.clusters = pd.read_csv(clusters_file, sep=" ", header=None)
        self.clusters.columns = ['lpar1', 'lpar2', ':', 'SG', 'active']
        self.clusters = self.clusters[['lpar1', 'lpar2']].drop_duplicates()
        self.hosts_id = hosts_id


    def read_data(self, hostname:str, metric: str):
        file_name = "./logs/" + str(hostname) + "*" + str(metric) + "_original.csv"
        logger.debug(file_name)
        data_file = glob.glob(file_name)[0]
        df = pd.read_csv(data_file)
        return data_file, df

    def save(self, df: pd.DataFrame, files: list):
        for file in files:
            df.to_csv(file)

    @intermediary
    def merge(self):

        logger.debug('Start merge data')

        for row, col in self.clusters.iterrows():

            lpar1 = col['lpar1']
            lpar2 = col['lpar2']

            logger.debug("Merge lpars: " + lpar1 + ' ' + lpar2 + " " + str(self.hosts_id['name'].tolist()))

            if lpar1 in self.hosts_id['name'].tolist() and lpar2 in self.hosts_id['name'].tolist():
                for metric in ['memory', 'user', 'system', 'swap']:

                    logger.debug("Merge loop: " + lpar1)
                    logger.debug("Merge loop: " + lpar2)

                    file1, df1 = self.read_data(lpar1, metric)
                    file2, df2 = self.read_data(lpar2, metric)
                    
                    df = pd.concat([df1[['clock', 'value']], df2[['clock', 'value']]], axis=1)
                    df.columns = ['clock_1', 'lpar1', 'clock_2', 'lpar2']
                    df['clus'] = df.apply(lambda  x: x['lpar1'] if x['lpar1'] > x['lpar2'] else x['lpar2'], axis=1)
                    df = df[['clock_1', 'clus']]

                    df.columns = ['clock', 'value']
                    self.save(df, [file1, file2])

                    df['clock'] = pd.to_datetime(df['clock'])
                    df = df.set_index('clock')[['value']]
                    df['value'] = df['value'].apply(lambda x: str(round(x, ROUND)))

                    for hostname in [lpar1, lpar2]:

                        write(df=df, hostname=hostname, metric=metric, item_id=None, source='cluster')
                        logger.debug('merge data ' + hostname)
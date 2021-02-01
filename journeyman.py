"""
Mini functions
"""
import logging

import configparser
config = configparser.ConfigParser()
config.read('/joyce/app/joyce.conf')

import time
TODAY = time.strftime("%Y-%m-%d %H:%M")
PATH = config['JOYCE']['PATH']
FILE_LOG = config['LOGGER']['FILE_LOG']

logger = logging.getLogger('joyce-app')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(PATH+FILE_LOG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

def intermediary(func):
    """
        My decorator for handle exceptions
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BaseException as e:
            logger.error('{} {}'.format(e, str(args)))
    return wrapper

def rename(metric: str) -> str:
    """
        Simple rename metric
    """

    if metric == "svmon_pavailable":
        metric = "memory"
    elif metric == "CPU user":
        metric = "user"
    elif metric == "CPU system":
        metric = "system"
    elif metric == "Swap file free (percent)":
        metric = "swap"

    return metric


def split_file_names(file_name:str) -> list:
    """
        Get file name and return list: [ hostname, item_id, metric ]
    """

    tmp_file_name = file_name.split('/')[4]
    file_name = str(tmp_file_name).split('_')

    return file_name

<img src="pics/logo.png" width="150"/>

![contributors](https://img.shields.io/github/contributors/tesemnikov-av/pelevin-recomendation-bot) ![last-commit](https://img.shields.io/github/last-commit/tesemnikov-av/Pelevin-recomendation-bot) ![repo-size](https://img.shields.io/github/repo-size/tesemnikov-av/Pelevin-recomendation-bot)

![watch](https://img.shields.io/github/watchers/tesemnikov-av/Pelevin-recomendation-bot?style=social) 



# Joyce : Anomaly Detection with Time Series Forecasting

This application predicted time series and finds deviations of current values from values predicted by the model. Using the difference in these values, we want to notice the abnormal load.

- Python3
- Zabbix
- Statsmodels (ARIMA)

Dependencies
~~~~~~~~~~~~

Joyce requires:

- Python (>= |PythonMinVersion|)
- NumPy (>= |NumPyMinVersion|)
- SciPy (>= |SciPyMinVersion|)
- Statmodels (>= |SciPyMinVersion|)

## Installation

Snorkel requires Python 3.6 or later. To install Joyce, we recommend using `pip`:

```bash
pip install snorkel
```
## Configuration

```bash
# Set correct values for zabbix and influxdb 
>> vi joyce.conf
# and run app.py every 23:00 (for example)
>> crontab -e
```


![Exaple1](./pics/example1.png)
    
If the difference between the maximum and minimum values is less than threshold (for example 5), 
then we will predict the average value. Otherwise, the prediction algorithm goes crazy.
This is quite enough for us to detect anomalies.

![Exaple2](./pics/example2.png)
 
![Exaple3](./pics/example3.png)

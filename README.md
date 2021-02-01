# joyce-app : Anomaly Detection with Time Series Forecasting


This application predicted time series and finds deviations of current values from values predicted by the model. Using the difference in these values, we want to notice the abnormal load.

- Python3
- Zabbix
- Statsmodels (ARIMA)
    
Grafana | Restricted Demonstration Stand
------|------
link        |   Grafana: Restricted Demonstration Stand (none)
user       |   oper
password   |   oper

![Exaple1](./pics/example1.png)



If the difference between the maximum and minimum values is less than threshold (for example 5), 
then we will predict the average value. Otherwise, the prediction algorithm goes crazy.
This is quite enough for us to detect anomalies.

![Exaple2](./pics/example2.png)
 

![Exaple3](./pics/example3.png)

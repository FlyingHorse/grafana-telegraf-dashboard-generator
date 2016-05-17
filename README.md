# grafana-telegraf-dashboard-generator

This simple script written in python is used to build Grafana json dashboards for Telegraf Metrics.

## Main goal
Sharing Grafana panels for telegraf metrics.

## How it works
The script connect to an InfluxDB cluster and lookup for all measurments in the the specified database with the "--databases" parameter.
This parameter can be a regexp so the script will lookup in all databases matching the pattern.

Then if there is a serie matching a row, it will just concat the corresponding row.json to the resulting json file.
Here is the current series list:
 - execvarnish3
 - nginx
 - apache
 - phpfpm
 - httpjson_opcache
 - memcached
 - mysql
 - mongodb
 - redis
 - elasticsearch
 - passenger
 - rabbitmq

Feel free to add new json panels !

You can add your own "templating variables" and "annotations".
Just put them as json files in the "templates" and/or "annotations" directory and use the "--enable-templating" and/or "--enable-annotations"

You will find the resulting dashboards under the "dashboards" directory.
You can now import your json file in grafana :)

## Usage
```
usage: generator.py [-h] [--influxdb-user INFLUXUSER]
                    [--influxdb-passwd INFLUXPASSWD] [--databases DBS]
                    [--hosts HOSTS] [--dashboard-version DASHVERSION]
                    [--enable-templating] [--enable-annotations] [-v]
optional arguments:
  -h, --help            show this help message and exit
  --influxdb-user INFLUXUSER
                        InfluxDB Username. Should be admin *
  --influxdb-passwd INFLUXPASSWD
                        InfluxDB Username password.
  --databases DBS       InfluxDB Databases as regexp
  --hosts HOSTS         InfluxDB raft hosts.
  --dashboard-version DASHVERSION
                        Dashboard version to set.
  --enable-templating   Enable templates
  --enable-annotations  Enable annotations
  --ssl                 Use SSL for InfluxDB connection.
  --verify-ssl          Verify SSL when connecting to InfluxDB.
  -v, --verbose         Increase output verbosity
```

Example:
```
python generator.py --influxdb-user admin --influxdb-passwd password --databases '^telegraf_*' --hosts 10.24.1.22:8086,10.24.1.23:8086 --dashboard-version 3 --enable-templating --enable-annotations
```


## Requirements
Use influxdb version > 2.11.0 and Jinja2> 2.8
```
pip install influxdb
pip install Jinja2
```

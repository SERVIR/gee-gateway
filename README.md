# gee-gateway

[![Python: 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![SERVIR: Global](https://img.shields.io/badge/SERVIR-Global-green)](https://servirglobal.net)

A REST API designed to be used by [CEO (Collect Earth Online)](https://github.com/openforis/collect-earth-online) to interface with Google Earth Engine.

## INSTALLATION

Follow this guide for your operating system. https://chriswarrick.com/blog/2016/02/10/deploying-python-web-apps-with-nginx-and-uwsgi-emperor/

The following is a shorthand version for Debian / Ubuntu

### Global packages

```bash
sudo apt install python3 python3-venv uwsgi uwsgi-plugin-python3 nginx-full
```

### Python virtual environment

```bash
git clone https://github.com/SERVIR/gee-gateway.git
cd gee-gateway/
python3 -m venv --prompt ceo venv/
source venv/bin/activate
pip install -r requirements.txt
pip install earthengine-api --upgrade
sudo touch venv/uwsgi.log
deactivate
npm install
```

## CONFIGURATION

### CONFIG FILES

Edit the gee-gateway configuration file `gee-gateway/config.py`

Copy and configure the nginx config file `gee-gateway/nginx_files/gee.conf` into `/etc/nginx/sites-available/gee.conf`
```sh
sudo cp nginx_files/gee.conf /etc/nginx/sites-available/gee.conf
sudo ln -s /etc/nginx/sites-available/gee.conf /etc/nginx/sites-enabled/
sudo nano /etc/nginx/gee.conf
sudo service nginx restart
```


Copy and configure the uwsgi config file `gee-gateway/nginx_files/gee-gateway.ini` into `/etc/uwsgi-emperor/vassals/gee-gateway.ini`
```sh
sudo cp nginx_files/gee-gateway.ini /etc/uwsgi-emperor/vassals/gee-gateway.ini
sudo nano /etc/uwsgi-emperor/vassals/gee-gateway.ini
```

Copy empire service file `gee-gateway/nginx_files/uwsgi-gee.service` to `/etc/systemd/system/uwsgi-gee.service`
```sh
sudo cp nginx_files/uwsgi-gee.service /etc/systemd/system/uwsgi-gee.service
```

### PERMISSIONS

Set the owner of the gee-gateway folder to the same as uid/gid in gee-gateway.ini
```bash
sudo usermod -a -G ceo www-data
sudo chown -R www-data:ceo /ceo/gee-venv/
```

### HTTPS/HTTP

HTTP access for 127.0.0.1 is required when running next to ceo. The nginx.conf
template includes a skeleton for HTTP.

To have nginx reload when certificates are renewed by certbot, place a script
file in /etc/letsencrypt/renewal-hooks/deploy. The sh file will need executable
writes. Inside that file place the following line:

```bash
systemctl reload nginx
```

### EXECUTION

Enable

```bash
sudo systemctl daemon-reload
sudo systemctl enable nginx uwsgi-gee
sudo systemctl reload nginx
```

Start, Stop, Restart (note that nginx and uwsgi-gee are two different processes)

```bash
sudo systemctl start nginx uwsgi-gee
sudo systemctl stop nginx uwsgi-gee
sudo systemctl restart nginx uwsgi-gee
```

## USE

Navigate to https://localhost:8888/ to interact with the web ui.

Have running alongside CEO.

curl https://localhost:8888/timeSeriesIndex -d '{"collectionNameTimeSeries":"LANDSAT/LC8_L1T_32DAY_NDWI","geometry":[[98.6270686247256,12.804422919455547],[98.62753901527437,12.804422919455547],[98.62753901527437,12.804714380460211],[98.6270686247256,12.804714380460211],[98.6270686247256,12.804422919455547]],"indexName":"NDWI","dateFromTimeSeries":"2015-01-01","dateToTimeSeries":"2017-12-31","reducer":"","scale":30,"point":[98.62730382,12.80456865],"start":"","end":"","band":"","dataType":""}'

curl https://localhost/geo-dash/gateway-request -d '{"collectionNameTimeSeries":"LANDSAT/LC8_L1T_32DAY_NDWI","geometry":[[98.6270686247256,12.804422919455547],[98.62753901527437,12.804422919455547],[98.62753901527437,12.804714380460211],[98.6270686247256,12.804714380460211],[98.6270686247256,12.804422919455547]],"indexName":"NDWI","dateFromTimeSeries":"2015-01-01","dateToTimeSeries":"2017-12-31","reducer":"","scale":30,"path":"timeSeriesIndex","point":[98.62730382,12.80456865],"start":"","end":"","band":"","dataType":""}'

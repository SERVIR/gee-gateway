# gee-gateway

[![Python: 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![SERVIR: Global](https://img.shields.io/badge/SERVIR-Global-green)](https://servirglobal.net)

A REST API designed to be used by [CEO (Collect Earth Online)](https://github.com/openforis/collect-earth-online) to interface with Google Earth Engine.

## INSTALLATION

### Global packages

```sh
sudo apt install python3 python3-venv uwsgi uwsgi-plugin-python3
```

### Python virtual environment

```sh
git clone https://github.com/SERVIR/gee-gateway.git
cd gee-gateway/
python3 -m venv --prompt ceo venv/
source venv/bin/activate
pip install -r requirements.txt
pip install earthengine-api --upgrade
deactivate
```

### PERMISSIONS

Set the owner of the gee-gateway folder to the same as uid/gid in gee-gateway.ini

```sh
sudo chown -R ceo:ceo gee-gateway/
```

## CONFIGURATION

### DEVELOPMENT

Run directly from uWsgi.

```sh
cd gee-gateway/
uwsgi --ini gee-uwsgi.ini
```

*If you do not wish to install wWsgi globally, you can install it within the virtual environment.

```sh
cd gee-gateway/
source venv/bin/activate
pip install uwsgi
uwsgi --ini gee-uwsgi.ini
```

### PRODUCTION

Edit the gee-gateway configuration file `gee-gateway/config.py`

Copy uwsgi service file `gee-gateway/nginx_files/gee-uwsgi.service` to `/etc/systemd/system/gee-uwsgi.service` and update path to gee-uwsgi.ini

```sh
sudo cp nginx_files/gee-uwsgi.service /etc/systemd/system/gee-uwsgi.service
sudo nano /etc/systemd/system/gee-uwsgi.service
```

Enable using systemd process

```sh
sudo systemctl daemon-reload
sudo systemctl enable gee-uwsgi
sudo systemctl start gee-uwsgi
```

### LOGS

```sh
less +G gee-gateway.logs
sudo journalctl -e -u gee-uwsgi
```

## USE

You can execute a test command using curl.

curl http://localhost:8888/timeSeriesByAsset -d '{"assetName":"LANDSAT/LC8_L1T_32DAY_NDWI","geometry":[[98.6270686247256,12.804422919455547],[98.62753901527437,12.804422919455547],[98.62753901527437,12.804714380460211],[98.6270686247256,12.804714380460211],[98.6270686247256,12.804422919455547]],"indexName":"NDWI","startDate":"2015-01-01","endDate":"2017-12-31","reducer":"median","scale":30,"point":[98.62730382,12.80456865], "band":"B3"}' -H "Content-type: application/json"

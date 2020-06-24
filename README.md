# gee-gateway

[![Python: 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A REST API designed to be used by [CEO (Collect Earth Online)](https://github.com/openforis/collect-earth-online) to interface with Google Earth Engine.

## INSTALLATION

Follow this guide for your operating system. https://chriswarrick.com/blog/2016/02/10/deploying-python-web-apps-with-nginx-and-uwsgi-emperor/

The following is a shorthand version for Debian / Ubuntu

### Global packages

```bash
sudo apt install python3 python3-venv uwsgi uwsgi-emperor uwsgi-plugin-python3 nginx-full
```

### Python virtual environment

```bash
python3 -m venv --prompt gee-gateway /ceo/gee-venv/
source /ceo/gee-venv/bin/activate
pip install -r requirements.txt
git clone https://github.com/openforis/collect-earth-online.git /ceo/gee-venv/
sudo touch /ceo/gee-venv/uwsgi.log
deactivate
```

## CONFIGURATION

Edit the gee-gateway configuration file `gee-gateway/config.py`

Copy and configure the nginx config file `gee-gateway/nginx_files/nginx.conf` into `/etc/nginx/nginx.conf`
```bash
sudo cp nginx_files/nginx.conf /etc/nginx/nginx.conf
sudo nano /etc/nginx/nginx.conf
```


Copy and configure the uwsgi config file `gee-gateway/nginx_files/gee-gateway.ini` into `/etc/uwsgi-emperor/vassals/gee-gateway.ini`
```bash
sudo cp nginx_files/gee-gateway.ini /etc/uwsgi-emperor/vassals/gee-gateway.ini
sudo nano /etc/uwsgi-emperor/vassals/gee-gateway.ini
```

Copy empire service file `gee-gateway/nginx_files/emperor.uwsgi.service` to `/etc/systemd/system/emperor.uwsgi.service`
```bash
sudo cp nginx_files/emperor.uwsgi.service /etc/systemd/system/emperor.uwsgi.service
```

## PERMISSIONS

Set the owner of the gee-gateway folder to the same as uid/gid in gee-gateway.ini
```bash
sudo usermod -a -G ceo www-data
sudo chown -R www-data:www-data /ceo/gee-venv/
```

## EXECUTION

Disable built in emperor service for Ubuntu

```bash
systemctl stop uwsgi-emperor
systemctl disable uwsgi-emperor
```

Enable

```bash
sudo systemctl daemon-reload
sudo systemctl enable nginx emperor.uwsgi
sudo systemctl reload nginx
```

Start, Stop, Restart

```bash
sudo systemctl start nginx emperor.uwsgi
sudo systemctl stop nginx emperor.uwsgi
sudo systemctl restart nginx emperor.uwsgi
```

## USAGE

```bash
usage: run.py [-h] [--gmaps_api_key GMAPS_API_KEY] [--ee_account EE_ACCOUNT]
              [--ee_key_path EE_KEY_PATH]

optional arguments:
  -h, --help            show this help message and exit
  --gmaps_api_key GMAPS_API_KEY
                        Google Maps API key
  --ee_account EE_ACCOUNT
                        Google Earth Engine account
  --ee_key_path EE_KEY_PATH
                        Google Earth Engine key path
```

## DOCUMENTATION

```bash
pip install sphinx
pip install sphinxcontrib-httpdomain
```

From project root directory

```bash
sphinx-build -aE -b html . static/docs
```

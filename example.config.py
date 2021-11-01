DEBUG = False
PORT = 8888
HOST = '0.0.0.0'
CERT = '/etc/letsencrypt/live/{domain}/fullchain.pem'
KEY = '/etc/letsencrypt/live/{domain}/privkey.pem'

CO_ORIGINS = '*'

EE_ACCOUNT = '<EE_ACCOUNT>'
EE_KEY_PATH = '<EE_KEY_PATH>'

import logging
LOGGING_LEVEL = logging.INFO

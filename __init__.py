from flask import Blueprint
import os
import sys
sys.path.append(os.path.dirname(__file__))

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


gee_gateway = Blueprint(
    'gee_gateway',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static/gee_gateway'
)

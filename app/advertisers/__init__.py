from flask import Blueprint

bp = Blueprint('advertisers', __name__)

from app.advertisers import routes
from flask import Blueprint

bp = Blueprint('activities', __name__)

from app.activities import routes
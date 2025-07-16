from flask import Blueprint

bp = Blueprint('contacts', __name__)

from app.contacts import routes
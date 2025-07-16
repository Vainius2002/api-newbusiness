from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config
from app.models import db, User

migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.advertisers import bp as advertisers_bp
    app.register_blueprint(advertisers_bp, url_prefix='/advertisers')
    
    from app.activities import bp as activities_bp
    app.register_blueprint(activities_bp, url_prefix='/activities')
    
    from app.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')
    
    from app.contacts import bp as contacts_bp
    app.register_blueprint(contacts_bp, url_prefix='/contacts')
    
    # Create upload folder
    import os
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    return app
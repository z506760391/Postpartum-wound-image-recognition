from flask import Flask, render_template
from models.database import db
from config import config_map
import os

def create_app(config_name=None):
    app = Flask(__name__)
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config_map.get(config_name, config_map['default']))

    db.init_app(app)

    with app.app_context():
        db.create_all()
        for folder in [app.config['UPLOAD_FOLDER'], app.config['LOG_FOLDER'], app.config['MODEL_SAVE_PATH']]:
            os.makedirs(folder, exist_ok=True)

    from routes.patient import patient_bp
    from routes.analysis import analysis_bp
    from routes.learning import learning_bp
    from routes.admin import admin_bp
    app.register_blueprint(patient_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(admin_bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.errorhandler(404)
    def not_found(e):
        return render_template('base.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('base.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)

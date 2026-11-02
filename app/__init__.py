import os
from flask import Flask
from app.config import Config
from app.extensions import db, login_manager

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inisialisasi Ekstensi
    db.init_app(app)
    login_manager.init_app(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.teachers import teachers_bp
    from app.routes.materials import materials_bp
    from app.routes.rubrics import rubrics_bp
    from app.routes.submissions import submissions_bp
    from app.routes.evaluations import evaluations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(teachers_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(rubrics_bp)
    app.register_blueprint(submissions_bp)
    app.register_blueprint(evaluations_bp)

    # Pastikan direktori uploads tersedia
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Error Handler 413 (Kelebihan Kapasitas Berkas / > 100 MB)
    @app.errorhandler(413)
    def request_entity_too_large(error):
        from flask import flash, redirect, url_for
        flash('Ukuran berkas melebihi batas maksimal kapasitas unggah sistem (Maksimal 100 MB). Silakan kompres berkas atau pilih yang lebih kecil.', 'danger')
        return redirect(url_for('submissions.upload'))

    # Custom Jinja Filters
    @app.template_filter('format_datetime')
    def format_datetime(val, fmt='%d %b %Y %H:%M'):
        if val is None:
            return '-'
        return val.strftime(fmt)

    @app.template_filter('format_date')
    def format_date(val, fmt='%d %b %Y'):
        if val is None:
            return '-'
        return val.strftime(fmt)

    @app.route('/health')
    def health_check():
        return {"status": "ok", "database": "connected"}, 200

    return app

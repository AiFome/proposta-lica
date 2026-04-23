import os, json, secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import LoginManager, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()
from models import db, bcrypt, User, Plan, UserConfig, SiteConfig

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(64))
    app.config['SESSION_COOKIE_SECURE']   = os.environ.get('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = int(os.environ.get('PERMANENT_SESSION_LIFETIME', 86400))
    app.config['MAX_CONTENT_LENGTH'] = 52428800
    # Render usa postgres:// mas SQLAlchemy exige postgresql://
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///proposta_lic.db')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True, 'pool_recycle': 300}
    app.config['MAIL_SERVER']   = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT']     = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS']  = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

    db.init_app(app)
    bcrypt.init_app(app)
    Migrate(app, db)
    mail = Mail(app)
    app.mail = mail

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    limiter = Limiter(key_func=get_remote_address, app=app,
        default_limits=['200 per day', '50 per hour'],
        storage_uri=os.environ.get('REDIS_URL', 'memory://'))
    app.limiter = limiter

    @app.after_request
    def set_security_headers(r):
        r.headers['X-Content-Type-Options'] = 'nosniff'
        r.headers['X-Frame-Options']        = 'SAMEORIGIN'
        r.headers['X-XSS-Protection']       = '1; mode=block'
        r.headers['Referrer-Policy']        = 'strict-origin-when-cross-origin'
        r.headers['Permissions-Policy']     = 'geolocation=(), microphone=(), camera=()'
        if os.environ.get('FLASK_ENV') == 'production':
            r.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return r

    from routes.auth    import auth_bp
    from routes.app_    import app_bp
    from routes.admin   import admin_bp
    from routes.payment import payment_bp
    from routes.api     import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(app_bp)
    app.register_blueprint(admin_bp,   url_prefix='/admin')
    app.register_blueprint(payment_bp, url_prefix='/pagamento')
    app.register_blueprint(api_bp,     url_prefix='/api')

    @app.errorhandler(404)
    def e404(e): return render_template('errors/404.html'), 404
    @app.errorhandler(403)
    def e403(e): return render_template('errors/403.html'), 403
    @app.errorhandler(500)
    def e500(e): return render_template('errors/500.html'), 500
    @app.errorhandler(429)
    def e429(e): return render_template('errors/429.html'), 429

    with app.app_context():
        db.create_all()
        _dados_iniciais()
        _migrar_banco()

    return app


def _dados_iniciais():
    if not Plan.query.first():
        planos = [
            Plan(nome='Básico', slug='basico', preco_mensal=49.90, preco_anual=499.00,
                 max_editais=5, max_produtos=50, max_docs_mb=200, tem_ia=False, ordem=1,
                 descricao='Ideal para iniciantes',
                 recursos=json.dumps(['5 editais/mês','50 produtos','200MB docs','Geração proposta','ZIP habilitação'])),
            Plan(nome='Profissional', slug='profissional', preco_mensal=99.90, preco_anual=999.00,
                 max_editais=30, max_produtos=500, max_docs_mb=1024, tem_ia=True, destaque=True, ordem=2,
                 descricao='Para empresas em crescimento',
                 recursos=json.dumps(['30 editais/mês','500 produtos','1GB docs','IA integrada','ZIP habilitação','Suporte prioritário'])),
            Plan(nome='Empresarial', slug='empresarial', preco_mensal=199.90, preco_anual=1999.00,
                 max_editais=999, max_produtos=9999, max_docs_mb=5120, tem_ia=True, ordem=3,
                 descricao='Para grandes operações',
                 recursos=json.dumps(['Editais ilimitados','Produtos ilimitados','5GB docs','IA integrada','ZIP habilitação','Suporte dedicado'])),
        ]
        for p in planos: db.session.add(p)
        db.session.commit()

    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@proposta-lic.com.br')
    if not User.query.filter_by(email=admin_email).first():
        admin = User(nome='Administrador', email=admin_email, is_admin=True,
                     is_active=True, email_verified=True, subscription_status='active',
                     plan_end=datetime.utcnow() + timedelta(days=36500))
        admin.set_password(os.environ.get('ADMIN_PASSWORD', 'Admin@2024!'))
        db.session.add(admin)
        db.session.add(UserConfig(user=admin, razao_social='Administrador'))
        db.session.commit()

    defaults = [('trial_duration','3600','int'),('site_nome','PropostaLic','string'),
                ('site_slogan','Gestão de propostas para licitações','string'),
                ('manutencao','false','bool'),('cadastro_aberto','true','bool')]
    for chave, valor, tipo in defaults:
        if not SiteConfig.query.filter_by(chave=chave).first():
            db.session.add(SiteConfig(chave=chave, valor=valor, tipo=tipo))
    db.session.commit()


def _migrar_banco():
    """Adiciona colunas novas sem quebrar o banco existente."""
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            # Adicionar colunas novas na user_configs se não existirem
            colunas_novas = [
                ("user_configs", "ordem_produto",     "VARCHAR(100) DEFAULT 'nome,fabricante,gramatura'"),
                ("user_configs", "separador_produto",  "VARCHAR(20)  DEFAULT ' / '"),
            ]
            for tabela, coluna, tipo in colunas_novas:
                try:
                    conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS {coluna} {tipo}"))
                    conn.commit()
                except Exception:
                    conn.rollback()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'Migração: {e}')


def requer_plano(f):
    @wraps(f)
    def dec(*a, **kw):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.pode_usar:
            flash('Seu acesso expirou. Contrate um plano para continuar.', 'warning')
            return redirect(url_for('payment.planos'))
        return f(*a, **kw)
    return dec


def requer_admin(f):
    @wraps(f)
    def dec(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*a, **kw)
    return dec


def log_admin(acao, detalhe=''):
    try:
        from models import AdminLog
        db.session.add(AdminLog(admin_id=current_user.id, acao=acao, detalhe=detalhe, ip=request.remote_addr))
        db.session.commit()
    except Exception: pass


def log_login(user, sucesso, motivo=''):
    try:
        from models import LoginLog
        db.session.add(LoginLog(user_id=user.id, ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent','')[:500], sucesso=sucesso, motivo=motivo))
        db.session.commit()
    except Exception: pass


if __name__ == '__main__':
    create_app().run(debug=False, host='0.0.0.0', port=5000)

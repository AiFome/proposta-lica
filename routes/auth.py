import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, UserConfig, PasswordResetToken, SiteConfig
import os

auth_bp = Blueprint('auth', __name__)

def _trial_dur():
    try: return int(SiteConfig.get('trial_duration', 3600))
    except: return int(os.environ.get('TRIAL_DURATION', 3600))

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard') if current_user.is_admin else url_for('app_.dashboard'))
    plans = __import__('models').Plan.query.filter_by(ativo=True).order_by(__import__('models').Plan.ordem).all()
    return render_template('landing.html', planos=plans)

@auth_bp.route('/registro', methods=['GET','POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('app_.dashboard'))
    if SiteConfig.get('cadastro_aberto','true') == 'false':
        flash('Novos cadastros estão temporariamente suspensos.', 'warning')
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        nome  = request.form.get('nome','').strip()
        email = request.form.get('email','').strip().lower()
        senha = request.form.get('senha','')
        conf  = request.form.get('confirmar_senha','')
        termos= request.form.get('termos')
        erros = []
        if len(nome) < 3: erros.append('Nome deve ter pelo menos 3 caracteres.')
        if '@' not in email: erros.append('E-mail inválido.')
        if len(senha) < 8: erros.append('Senha deve ter pelo menos 8 caracteres.')
        if not any(c.isupper() for c in senha): erros.append('Senha deve ter pelo menos uma maiúscula.')
        if not any(c.isdigit() for c in senha): erros.append('Senha deve ter pelo menos um número.')
        if senha != conf: erros.append('Senhas não coincidem.')
        if not termos: erros.append('Aceite os Termos de Uso.')
        if User.query.filter_by(email=email).first(): erros.append('E-mail já cadastrado.')
        if erros:
            for e in erros: flash(e, 'danger')
            return render_template('auth/registro.html', nome=nome, email=email)
        user = User(nome=nome, email=email)
        user.set_password(senha)
        user.set_trial(_trial_dur())
        user.email_token = secrets.token_urlsafe(32)
        db.session.add(user)
        db.session.flush()
        db.session.add(UserConfig(user_id=user.id))
        db.session.commit()
        _enviar_verificacao(user)
        login_user(user, remember=False)
        _log_login(user, True, 'registro')
        flash(f'Bem-vindo(a), {nome}! Você tem {_trial_dur()//60} minutos de teste gratuito.', 'success')
        return redirect(url_for('app_.dashboard'))
    return render_template('auth/registro.html')

@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard') if current_user.is_admin else url_for('app_.dashboard'))
    if request.method == 'POST':
        email  = request.form.get('email','').strip().lower()
        senha  = request.form.get('senha','')
        lembrar= bool(request.form.get('lembrar'))
        user   = User.query.filter_by(email=email).first()
        if not user or not user.check_password(senha):
            if user: _log_login(user, False, 'senha incorreta')
            flash('E-mail ou senha incorretos.', 'danger')
            return render_template('auth/login.html', email=email)
        if not user.is_active:
            _log_login(user, False, 'conta bloqueada')
            flash('Conta bloqueada. Entre em contato com o suporte.', 'danger')
            return render_template('auth/login.html', email=email)
        if user.totp_enabled:
            session['2fa_user_id'] = user.id
            session['2fa_lembrar'] = lembrar
            return redirect(url_for('auth.verificar_2fa'))
        login_user(user, remember=lembrar)
        user.last_login = datetime.utcnow()
        user.login_count += 1
        user.ip_ultimo = request.remote_addr
        db.session.commit()
        _log_login(user, True)
        nxt = request.args.get('next')
        return redirect(nxt or (url_for('admin.dashboard') if user.is_admin else url_for('app_.dashboard')))
    return render_template('auth/login.html')

@auth_bp.route('/2fa', methods=['GET','POST'])
def verificar_2fa():
    uid = session.get('2fa_user_id')
    if not uid: return redirect(url_for('auth.login'))
    user = User.query.get(uid)
    if not user: return redirect(url_for('auth.login'))
    if request.method == 'POST':
        import pyotp
        if pyotp.TOTP(user.totp_secret).verify(request.form.get('codigo','').strip(), valid_window=1):
            lembrar = session.pop('2fa_lembrar', False)
            session.pop('2fa_user_id', None)
            login_user(user, remember=lembrar)
            user.last_login = datetime.utcnow()
            user.login_count += 1
            db.session.commit()
            _log_login(user, True, '2fa')
            return redirect(url_for('admin.dashboard') if user.is_admin else url_for('app_.dashboard'))
        flash('Código inválido.', 'danger')
    return render_template('auth/2fa.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu com segurança.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/verificar-email/<token>')
def verificar_email(token):
    user = User.query.filter_by(email_token=token).first()
    if user:
        user.email_verified = True; user.email_token = None; db.session.commit()
        flash('E-mail verificado com sucesso!', 'success')
    else:
        flash('Link inválido ou expirado.', 'danger')
    return redirect(url_for('app_.dashboard') if current_user.is_authenticated else url_for('auth.login'))

@auth_bp.route('/esqueci-senha', methods=['GET','POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        user  = User.query.filter_by(email=email).first()
        flash('Se esse e-mail estiver cadastrado, você receberá as instruções.', 'info')
        if user:
            token = secrets.token_urlsafe(32)
            db.session.add(PasswordResetToken(user_id=user.id, token=token,
                expires_at=datetime.utcnow()+timedelta(hours=1)))
            db.session.commit()
            _enviar_reset(user, token)
        return redirect(url_for('auth.login'))
    return render_template('auth/esqueci_senha.html')

@auth_bp.route('/redefinir-senha/<token>', methods=['GET','POST'])
def redefinir_senha(token):
    rst = PasswordResetToken.query.filter_by(token=token).first()
    if not rst or rst.expirado:
        flash('Link inválido ou expirado.', 'danger')
        return redirect(url_for('auth.esqueci_senha'))
    if request.method == 'POST':
        senha = request.form.get('senha','')
        conf  = request.form.get('confirmar_senha','')
        if len(senha) < 8: flash('Senha deve ter pelo menos 8 caracteres.', 'danger'); return render_template('auth/redefinir_senha.html', token=token)
        if senha != conf: flash('Senhas não coincidem.', 'danger'); return render_template('auth/redefinir_senha.html', token=token)
        User.query.get(rst.user_id).set_password(senha)
        rst.used = True; db.session.commit()
        flash('Senha redefinida! Faça login.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/redefinir_senha.html', token=token)

def _log_login(user, sucesso, motivo=''):
    try:
        from models import LoginLog
        db.session.add(LoginLog(user_id=user.id, ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent','')[:500], sucesso=sucesso, motivo=motivo))
        db.session.commit()
    except Exception: pass

def _enviar_verificacao(user):
    try:
        from flask_mail import Message
        url = url_for('auth.verificar_email', token=user.email_token, _external=True)
        msg = Message('Verifique seu e-mail - PropostaLic', recipients=[user.email])
        msg.html = render_template('emails/verificacao.html', user=user, url=url)
        current_app.mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Email verificação: {e}')

def _enviar_reset(user, token):
    try:
        from flask_mail import Message
        url = url_for('auth.redefinir_senha', token=token, _external=True)
        msg = Message('Redefinir senha - PropostaLic', recipients=[user.email])
        msg.html = render_template('emails/reset_senha.html', user=user, url=url)
        current_app.mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Email reset: {e}')

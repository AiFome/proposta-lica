from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
import json, uuid

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id             = db.Column(db.Integer, primary_key=True)
    uuid           = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    nome           = db.Column(db.String(120), nullable=False)
    email          = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash  = db.Column(db.String(256), nullable=False)
    telefone       = db.Column(db.String(20))
    empresa        = db.Column(db.String(150))
    cnpj           = db.Column(db.String(18))
    is_active      = db.Column(db.Boolean, default=True)
    is_admin       = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)
    email_token    = db.Column(db.String(64))
    totp_secret    = db.Column(db.String(32))
    totp_enabled   = db.Column(db.Boolean, default=False)
    trial_start    = db.Column(db.DateTime, default=datetime.utcnow)
    trial_end      = db.Column(db.DateTime)
    plan_id        = db.Column(db.Integer, db.ForeignKey('plans.id'))
    plan_start     = db.Column(db.DateTime)
    plan_end       = db.Column(db.DateTime)
    stripe_customer_id     = db.Column(db.String(64))
    stripe_subscription_id = db.Column(db.String(64))
    subscription_status    = db.Column(db.String(20), default='trial')
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login     = db.Column(db.DateTime)
    login_count    = db.Column(db.Integer, default=0)
    ip_ultimo      = db.Column(db.String(45))

    plan      = db.relationship('Plan', back_populates='users')
    config    = db.relationship('UserConfig', back_populates='user', uselist=False, cascade='all, delete-orphan')
    invoices  = db.relationship('Invoice', back_populates='user', cascade='all, delete-orphan')
    login_logs= db.relationship('LoginLog', back_populates='user', cascade='all, delete-orphan')
    documentos= db.relationship('UserDocument', back_populates='user', cascade='all, delete-orphan')
    editais   = db.relationship('UserEdital', back_populates='user', cascade='all, delete-orphan')
    produtos  = db.relationship('UserProduto', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, p): self.password_hash = bcrypt.generate_password_hash(p).decode('utf-8')
    def check_password(self, p): return bcrypt.check_password_hash(self.password_hash, p)
    def set_trial(self, secs=3600):
        self.trial_start = datetime.utcnow()
        self.trial_end   = datetime.utcnow() + timedelta(seconds=secs)
        self.subscription_status = 'trial'

    @property
    def trial_restante_segundos(self):
        if self.trial_end and self.subscription_status == 'trial':
            return max(0, int((self.trial_end - datetime.utcnow()).total_seconds()))
        return 0

    @property
    def trial_expirado(self):
        return datetime.utcnow() > self.trial_end if self.trial_end else True

    @property
    def pode_usar(self):
        if self.is_admin: return True
        if not self.is_active: return False
        if self.subscription_status == 'active' and self.plan_end and datetime.utcnow() < self.plan_end:
            return True
        if self.subscription_status == 'trial' and not self.trial_expirado:
            return True
        return False

    @property
    def status_display(self):
        if self.is_admin: return ('Admin', 'purple')
        if self.subscription_status == 'active': return ('Ativo', 'green')
        if self.subscription_status == 'trial':
            return ('Trial Expirado', 'red') if self.trial_expirado else ('Trial', 'blue')
        if self.subscription_status == 'past_due': return ('Pagamento Pendente', 'orange')
        if self.subscription_status == 'canceled': return ('Cancelado', 'gray')
        return ('Bloqueado', 'red')

    def to_dict(self):
        return {'id': self.id, 'uuid': self.uuid, 'nome': self.nome, 'email': self.email,
                'empresa': self.empresa, 'is_admin': self.is_admin, 'is_active': self.is_active,
                'subscription_status': self.subscription_status,
                'plan': self.plan.nome if self.plan else None,
                'trial_end': self.trial_end.isoformat() if self.trial_end else None,
                'plan_end': self.plan_end.isoformat() if self.plan_end else None,
                'created_at': self.created_at.isoformat()}


class Plan(db.Model):
    __tablename__ = 'plans'
    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(50), nullable=False)
    slug          = db.Column(db.String(30), unique=True)
    descricao     = db.Column(db.Text)
    preco_mensal  = db.Column(db.Float, nullable=False)
    preco_anual   = db.Column(db.Float)
    stripe_price_mensal = db.Column(db.String(64))
    stripe_price_anual  = db.Column(db.String(64))
    max_editais   = db.Column(db.Integer, default=10)
    max_produtos  = db.Column(db.Integer, default=100)
    max_docs_mb   = db.Column(db.Integer, default=500)
    tem_ia        = db.Column(db.Boolean, default=True)
    tem_zip       = db.Column(db.Boolean, default=True)
    destaque      = db.Column(db.Boolean, default=False)
    ativo         = db.Column(db.Boolean, default=True)
    ordem         = db.Column(db.Integer, default=0)
    recursos      = db.Column(db.Text, default='[]')
    users         = db.relationship('User', back_populates='plan')
    def get_recursos(self):
        try: return json.loads(self.recursos)
        except: return []
    def set_recursos(self, lista): self.recursos = json.dumps(lista, ensure_ascii=False)


class UserConfig(db.Model):
    __tablename__ = 'user_configs'
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    razao_social   = db.Column(db.String(200))
    cnpj           = db.Column(db.String(18))
    ie             = db.Column(db.String(30))
    telefone       = db.Column(db.String(20))
    email_comercial= db.Column(db.String(120))
    endereco       = db.Column(db.String(300))
    banco          = db.Column(db.String(200))
    representante  = db.Column(db.String(150))
    cpfrg          = db.Column(db.String(30))
    modelo_validade= db.Column(db.Text, default='60 (SESSENTA) DIAS, A CONTAR DA DATA DA APRESENTACAO.')
    modelo_prazo   = db.Column(db.Text, default='CONFORME EDITAL.')
    modelo_local   = db.Column(db.Text, default='CONFORME EDITAL.')
    modelo_decl    = db.Column(db.Text)
    modelo_obs     = db.Column(db.Text)
    anthropic_key_enc = db.Column(db.Text)
    ordem_produto      = db.Column(db.String(100), default='nome,fabricante,gramatura')
    separador_produto  = db.Column(db.String(20),  default=' / ')
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user           = db.relationship('User', back_populates='config')
    def to_dict(self):
        return {'razao_social': self.razao_social, 'cnpj': self.cnpj, 'ie': self.ie,
                'telefone': self.telefone, 'email_comercial': self.email_comercial,
                'endereco': self.endereco, 'banco': self.banco, 'representante': self.representante,
                'cpfrg': self.cpfrg, 'modelo_validade': self.modelo_validade,
                'modelo_prazo': self.modelo_prazo, 'modelo_local': self.modelo_local,
                'modelo_decl': self.modelo_decl, 'modelo_obs': self.modelo_obs,
                'ordem_produto': self.ordem_produto or 'nome,fabricante,gramatura',
                'separador_produto': self.separador_produto or ' / '}


class UserDocument(db.Model):
    __tablename__ = 'user_documents'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    doc_key    = db.Column(db.String(60))
    label      = db.Column(db.String(200))
    filename   = db.Column(db.String(255))
    mimetype   = db.Column(db.String(100))
    tamanho    = db.Column(db.Integer)
    dados      = db.Column(db.LargeBinary)
    categoria  = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user       = db.relationship('User', back_populates='documentos')


class UserEdital(db.Model):
    __tablename__ = 'user_editais'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    nome       = db.Column(db.String(255))
    pregao     = db.Column(db.String(50))
    processo   = db.Column(db.String(50))
    prefeitura = db.Column(db.String(200))
    plataforma = db.Column(db.String(200))
    objeto     = db.Column(db.Text)
    exigencias = db.Column(db.Text, default='[]')
    itens      = db.Column(db.Text, default='[]')
    dados_pdf  = db.Column(db.LargeBinary)
    tamanho    = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship('User', back_populates='editais')
    def get_exigencias(self):
        try: return json.loads(self.exigencias)
        except: return []
    def get_itens(self):
        try: return json.loads(self.itens)
        except: return []


class UserProduto(db.Model):
    __tablename__ = 'user_produtos'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    nome       = db.Column(db.String(200), nullable=False)
    fabricante = db.Column(db.String(150))
    gramatura  = db.Column(db.String(50))
    categoria  = db.Column(db.String(100))
    anvisa     = db.Column(db.String(50))
    codigo     = db.Column(db.String(50))
    obs        = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user       = db.relationship('User', back_populates='produtos')
    def to_dict(self):
        return {'id': self.id, 'nome': self.nome, 'fabricante': self.fabricante,
                'gramatura': self.gramatura, 'categoria': self.categoria,
                'anvisa': self.anvisa, 'codigo': self.codigo, 'obs': self.obs}


class Invoice(db.Model):
    __tablename__ = 'invoices'
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    plan_id        = db.Column(db.Integer, db.ForeignKey('plans.id'))
    stripe_invoice_id     = db.Column(db.String(64))
    stripe_payment_intent = db.Column(db.String(64))
    valor          = db.Column(db.Float)
    moeda          = db.Column(db.String(3), default='BRL')
    status         = db.Column(db.String(20))
    periodo        = db.Column(db.String(10))
    data_pagamento = db.Column(db.DateTime)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    user           = db.relationship('User', back_populates='invoices')
    plan           = db.relationship('Plan')


class LoginLog(db.Model):
    __tablename__ = 'login_logs'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    ip         = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    sucesso    = db.Column(db.Boolean)
    motivo     = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship('User', back_populates='login_logs')


class AdminLog(db.Model):
    __tablename__ = 'admin_logs'
    id         = db.Column(db.Integer, primary_key=True)
    admin_id   = db.Column(db.Integer, db.ForeignKey('users.id'))
    acao       = db.Column(db.String(100))
    detalhe    = db.Column(db.Text)
    ip         = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'))
    token      = db.Column(db.String(64), unique=True)
    expires_at = db.Column(db.DateTime)
    used       = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    @property
    def expirado(self): return datetime.utcnow() > self.expires_at or self.used


class SiteConfig(db.Model):
    __tablename__ = 'site_configs'
    id    = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Text)
    tipo  = db.Column(db.String(20), default='string')

    @staticmethod
    def get(chave, default=None):
        cfg = SiteConfig.query.filter_by(chave=chave).first()
        if not cfg: return default
        if cfg.tipo == 'int': return int(cfg.valor)
        if cfg.tipo == 'bool': return cfg.valor.lower() == 'true'
        if cfg.tipo == 'json':
            try: return json.loads(cfg.valor)
            except: return default
        return cfg.valor

    @staticmethod
    def set(chave, valor, tipo='string'):
        cfg = SiteConfig.query.filter_by(chave=chave).first()
        if not cfg:
            cfg = SiteConfig(chave=chave, tipo=tipo)
            db.session.add(cfg)
        cfg.valor = json.dumps(valor) if tipo == 'json' else str(valor)
        db.session.commit()

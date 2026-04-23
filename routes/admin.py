import os, json, urllib.request, urllib.error
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from models import db, User, Plan, Invoice, LoginLog, AdminLog, SiteConfig, UserDocument, UserEdital

admin_bp = Blueprint('admin', __name__)

def _chk():
    if not current_user.is_authenticated or not current_user.is_admin: abort(403)

def _log(acao, detalhe=''):
    try:
        db.session.add(AdminLog(admin_id=current_user.id, acao=acao, detalhe=detalhe, ip=request.remote_addr))
        db.session.commit()
    except Exception: pass

def _api(payload, apikey, timeout=120):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=data,
        headers={'Content-Type':'application/json','x-api-key':apikey,'anthropic-version':'2023-06-01','anthropic-beta':'pdfs-2024-09-25'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        corpo = e.read().decode('utf-8', errors='replace')
        try: msg = json.loads(corpo).get('error',{}).get('message', corpo)
        except: msg = corpo
        return None, f'HTTP {e.code}: {msg}'
    except Exception as e:
        return None, str(e)

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@admin_bp.route('/')
@login_required
def dashboard():
    _chk()
    hoje = datetime.utcnow(); semana = hoje - timedelta(days=7)
    stats = {
        'total_usuarios': User.query.filter_by(is_admin=False).count(),
        'usuarios_ativos': User.query.filter_by(subscription_status='active').count(),
        'usuarios_trial': User.query.filter_by(subscription_status='trial').count(),
        'novos_semana': User.query.filter(User.created_at>=semana, User.is_admin==False).count(),
        'receita_mes': db.session.query(func.sum(Invoice.valor)).filter(
            Invoice.status=='paid', Invoice.created_at>=hoje.replace(day=1)).scalar() or 0,
        'total_editais': UserEdital.query.count(),
        'total_docs': UserDocument.query.count(),
    }
    recentes = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).limit(10).all()
    logs = AdminLog.query.order_by(AdminLog.created_at.desc()).limit(20).all()
    return render_template('admin/dashboard.html', stats=stats, recentes=recentes, logs=logs)

@admin_bp.route('/usuarios')
@login_required
def usuarios():
    _chk()
    q = request.args.get('q',''); status = request.args.get('status',''); page = request.args.get('page',1,type=int)
    query = User.query.filter_by(is_admin=False)
    if q: query = query.filter((User.nome.ilike(f'%{q}%'))|(User.email.ilike(f'%{q}%'))|(User.empresa.ilike(f'%{q}%')))
    if status: query = query.filter_by(subscription_status=status)
    return render_template('admin/usuarios.html', usuarios=query.order_by(User.created_at.desc()).paginate(page=page, per_page=25), q=q, status=status)

@admin_bp.route('/usuarios/<int:uid>')
@login_required
def usuario_detalhe(uid):
    _chk()
    user = User.query.get_or_404(uid)
    logs = LoginLog.query.filter_by(user_id=uid).order_by(LoginLog.created_at.desc()).limit(20).all()
    invoices = Invoice.query.filter_by(user_id=uid).order_by(Invoice.created_at.desc()).all()
    plans = Plan.query.filter_by(ativo=True).all()
    return render_template('admin/usuario_detalhe.html', user=user, logs=logs, invoices=invoices, plans=plans)

@admin_bp.route('/usuarios/<int:uid>/acao', methods=['POST'])
@login_required
def usuario_acao(uid):
    _chk()
    user = User.query.get_or_404(uid); acao = request.form.get('acao')
    if acao == 'ativar': user.is_active=True; flash(f'{user.email} ativado.','success'); _log('usuario_ativar', user.email)
    elif acao == 'bloquear': user.is_active=False; flash(f'{user.email} bloqueado.','warning'); _log('usuario_bloquear', user.email)
    elif acao == 'estender_trial':
        horas = int(request.form.get('horas',24))
        user.trial_end = datetime.utcnow()+timedelta(hours=horas); user.subscription_status='trial'
        flash(f'Trial estendido +{horas}h.','success'); _log('estender_trial',f'{user.email} +{horas}h')
    elif acao == 'dar_plano':
        plan = Plan.query.get(request.form.get('plan_id')); dias=int(request.form.get('dias',30))
        if plan:
            user.plan_id=plan.id; user.plan_start=datetime.utcnow()
            user.plan_end=datetime.utcnow()+timedelta(days=dias); user.subscription_status='active'
            flash(f'Plano {plan.nome} atribuído.','success'); _log('dar_plano',f'{user.email} {plan.nome} {dias}d')
    elif acao == 'resetar_senha':
        nova = request.form.get('nova_senha','')
        if len(nova)>=8: user.set_password(nova); flash('Senha redefinida.','success'); _log('resetar_senha',user.email)
        else: flash('Senha deve ter pelo menos 8 caracteres.','danger')
    db.session.commit()
    return redirect(url_for('admin.usuario_detalhe', uid=uid))

@admin_bp.route('/planos', methods=['GET','POST'])
@login_required
def planos():
    _chk()
    if request.method == 'POST':
        pid = request.form.get('id')
        plan = Plan.query.get(pid) if pid else Plan()
        plan.nome=request.form.get('nome',''); plan.slug=request.form.get('slug','')
        plan.descricao=request.form.get('descricao','')
        plan.preco_mensal=float(request.form.get('preco_mensal',0))
        plan.preco_anual=float(request.form.get('preco_anual',0) or 0)
        plan.max_editais=int(request.form.get('max_editais',10))
        plan.max_produtos=int(request.form.get('max_produtos',100))
        plan.max_docs_mb=int(request.form.get('max_docs_mb',500))
        plan.tem_ia=bool(request.form.get('tem_ia'))
        plan.tem_zip=bool(request.form.get('tem_zip'))
        plan.destaque=bool(request.form.get('destaque'))
        plan.ativo=bool(request.form.get('ativo',True))
        plan.stripe_price_mensal=request.form.get('stripe_price_mensal','')
        plan.stripe_price_anual=request.form.get('stripe_price_anual','')
        plan.set_recursos([r.strip() for r in request.form.get('recursos','').split('\n') if r.strip()])
        if not pid: db.session.add(plan)
        db.session.commit(); _log('salvar_plano', plan.nome)
        flash('Plano salvo!','success')
        return redirect(url_for('admin.planos'))
    return render_template('admin/planos.html', planos=Plan.query.order_by(Plan.ordem).all())

@admin_bp.route('/configuracoes', methods=['GET','POST'])
@login_required
def configuracoes():
    _chk()
    if request.method == 'POST':
        for k,v,t in [('site_nome',request.form.get('site_nome','PropostaLic'),'string'),
                      ('site_slogan',request.form.get('site_slogan',''),'string'),
                      ('trial_duration',request.form.get('trial_duration','3600'),'int'),
                      ('manutencao','true' if request.form.get('manutencao') else 'false','bool'),
                      ('cadastro_aberto','true' if request.form.get('cadastro_aberto') else 'false','bool')]:
            SiteConfig.set(k, v, t)
        _log('salvar_config'); flash('Configurações salvas!','success')
        return redirect(url_for('admin.configuracoes'))
    cfgs = {c.chave: c.valor for c in SiteConfig.query.all()}
    return render_template('admin/configuracoes.html', cfgs=cfgs)

@admin_bp.route('/financeiro')
@login_required
def financeiro():
    _chk()
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(100).all()
    receita_total = db.session.query(func.sum(Invoice.valor)).filter_by(status='paid').scalar() or 0
    receita_mes   = db.session.query(func.sum(Invoice.valor)).filter(
        Invoice.status=='paid', Invoice.created_at>=datetime.utcnow().replace(day=1)).scalar() or 0
    return render_template('admin/financeiro.html', invoices=invoices, receita_total=receita_total, receita_mes=receita_mes)

@admin_bp.route('/logs')
@login_required
def logs():
    _chk()
    page = request.args.get('page',1,type=int); tipo = request.args.get('tipo','login')
    if tipo == 'login':
        logs = LoginLog.query.order_by(LoginLog.created_at.desc()).paginate(page=page, per_page=50)
    else:
        logs = AdminLog.query.order_by(AdminLog.created_at.desc()).paginate(page=page, per_page=50)
    return render_template('admin/logs.html', logs=logs, tipo=tipo)

@admin_bp.route('/assistente')
@login_required
def assistente():
    _chk()
    arquivos = []
    for root, dirs, files in os.walk(APP_DIR):
        dirs[:] = [d for d in dirs if d not in ('__pycache__','.git','venv','env','node_modules','migrations','.backups')]
        for file in files:
            if file.endswith(('.py','.html','.css','.js','.json','.txt','.md','.sh')):
                arquivos.append(os.path.relpath(os.path.join(root,file), APP_DIR))
    return render_template('admin/assistente.html', arquivos=sorted(arquivos))

@admin_bp.route('/assistente/ler', methods=['POST'])
@login_required
def assistente_ler():
    _chk()
    arq = request.json.get('arquivo','')
    if not arq or '..' in arq: return jsonify({'erro':'Inválido'}), 400
    caminho = os.path.join(APP_DIR, arq)
    if not os.path.isfile(caminho): return jsonify({'erro':'Não encontrado'}), 404
    try:
        with open(caminho,'r',encoding='utf-8',errors='replace') as f: return jsonify({'conteudo':f.read(),'arquivo':arq})
    except Exception as e: return jsonify({'erro':str(e)}), 500

@admin_bp.route('/assistente/salvar', methods=['POST'])
@login_required
def assistente_salvar():
    _chk()
    arq = request.json.get('arquivo',''); conteudo = request.json.get('conteudo','')
    if not arq or '..' in arq: return jsonify({'erro':'Inválido'}), 400
    caminho = os.path.join(APP_DIR, arq)
    try:
        bk_dir = os.path.join(APP_DIR, '.backups'); os.makedirs(bk_dir, exist_ok=True)
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        with open(caminho,'r',encoding='utf-8',errors='replace') as f: orig = f.read()
        with open(os.path.join(bk_dir, f"{arq.replace('/','_')}_{ts}.bak"),'w',encoding='utf-8') as f: f.write(orig)
    except Exception: pass
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho,'w',encoding='utf-8') as f: f.write(conteudo)
        _log('editar_arquivo', arq)
        return jsonify({'ok':True,'msg':f'Arquivo {arq} salvo!'})
    except Exception as e: return jsonify({'erro':str(e)}), 500

@admin_bp.route('/assistente/chat', methods=['POST'])
@login_required
def assistente_chat():
    _chk()
    mensagem = request.json.get('mensagem','').strip()
    arq_ctx  = request.json.get('arquivo','')
    historico= request.json.get('historico',[])
    apikey   = os.environ.get('ANTHROPIC_API_KEY','')
    if not apikey: return jsonify({'erro':'Chave ANTHROPIC_API_KEY não configurada no .env'}), 400
    sistema = ('Você é o assistente de desenvolvimento do PropostaLic (SaaS Flask/Python). '
               'Pode modificar arquivos do sistema. Quando pedir para modificar um arquivo, '
               'retorne o código COMPLETO dentro de ```codigo```. Responda em português.')
    if arq_ctx and '..' not in arq_ctx:
        caminho = os.path.join(APP_DIR, arq_ctx)
        if os.path.isfile(caminho):
            try:
                with open(caminho,'r',encoding='utf-8',errors='replace') as f: conteudo = f.read()
                sistema += f'\n\nArquivo aberto: {arq_ctx}\n```\n{conteudo[:8000]}\n```'
            except Exception: pass
    resp, err = _api({'model':'claude-sonnet-4-6','max_tokens':4000,'system':sistema,
        'messages': historico+[{'role':'user','content':mensagem}]}, apikey, timeout=120)
    if err: return jsonify({'erro':err}), 500
    texto = ''.join(c.get('text','') for c in resp.get('content',[]))
    _log('assistente_chat', mensagem[:200])
    return jsonify({'resposta':texto})

@admin_bp.route('/assistente/backups')
@login_required
def assistente_backups():
    _chk()
    bk_dir = os.path.join(APP_DIR, '.backups')
    backups = []
    if os.path.exists(bk_dir):
        for f in sorted(os.listdir(bk_dir), reverse=True)[:50]:
            caminho = os.path.join(bk_dir, f)
            backups.append({'nome':f,'tamanho':os.path.getsize(caminho),
                            'data':datetime.fromtimestamp(os.path.getmtime(caminho)).strftime('%d/%m/%Y %H:%M')})
    return jsonify({'backups':backups})

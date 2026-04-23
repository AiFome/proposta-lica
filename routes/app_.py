import json, io, base64, zipfile, os
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, send_file, current_app)
from flask_login import login_required, current_user
from models import db, UserConfig, UserDocument, UserEdital, UserProduto, Plan
import urllib.request, urllib.error

app_bp = Blueprint('app_', __name__)

def _api_call(payload, apikey, timeout=180):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=data,
        headers={'Content-Type':'application/json','x-api-key':apikey,
                 'anthropic-version':'2023-06-01','anthropic-beta':'pdfs-2024-09-25'})
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

def _get_apikey():
    # Sempre usa a chave do servidor (.env) — centralizada pelo admin
    server_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if server_key:
        return server_key
    # Fallback: chave individual do usuário (caso o admin não tenha configurado)
    cfg = current_user.config
    if not cfg or not cfg.anthropic_key_enc: return None
    try:
        from cryptography.fernet import Fernet
        key = current_app.config['SECRET_KEY'][:32].encode().ljust(32)[:32]
        fkey = base64.urlsafe_b64encode(key)
        return Fernet(fkey).decrypt(cfg.anthropic_key_enc.encode()).decode()
    except Exception:
        return cfg.anthropic_key_enc

def _encrypt_apikey(raw):
    try:
        from cryptography.fernet import Fernet
        key = current_app.config['SECRET_KEY'][:32].encode().ljust(32)[:32]
        fkey = base64.urlsafe_b64encode(key)
        return Fernet(fkey).encrypt(raw.encode()).decode()
    except Exception:
        return raw

def _requer_plano():
    from app import requer_plano
    return requer_plano

@app_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.pode_usar and not current_user.is_admin:
        return redirect(url_for('payment.planos'))
    editais = UserEdital.query.filter_by(user_id=current_user.id).order_by(UserEdital.created_at.desc()).limit(5).all()
    total_docs = UserDocument.query.filter_by(user_id=current_user.id).count()
    total_produtos = UserProduto.query.filter_by(user_id=current_user.id).count()
    return render_template('app/dashboard.html', cfg=current_user.config,
                           editais=editais, total_docs=total_docs, total_produtos=total_produtos)

@app_bp.route('/proposta')
@login_required
def proposta():
    if not current_user.pode_usar and not current_user.is_admin:
        return redirect(url_for('payment.planos'))
    produtos = UserProduto.query.filter_by(user_id=current_user.id).order_by(UserProduto.nome).all()
    editais  = UserEdital.query.filter_by(user_id=current_user.id).order_by(UserEdital.created_at.desc()).all()
    return render_template('app/proposta.html', cfg=current_user.config,
                           produtos=[p.to_dict() for p in produtos], editais=editais)

@app_bp.route('/produtos')
@login_required
def produtos():
    if not current_user.pode_usar and not current_user.is_admin:
        return redirect(url_for('payment.planos'))
    q = request.args.get('q','')
    query = UserProduto.query.filter_by(user_id=current_user.id)
    if q:
        query = query.filter((UserProduto.nome.ilike(f'%{q}%'))|(UserProduto.fabricante.ilike(f'%{q}%')))
    return render_template('app/produtos.html', produtos=query.order_by(UserProduto.nome).all(), q=q)

@app_bp.route('/produtos/salvar', methods=['POST'])
@login_required
def produto_salvar():
    try:
        if not current_user.pode_usar: return jsonify({'erro':'Acesso bloqueado.'}), 403
        data = request.json
        if not data: return jsonify({'erro':'Dados inválidos'}), 400
        pid  = data.get('id')
        if pid:
            prod = UserProduto.query.filter_by(id=int(pid), user_id=current_user.id).first()
            if not prod: return jsonify({'erro':'Produto não encontrado'}), 404
        else:
            plan = current_user.plan
            if plan:
                total = UserProduto.query.filter_by(user_id=current_user.id).count()
                if total >= plan.max_produtos:
                    return jsonify({'erro': f'Limite de {plan.max_produtos} produtos atingido.'}), 403
            prod = UserProduto(user_id=current_user.id)
            db.session.add(prod)
        prod.nome = data.get('nome',''); prod.fabricante = data.get('fabricante','')
        prod.gramatura = data.get('gramatura',''); prod.categoria = data.get('categoria','')
        prod.anvisa = data.get('anvisa',''); prod.codigo = data.get('codigo','')
        prod.obs = data.get('obs','')
        db.session.commit()
        return jsonify({'ok': True, 'id': prod.id})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Erro produto_salvar: {e}')
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500

@app_bp.route('/produtos/excluir/<int:pid>', methods=['DELETE'])
@login_required
def produto_excluir(pid):
    prod = UserProduto.query.filter_by(id=pid, user_id=current_user.id).first_or_404()
    db.session.delete(prod); db.session.commit()
    return jsonify({'ok': True})

@app_bp.route('/documentacao')
@login_required
def documentacao():
    if not current_user.pode_usar and not current_user.is_admin:
        return redirect(url_for('payment.planos'))
    docs_list = UserDocument.query.filter_by(user_id=current_user.id).all()
    docs = {d.doc_key: d for d in docs_list}
    editais = UserEdital.query.filter_by(user_id=current_user.id).order_by(UserEdital.created_at.desc()).all()
    return render_template('app/documentacao.html', docs=docs, editais=editais)

@app_bp.route('/documentacao/upload', methods=['POST'])
@login_required
def doc_upload():
    if not current_user.pode_usar: return jsonify({'erro':'Acesso bloqueado.'}), 403
    doc_key  = request.form.get('doc_key','')
    label    = request.form.get('label','')
    categoria= request.form.get('categoria','outros')
    arquivo  = request.files.get('arquivo')
    if not arquivo or not doc_key: return jsonify({'erro':'Dados inválidos'}), 400
    plan = current_user.plan
    if plan:
        total = db.session.query(db.func.sum(UserDocument.tamanho)).filter_by(user_id=current_user.id).scalar() or 0
        if total + len(arquivo.read()) > plan.max_docs_mb * 1024 * 1024:
            return jsonify({'erro': f'Limite de {plan.max_docs_mb}MB atingido.'}), 403
        arquivo.seek(0)
    dados = arquivo.read()
    UserDocument.query.filter_by(user_id=current_user.id, doc_key=doc_key).delete()
    db.session.add(UserDocument(user_id=current_user.id, doc_key=doc_key, label=label or doc_key,
        filename=arquivo.filename, mimetype=arquivo.mimetype, tamanho=len(dados),
        dados=dados, categoria=categoria))
    db.session.commit()
    return jsonify({'ok': True, 'nome': arquivo.filename, 'tamanho': _fmt(len(dados))})

@app_bp.route('/documentacao/baixar/<int:did>')
@login_required
def doc_baixar(did):
    doc = UserDocument.query.filter_by(id=did, user_id=current_user.id).first_or_404()
    return send_file(io.BytesIO(doc.dados), mimetype=doc.mimetype,
                     as_attachment=True, download_name=doc.filename)

@app_bp.route('/documentacao/excluir/<int:did>', methods=['DELETE'])
@login_required
def doc_excluir(did):
    doc = UserDocument.query.filter_by(id=did, user_id=current_user.id).first_or_404()
    db.session.delete(doc); db.session.commit()
    return jsonify({'ok': True})

@app_bp.route('/edital/enviar', methods=['POST'])
@login_required
def edital_enviar():
    if not current_user.pode_usar: return jsonify({'erro':'Acesso bloqueado.'}), 403
    arquivo = request.files.get('edital')
    if not arquivo: return jsonify({'erro':'Nenhum arquivo enviado'}), 400
    plan = current_user.plan
    if plan:
        total = UserEdital.query.filter_by(user_id=current_user.id).count()
        if total >= plan.max_editais:
            return jsonify({'erro': f'Limite de {plan.max_editais} editais atingido.'}), 403
    dados_pdf = arquivo.read()
    b64 = base64.b64encode(dados_pdf).decode()
    apikey = _get_apikey()
    exigencias, pregao, prefeitura, processo, plataforma, objeto, itens_json = [], '', '', '', '', '', []
    if apikey:
        prompt = ('Analise o edital PDF. Retorne APENAS JSON: '
                  '{"pregao":"","processo":"","prefeitura":"","plataforma":"","objeto":"",'
                  '"exigencias":["certidao federal"],'
                  '"itens":[{"num":"01","desc":"DESCRITIVO COMPLETO","qtd":"10","unid":"UNID"}]}')
        resp, err = _api_call({'model':'claude-haiku-4-5-20251001','max_tokens':4000,
            'messages':[{'role':'user','content':[
                {'type':'document','source':{'type':'base64','media_type':'application/pdf','data':b64}},
                {'type':'text','text':prompt}
            ]}]}, apikey, timeout=90)
        if not err and resp:
            raw = ''.join(c.get('text','') for c in resp.get('content',[]))
            raw = raw.strip().lstrip('```json').lstrip('```').rstrip('```').strip()
            try:
                p = json.loads(raw)
                pregao=p.get('pregao',''); processo=p.get('processo','')
                prefeitura=p.get('prefeitura',''); plataforma=p.get('plataforma','')
                objeto=p.get('objeto',''); exigencias=p.get('exigencias',[])
                itens_json=p.get('itens',[])
            except Exception: pass
    ed = UserEdital(user_id=current_user.id, nome=arquivo.filename,
        pregao=pregao, processo=processo, prefeitura=prefeitura,
        plataforma=plataforma, objeto=objeto,
        exigencias=json.dumps(exigencias), itens=json.dumps(itens_json),
        dados_pdf=dados_pdf, tamanho=len(dados_pdf))
    db.session.add(ed); db.session.commit()
    return jsonify({'ok':True,'id':ed.id,'pregao':pregao,'prefeitura':prefeitura,
                    'exigencias':exigencias,'itens':itens_json})

@app_bp.route('/edital/<int:eid>/baixar')
@login_required
def edital_baixar(eid):
    ed = UserEdital.query.filter_by(id=eid, user_id=current_user.id).first_or_404()
    return send_file(io.BytesIO(ed.dados_pdf), mimetype='application/pdf',
                     as_attachment=True, download_name=ed.nome)

@app_bp.route('/edital/<int:eid>/excluir', methods=['DELETE'])
@login_required
def edital_excluir(eid):
    ed = UserEdital.query.filter_by(id=eid, user_id=current_user.id).first_or_404()
    db.session.delete(ed); db.session.commit()
    return jsonify({'ok': True})

@app_bp.route('/gerar-zip', methods=['POST'])
@login_required
def gerar_zip():
    if not current_user.pode_usar: return jsonify({'erro':'Acesso bloqueado.'}), 403
    eid = request.json.get('edital_id')
    ed  = UserEdital.query.filter_by(id=eid, user_id=current_user.id).first_or_404()
    docs = UserDocument.query.filter_by(user_id=current_user.id).all()
    buf = io.BytesIO()
    readme = (f'PACOTE DE HABILITACAO\n{"="*40}\nEdital: {ed.nome}\nPregao: {ed.pregao}\n'
              f'Prefeitura: {ed.prefeitura}\nGerado em: {datetime.utcnow().strftime("%d/%m/%Y %H:%M")}\n{"="*40}\n\n')
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for i, doc in enumerate(docs, 1):
            ext = doc.filename.rsplit('.',1)[-1] if '.' in doc.filename else 'bin'
            nome = f'{i:02d}_{_san(doc.label or doc.doc_key)}.{ext}'
            zf.writestr(nome, doc.dados)
            readme += f'{i}. {doc.label or doc.filename}\n'
        zf.writestr('00_LEIA-ME.txt', readme.encode('utf-8'))
    buf.seek(0)
    nome_zip = f'Habilitacao_PE{(ed.pregao or "pacote").replace("/","-")}.zip'
    return send_file(buf, mimetype='application/zip', as_attachment=True, download_name=nome_zip)

@app_bp.route('/analisar-edital', methods=['POST'])
@login_required
def analisar_edital():
    if not current_user.pode_usar: return jsonify({'erro':'Acesso bloqueado.'}), 403
    apikey = _get_apikey()
    if not apikey: return jsonify({'erro':'Configure sua chave de API Anthropic nas configurações.'}), 400
    b64 = request.json.get('pdf')
    if not b64: return jsonify({'erro':'PDF não enviado'}), 400
    prompt = ('Extraia do edital PDF: numero do pregao, processo, prefeitura, plataforma e TODOS os itens do Termo de Referencia. '
              'Retorne APENAS JSON sem texto adicional: '
              '{"pregao":"005/2026","processo":"022/2026","prefeitura":"Nome Municipio","plataforma":"Nome plataforma","objeto":"Objeto resumido",'
              '"itens":[{"num":"01","desc":"DESCRICAO COMPLETA DO ITEM EM MAIUSCULAS","qtd":"10","unid":"UNID"}]} '
              'REGRAS: desc em MAIUSCULAS, inclua TODOS os itens, retorne APENAS o JSON.')
    resp, err = _api_call({'model':'claude-haiku-4-5-20251001','max_tokens':8000,
        'messages':[{'role':'user','content':[
            {'type':'document','source':{'type':'base64','media_type':'application/pdf','data':b64}},
            {'type':'text','text':prompt}
        ]}]}, apikey, timeout=180)
    if err: return jsonify({'erro': err}), 500
    raw = ''.join(c.get('text','') for c in resp.get('content',[])).strip().lstrip('```json').lstrip('```').rstrip('```').strip()
    try: return jsonify(json.loads(raw))
    except Exception as e: return jsonify({'erro': str(e)}), 500

@app_bp.route('/gerar-proposta', methods=['POST'])
@login_required
def gerar_proposta():
    if not current_user.pode_usar: return jsonify({'erro':'Acesso bloqueado.'}), 403
    from utils.docx_gen import gerar_docx
    data = request.json
    if not data: return jsonify({'erro':'Dados não recebidos.'}), 400
    empresa = data.get('empresa') or {}
    edital  = data.get('edital')  or {}
    itens   = data.get('itens')   or []
    modelo  = data.get('modelo')  or {}
    estilo  = data.get('estilo')  or 'padrao'

    # Se empresa vier vazia, buscar do perfil do usuário
    if not empresa.get('razao_social') and not empresa.get('razao'):
        cfg = current_user.config
        if cfg:
            empresa = cfg.to_dict()

    # Se modelo vier vazio, buscar do perfil do usuário
    if not modelo.get('validade'):
        cfg = current_user.config
        if cfg:
            modelo = {
                'validade': cfg.modelo_validade or '60 (SESSENTA) DIAS, A CONTAR DA DATA DA APRESENTACAO.',
                'prazo':    cfg.modelo_prazo    or 'CONFORME EDITAL.',
                'local':    cfg.modelo_local    or 'CONFORME EDITAL.',
                'decl':     cfg.modelo_decl     or '',
                'obs':      cfg.modelo_obs      or '',
            }

    try:
        docx = gerar_docx(empresa, edital, itens, modelo, estilo=estilo)
        pregao = (edital.get('pregao','') or '').replace('/','- ')
        nome_arquivo = f'Proposta_PE{pregao}.docx' if pregao else 'Proposta.docx'
        return send_file(
            io.BytesIO(docx),
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=nome_arquivo
        )
    except Exception as e:
        import traceback
        current_app.logger.error(f'Erro gerar_proposta: {traceback.format_exc()}')
        return jsonify({'erro': f'Erro ao gerar DOCX: {str(e)}'}), 500

@app_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    if not current_user.pode_usar: return jsonify({'erro':'Acesso bloqueado.'}), 403
    apikey = _get_apikey()
    if not apikey: return jsonify({'erro':'Configure sua chave de API Anthropic.'}), 400
    resp, err = _api_call({'model':'claude-haiku-4-5-20251001','max_tokens':1000,
        'system': request.json.get('system','Você é um assistente de licitações. Responda em português.'),
        'messages': request.json.get('messages',[])}, apikey, timeout=60)
    if err: return jsonify({'erro': err}), 500
    return jsonify({'resposta': ''.join(c.get('text','') for c in resp.get('content',[]))})

@app_bp.route('/perfil', methods=['GET','POST'])
@login_required
def perfil():
    if request.method == 'POST':
        acao = request.form.get('acao')
        if acao == 'dados':
            current_user.nome     = request.form.get('nome','').strip()
            current_user.telefone = request.form.get('telefone','').strip()
            current_user.empresa  = request.form.get('empresa','').strip()
            current_user.cnpj     = request.form.get('cnpj','').strip()
            db.session.commit(); flash('Dados atualizados!', 'success')
        elif acao == 'senha':
            atual = request.form.get('senha_atual','')
            nova  = request.form.get('nova_senha','')
            conf  = request.form.get('confirmar_senha','')
            if not current_user.check_password(atual): flash('Senha atual incorreta.', 'danger')
            elif len(nova) < 8: flash('Nova senha deve ter pelo menos 8 caracteres.', 'danger')
            elif nova != conf: flash('Senhas não coincidem.', 'danger')
            else:
                current_user.set_password(nova); db.session.commit()
                flash('Senha alterada com sucesso!', 'success')
        elif acao == 'empresa_config':
            cfg = current_user.config or UserConfig(user_id=current_user.id)
            cfg.razao_social=request.form.get('razao_social',''); cfg.cnpj=request.form.get('cnpj_empresa','')
            cfg.ie=request.form.get('ie',''); cfg.telefone=request.form.get('tel','')
            cfg.email_comercial=request.form.get('email_comercial',''); cfg.endereco=request.form.get('endereco','')
            cfg.banco=request.form.get('banco',''); cfg.representante=request.form.get('representante','')
            cfg.cpfrg=request.form.get('cpfrg','')
            raw = request.form.get('anthropic_key','').strip()
            if raw and not raw.startswith('•'): cfg.anthropic_key_enc = _encrypt_apikey(raw)
            if not cfg.id: db.session.add(cfg)
            db.session.commit(); flash('Configurações salvas!', 'success')
        elif acao == 'modelo':
            cfg = current_user.config or UserConfig(user_id=current_user.id)
            cfg.modelo_validade=request.form.get('modelo_validade','')
            cfg.modelo_prazo=request.form.get('modelo_prazo','')
            cfg.modelo_local=request.form.get('modelo_local','')
            cfg.modelo_decl=request.form.get('modelo_decl','')
            cfg.modelo_obs=request.form.get('modelo_obs','')
            cfg.ordem_produto=request.form.get('ordem_produto','nome,fabricante,gramatura')
            cfg.separador_produto=request.form.get('separador_produto',' / ')
            if not cfg.id: db.session.add(cfg)
            db.session.commit(); flash('Modelo salvo!', 'success')
        return redirect(url_for('app_.perfil'))
    return render_template('app/perfil.html')

@app_bp.route('/api/status')
@login_required
def api_status():
    return jsonify({'pode_usar': current_user.pode_usar,
                    'status': current_user.subscription_status,
                    'trial_restante': current_user.trial_restante_segundos,
                    'trial_expirado': current_user.trial_expirado,
                    'plan': current_user.plan.nome if current_user.plan else None,
                    'plan_end': current_user.plan_end.isoformat() if current_user.plan_end else None})

def _fmt(b):
    if b<1024: return f'{b} B'
    if b<1048576: return f'{b/1024:.1f} KB'
    return f'{b/1048576:.1f} MB'

def _san(s):
    import re
    return re.sub(r'[^a-zA-Z0-9\-_\u00C0-\u024F]','_', str(s or ''))[:60]

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import UserProduto, UserEdital, UserDocument

api_bp = Blueprint('api', __name__)

@api_bp.route('/produtos')
@login_required
def produtos():
    q = request.args.get('q','')
    query = UserProduto.query.filter_by(user_id=current_user.id)
    if q: query = query.filter(UserProduto.nome.ilike(f'%{q}%'))
    return jsonify([p.to_dict() for p in query.order_by(UserProduto.nome).all()])

@api_bp.route('/editais')
@login_required
def editais():
    eds = UserEdital.query.filter_by(user_id=current_user.id).order_by(UserEdital.created_at.desc()).all()
    return jsonify([{'id':e.id,'nome':e.nome,'pregao':e.pregao,'processo':e.processo,
                     'prefeitura':e.prefeitura,'plataforma':e.plataforma,'objeto':e.objeto,
                     'exigencias':e.get_exigencias(),'itens':e.get_itens()} for e in eds])

@api_bp.route('/docs')
@login_required
def docs():
    docs = UserDocument.query.filter_by(user_id=current_user.id).all()
    return jsonify([{'id':d.id,'doc_key':d.doc_key,'label':d.label,'filename':d.filename,
                     'tamanho':d.tamanho,'categoria':d.categoria,
                     'data':d.updated_at.strftime('%d/%m/%Y') if d.updated_at else ''} for d in docs])

@api_bp.route('/config')
@login_required
def config():
    cfg = current_user.config
    if not cfg: return jsonify({})
    return jsonify(cfg.to_dict())

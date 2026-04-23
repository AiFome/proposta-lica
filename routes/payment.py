import os, json, stripe
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from models import db, User, Plan, Invoice

payment_bp = Blueprint('payment', __name__)
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY','')

@payment_bp.route('/planos')
@login_required
def planos():
    return render_template('payment/planos.html', planos=Plan.query.filter_by(ativo=True).order_by(Plan.ordem).all())

@payment_bp.route('/checkout/<slug>/<periodo>')
@login_required
def checkout(slug, periodo):
    if periodo not in ('mensal','anual'): abort(400)
    plan = Plan.query.filter_by(slug=slug, ativo=True).first_or_404()
    price_id = plan.stripe_price_mensal if periodo=='mensal' else plan.stripe_price_anual
    if not price_id:
        flash('Plano não disponível para pagamento online. Entre em contato.','warning')
        return redirect(url_for('payment.planos'))
    try:
        if not current_user.stripe_customer_id:
            c = stripe.Customer.create(email=current_user.email, name=current_user.nome,
                                       metadata={'user_id':str(current_user.id)})
            current_user.stripe_customer_id = c.id; db.session.commit()
        session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{'price':price_id,'quantity':1}],
            mode='subscription',
            success_url=url_for('payment.sucesso',_external=True)+'?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment.planos',_external=True),
            metadata={'user_id':str(current_user.id),'plan_id':str(plan.id),'periodo':periodo},
            locale='pt-BR')
        return redirect(session.url, code=303)
    except stripe.error.StripeError as e:
        flash(f'Erro ao processar: {e.user_message}','danger')
        return redirect(url_for('payment.planos'))

@payment_bp.route('/sucesso')
@login_required
def sucesso():
    sid = request.args.get('session_id')
    if sid:
        try:
            s = stripe.checkout.Session.retrieve(sid)
            if s.payment_status == 'paid': flash('Pagamento confirmado! Plano ativado.','success')
        except Exception: pass
    return render_template('payment/sucesso.html')

@payment_bp.route('/meu-plano')
@login_required
def meu_plano():
    invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.created_at.desc()).limit(12).all()
    planos = Plan.query.filter_by(ativo=True).order_by(Plan.ordem).all()
    return render_template('payment/meu_plano.html', invoices=invoices, planos=planos)

@payment_bp.route('/cancelar', methods=['POST'])
@login_required
def cancelar():
    if not current_user.stripe_subscription_id:
        flash('Nenhuma assinatura ativa.','warning')
        return redirect(url_for('payment.meu_plano'))
    try:
        stripe.Subscription.cancel(current_user.stripe_subscription_id)
        current_user.subscription_status = 'canceled'; db.session.commit()
        flash('Assinatura cancelada.','info')
    except stripe.error.StripeError as e:
        flash(f'Erro: {e.user_message}','danger')
    return redirect(url_for('payment.meu_plano'))

@payment_bp.route('/portal')
@login_required
def portal_cliente():
    if not current_user.stripe_customer_id:
        flash('Nenhuma assinatura encontrada.','warning')
        return redirect(url_for('payment.meu_plano'))
    try:
        p = stripe.billing_portal.Session.create(customer=current_user.stripe_customer_id,
            return_url=url_for('payment.meu_plano',_external=True))
        return redirect(p.url)
    except stripe.error.StripeError as e:
        flash(f'Erro: {e.user_message}','danger')
        return redirect(url_for('payment.meu_plano'))

@payment_bp.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data(); sig = request.headers.get('Stripe-Signature','')
    secret  = os.environ.get('STRIPE_WEBHOOK_SECRET','')
    try: event = stripe.Webhook.construct_event(payload, sig, secret)
    except (ValueError, stripe.error.SignatureVerificationError): abort(400)
    obj = event['data']['object']; etype = event['type']
    if etype == 'checkout.session.completed': _checkout_ok(obj)
    elif etype in ('invoice.paid','invoice.payment_succeeded'): _invoice_paid(obj)
    elif etype == 'invoice.payment_failed': _payment_failed(obj)
    elif etype in ('customer.subscription.deleted','customer.subscription.canceled'): _sub_canceled(obj)
    elif etype == 'customer.subscription.updated': _sub_updated(obj)
    return jsonify({'received':True})

def _checkout_ok(s):
    uid = s.get('metadata',{}).get('user_id'); pid = s.get('metadata',{}).get('plan_id')
    periodo = s.get('metadata',{}).get('periodo','mensal')
    if not uid or not pid: return
    user = User.query.get(int(uid)); plan = Plan.query.get(int(pid))
    if not user or not plan: return
    dias = 30 if periodo=='mensal' else 365
    user.plan_id=plan.id; user.plan_start=datetime.utcnow()
    user.plan_end=datetime.utcnow()+timedelta(days=dias)
    user.subscription_status='active'; user.stripe_subscription_id=s.get('subscription')
    db.session.commit()

def _invoice_paid(inv):
    user = User.query.filter_by(stripe_customer_id=inv.get('customer')).first()
    if not user: return
    db.session.add(Invoice(user_id=user.id, plan_id=user.plan_id,
        stripe_invoice_id=inv.get('id'), valor=(inv.get('amount_paid',0)/100),
        moeda=inv.get('currency','brl').upper(), status='paid', data_pagamento=datetime.utcnow()))
    if user.plan_end:
        user.plan_end = max(user.plan_end, datetime.utcnow()) + timedelta(days=30)
    user.subscription_status='active'; db.session.commit()

def _payment_failed(inv):
    user = User.query.filter_by(stripe_customer_id=inv.get('customer')).first()
    if user: user.subscription_status='past_due'; db.session.commit()

def _sub_canceled(sub):
    user = User.query.filter_by(stripe_customer_id=sub.get('customer')).first()
    if user: user.subscription_status='canceled'; db.session.commit()

def _sub_updated(sub):
    user = User.query.filter_by(stripe_customer_id=sub.get('customer')).first()
    if user:
        m = {'active':'active','past_due':'past_due','canceled':'canceled','unpaid':'past_due'}
        user.subscription_status = m.get(sub.get('status'),'active'); db.session.commit()

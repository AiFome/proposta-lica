#!/bin/bash
set -e
echo "════════════════════════════════════"
echo "  PropostaLic SaaS — Instalação"
echo "════════════════════════════════════"
[ "$EUID" -ne 0 ] && echo "Execute como root: sudo ./install.sh" && exit 1
APP_DIR="/opt/proposta-lic"
APP_USER="proposta"
DOMAIN="${1:-proposta-lic.com.br}"

apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx postgresql postgresql-contrib redis-server certbot python3-certbot-nginx ufw

id -u $APP_USER &>/dev/null || useradd -m -s /bin/bash $APP_USER
sudo -u postgres psql -c "CREATE USER proposta_user WITH PASSWORD 'SenhaForte2024!' CREATEDB;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE proposta_lic OWNER proposta_user;" 2>/dev/null || true

mkdir -p $APP_DIR
cp -r . $APP_DIR/
chown -R $APP_USER:$APP_USER $APP_DIR
sudo -u $APP_USER python3 -m venv $APP_DIR/venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip -q
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt -q

[ ! -f "$APP_DIR/.env" ] && cp $APP_DIR/.env.example $APP_DIR/.env && \
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(64))") && \
  sed -i "s/sua_chave_secreta_muito_longa_aqui_min64chars/$SECRET/" $APP_DIR/.env && \
  sed -i "s|postgresql://usuario:senha@localhost|postgresql://proposta_user:SenhaForte2024!@localhost|" $APP_DIR/.env

cat > /etc/systemd/system/proposta-lic.service << SVCEOF
[Unit]
Description=PropostaLic SaaS
After=network.target postgresql.service redis.service
[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 "app:create_app()"
Restart=always
[Install]
WantedBy=multi-user.target
SVCEOF

cat > /etc/nginx/sites-available/proposta-lic << NGXEOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    client_max_body_size 50M;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    location /static/ { alias $APP_DIR/static/; expires 30d; }
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
    location ~ /\. { deny all; }
    location ~ \.env$ { deny all; }
    location ~ \.db$ { deny all; }
}
NGXEOF

ln -sf /etc/nginx/sites-available/proposta-lic /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
ufw --force enable && ufw allow ssh && ufw allow 'Nginx Full' && ufw deny 5000
mkdir -p /var/log/proposta-lic && chown $APP_USER:$APP_USER /var/log/proposta-lic
sudo -u $APP_USER bash -c "cd $APP_DIR && venv/bin/python -c 'from app import create_app; create_app()'"
systemctl daemon-reload && systemctl enable proposta-lic && systemctl start proposta-lic
systemctl enable redis-server && systemctl start redis-server

echo ""
echo "════════════════════════════════════"
echo "  ✅ Instalação concluída!"
echo "  Site: http://$DOMAIN"
echo "  Configure: $APP_DIR/.env"
echo "  SSL: certbot --nginx -d $DOMAIN"
echo "  Admin: admin@proposta-lic.com.br"
echo "  Senha admin: TrocaEssaSenha@2024!"
echo "  ⚠️  TROQUE A SENHA IMEDIATAMENTE!"
echo "════════════════════════════════════"

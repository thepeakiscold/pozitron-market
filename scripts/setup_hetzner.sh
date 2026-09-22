#!/usr/bin/env bash
# ==============================================================================
# Pozitron Market - Hetzner Cloud Automated VPS Provisioning & Deployment Script
# Target OS: Ubuntu 22.04 / 24.04 LTS (x86_64 or ARM64)
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}   Pozitron Market - Hetzner Cloud Setup Script       ${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. Root check
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}[HATA] Bu betik root yetkisiyle calistirilmalidir. Lutfen 'sudo bash' ile calistirin.${NC}"
    exit 1
fi

APP_DIR="/var/www/pozitron"
ENV_DIR="/etc/pozitron"
REPO_URL="https://github.com/thepeakiscold/pozitron-market.git"

# 2. System updates & package installation
echo -e "\n${YELLOW}[1/7] Paket listesi guncelleniyor ve gereksinimler kuruluyor...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    sqlite3 \
    ffmpeg \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban

# 3. Clone or pull repo
echo -e "\n${YELLOW}[2/7] Pozitron Market kaynak kodlari hazirlaniyor...${NC}"
mkdir -p /var/www
if [ ! -d "${APP_DIR}/.git" ]; then
    echo "Depo klonlaniyor: ${REPO_URL} -> ${APP_DIR}"
    git clone "${REPO_URL}" "${APP_DIR}"
else
    echo "Mevcut depo guncelleniyor (git pull)..."
    cd "${APP_DIR}"
    git fetch origin
    git reset --hard origin/main
fi

# 4. Setup Python Virtual Environment & Dependencies
echo -e "\n${YELLOW}[3/7] Python sanal ortami olusturuluyor ve bagimliliklar yukleniyor...${NC}"
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip -q
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt" -q

# Ensure directories exist
mkdir -p "${APP_DIR}/uploads" "${APP_DIR}/data" "${APP_DIR}/products"
chown -R www-data:www-data "${APP_DIR}"
chmod -R 775 "${APP_DIR}"

# 5. Environment configuration file
echo -e "\n${YELLOW}[4/7] Guvenlik ve ortam degiskenleri hazirlaniyor...${NC}"
mkdir -p "${ENV_DIR}"
if [ ! -f "${ENV_DIR}/pozitron.env" ]; then
    cat << 'EOF' > "${ENV_DIR}/pozitron.env"
# Pozitron Market Production Environment Variables
POZITRON_ENV=production
PORT=8000
SECRET_KEY=pozitron_secret_prod_key_7792_fpv_market
ADMIN_API_KEY=pzt_adm_sec_9941a87b32c

# SMTP E-posta Ayarlari (Direct SMTP port 587 Hetzner'de tamamen aciktir)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@pozitronmarkets.com
SMTP_PASSWORD=fugtmwxhotugronp
SMTP_FROM=Pozitron Market <noreply@pozitronmarkets.com>

# Alternatif HTTP API E-posta Anahtarlari (Gerekirse)
# RESEND_API_KEY=
# BREVO_API_KEY=
# GEMINI_API_KEY=
EOF
    chmod 600 "${ENV_DIR}/pozitron.env"
    chown root:root "${ENV_DIR}/pozitron.env"
    echo "Yeni ${ENV_DIR}/pozitron.env dosyasi olusturuldu."
else
    echo "Mevcut ${ENV_DIR}/pozitron.env korundu."
fi

# 6. Setup Systemd Service
echo -e "\n${YELLOW}[5/7] Systemd servis kaydi yapiliyor (pozitron.service)...${NC}"
cat << EOF > /etc/systemd/system/pozitron.service
[Unit]
Description=Pozitron Market Backend API Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=${APP_DIR}
EnvironmentFile=-${ENV_DIR}/pozitron.env
Environment=PYTHONUNBUFFERED=1
Environment=POZITRON_ENV=production
Environment=PORT=8000
ExecStart=${APP_DIR}/venv/bin/python3 ${APP_DIR}/server.py
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pozitron
systemctl restart pozitron

# 7. Setup Nginx Reverse Proxy
echo -e "\n${YELLOW}[6/7] Nginx Reverse Proxy yapilandiriliyor...${NC}"
cat << 'EOF' > /etc/nginx/sites-available/pozitron
server {
    listen 80;
    listen [::]:80;
    server_name api.pozitronmarket.com _;

    client_max_body_size 100M;

    # Guvenlik Basliklari
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options SAMEORIGIN always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/pozitron /etc/nginx/sites-enabled/pozitron
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# 8. Firewall Configuration (UFW)
echo -e "\n${YELLOW}[7/7] Guvenlik duvari (UFW) ayarlaniyor...${NC}"
ufw allow OpenSSH > /dev/null 2>&1 || true
ufw allow 80/tcp > /dev/null 2>&1 || true
ufw allow 443/tcp > /dev/null 2>&1 || true
ufw --force enable > /dev/null 2>&1 || true

# 9. Verify API Health
echo -e "\n${YELLOW}Servis saglik kontrolu yapiliyor...${NC}"
sleep 2
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health || echo "000")

if [ "$HEALTH_STATUS" -eq 200 ]; then
    echo -e "${GREEN}[BASARILI] Pozitron API yerel olarak calisiyor (HTTP 200 OK)!${NC}"
else
    echo -e "${YELLOW}[BILGI] Servis baslatiliyor... HTTP Kodu: ${HEALTH_STATUS}${NC}"
fi

PUBLIC_IP=$(curl -s https://api.ipify.org || hostname -I | awk '{print $1}')

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}   Pozitron Market Kurulumu Tamamlandi!               ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "Sunucu Dis IP: ${BLUE}${PUBLIC_IP}${NC}"
echo -e "\n${YELLOW}SONRAKI ADIMLAR:${NC}"
echo -e "1. DNS Yonetim panelinizden (Cloudflare / Domain paneliniz):"
echo -e "   - Tip: ${GREEN}A${NC}"
echo -e "   - Ad: ${GREEN}api${NC} (veya api.pozitronmarket.com)"
echo -e "   - Deger: ${GREEN}${PUBLIC_IP}${NC}"
echo -e ""
echo -e "2. DNS yayildiktan sonra ucretsiz Let's Encrypt SSL sertifikasi kurmak icin:"
echo -e "   ${BLUE}certbot --nginx -d api.pozitronmarket.com${NC}"
echo -e ""
echo -e "3. Servis durumunu kontrol etmek icin:"
echo -e "   ${BLUE}systemctl status pozitron${NC}"
echo -e "   ${BLUE}journalctl -u pozitron -f${NC}"
echo -e "======================================================\n"

#!/bin/sh
# Endurece un droplet Ubuntu recién creado (correr UNA vez, como root, ANTES del primer deploy).
# Requisito: ya entrás por SSH con tu clave (el script desactiva el ingreso con contraseña).
#   sh harden.sh
set -eu

[ "$(id -u)" -eq 0 ] || { echo "Correr como root."; exit 1; }
if [ ! -s /root/.ssh/authorized_keys ]; then
	echo "No hay ninguna clave SSH en /root/.ssh/authorized_keys: te quedarías afuera. Cancelado."
	exit 1
fi

echo "→ Actualizando el sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get upgrade -yq

echo "→ Actualizaciones de seguridad automáticas"
apt-get install -yq unattended-upgrades
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

echo "→ SSH solo con clave (sin contraseñas)"
cat > /etc/ssh/sshd_config.d/10-sgi-hardening.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
MaxAuthTries 3
LoginGraceTime 30
X11Forwarding no
EOF
sshd -t && systemctl reload ssh

echo "→ fail2ban: bloquea IPs que insisten con SSH"
apt-get install -yq fail2ban
cat > /etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
maxretry = 5
findtime = 10m
bantime = 1h
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban

echo "→ Firewall del sistema: solo SSH, HTTP y HTTPS"
apt-get install -yq ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "→ Permisos del .env (solo root lo lee)"
[ -f /opt/sgi-agro/deploy/.env ] && chmod 600 /opt/sgi-agro/deploy/.env || true

echo
echo "Listo. Además, en el panel de DigitalOcean: Firewall de red con solo 22, 80 y 443"
echo "(Docker publica puertos por fuera de ufw; el firewall de DigitalOcean es el que manda)."

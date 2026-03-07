#!/bin/bash
# install.sh - Complete installer for Bot Tunneling

echo "===================================="
echo "🚀 INSTALASI BOT TUNNELING"
echo "===================================="
echo "Progress...... Installing.."
mkdir -p /etc/conf/
cd /etc/conf/
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/file/api-vm.sh &>/dev/null
sleep 0.5
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/file/api-vl.sh &>/dev/null
sleep 0.5
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/file/api-trj.sh &>/dev/null
sleep 0.5
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/file/api-ssh.sh &>/dev/null
chmod +x *.sh
sleep 1
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/botvpn.py &>/dev/null
clear
echo "DONE INSTALING....."
cd
sleep 2
clear
cd /etc/systemd/system/
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/mini-botvpn.service &>/dev/null
cd

apt install python3
apt install python3-pip

# Install dependencies
echo "📦 Menginstall dependencies..."
pip install python-telegram-bot==20.7 --break-system-packages

# Input token
clear
echo ""
read -p "🤖 Masukkan BOT Token : " BOT_TOKEN

# Input admin ID
read -p "👤 Masukkan ID Admin : " ADMIN_ID

# Buat config.json
cat > /etc/conf/config.json <<EOF
{
    "token": "$BOT_TOKEN",
    "admin_ids": [$ADMIN_ID],
    "scripts": {
        "ssh": "/etc/conf/api-ssh.sh",
        "vmess": "/etc/conf/api-vm.sh",
        "vless": "/etc/conf/api-vl.sh",
        "trojan": "/etc/conf/api-trj.sh"
    }
}
EOF

# Cek script bash
echo ""
echo "🔍 Memeriksa script bash..."
MISSING=0
for script in "/etc/conf/api-ssh.sh" "/etc/conf/api-vm.sh" "/etc/conf/api-vl.sh" "/etc/conf/api-trj.sh"; do
    if [ -f "$script" ]; then
        echo "✅ $script ditemukan"
    else
        echo "❌ $script TIDAK ditemukan"
        MISSING=1
    fi
done

echo ""
if [ $MISSING -eq 1 ]; then
    echo "⚠️  Beberapa script bash tidak ditemukan!"
    echo "   Pastikan script sudah ada di /etc/conf/ sebelum menjalankan bot."
else
    echo "✅ Semua script bash tersedia!"
fi

systemctl enable mini-botvpn
sleep 0.2
systemctl start mini-botvpn
systemctl restart mini-botvpn
sleep 0.1

clear
status_bot=$(systemctl is-active mini-botvpn)
if [ "$status_bot" = "active" ]; then
    echo "✅ Bot sedang berjalan"
    # Lakukan sesuatu kalau running
elif [ "$status_bot" = "inactive" ]; then
    echo "⏸️ Bot sedang mati"
    # Lakukan sesuatu kalau mati
else
    echo "❌ Bot error atau tidak terinstall"
fi

echo ""
echo "===================================="
echo "✅ INSTALASI SELESAI!"
echo "===================================="
echo "📁 Config: /etc/conf/config.json"
echo "🤖 Token: $BOT_TOKEN"
echo "👤 Admin: $ADMIN_ID"
echo "===================================="
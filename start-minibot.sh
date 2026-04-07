#!/bin/bash
# install.sh - Complete installer for Bot Tunneling
clear
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
sleep 0.5
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/file/server.sh &>/dev/null

# // script tahap 2

sleep 0.5
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/file/api-renewvm.sh &>/dev/null
sleep 0.5
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/file/api-renewssh.sh &>/dev/null
sleep 0.5
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/file/api-renewvl.sh &>/dev/null
sleep 0.5
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/file/api-renewtrj.sh &>/dev/null
chmod +x *.sh
sleep 1
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/main.py &>/dev/null
clear
echo "DONE INSTALING....."
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/file/qris.jpg &>/dev/null
cd
sleep 2
clear
cd /etc/systemd/system/
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/mini-botvpn.service &>/dev/null
cd

# // package 
sleep 0.1
cd /usr/local/sbin/
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/file/bot-expuser &>/dev/null
sleep 0.2
wget https://raw.githubusercontent.com/xawn22/mini-botvpn/main/file/bot-renew &>/dev/null
sleep 1
chmod +x bot-expuser
chmod +x bot-renew

apt install python3
apt install python3-pip

# Install dependencies
echo "📦 Menginstall dependencies..."
apt install -y jq
apt install python3-pip -y
pip3 install python-telegram-bot==20.7
pip3 install asyncio

# Cek script bash
echo ""
echo "🔍 Memeriksa script bash..."
MISSING=0
for script in "/etc/conf/api-ssh.sh" "/etc/conf/api-vm.sh" "/etc/conf/api-vl.sh" "/etc/conf/api-trj.sh" "/etc/conf/server.sh"; do
    if [ -f "$script" ]; then
        echo "✅ $script ditemukan"
		sleep 2
    else
        echo "❌ $script TIDAK ditemukan"
		sleep 2
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
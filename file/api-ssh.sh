#!/bin/bash
# ==========================================
# Script Create SSH untuk Bot Telegram
# Penerima parameter: username password quota iplimit days
# ==========================================

# Konfigurasi
DOMAIN=$(cat /etc/xray/domain 2>/dev/null)
IP=$(curl -sS icanhazip.com)
NS=$(cat /etc/xray/dns 2>/dev/null)
PUB=$(cat /etc/slowdns/server.pub 2>/dev/null)
LIMIT_IP_DIR="/etc/limit/ssh/ip"
QUOTA_DIR="/etc/ssh"
SSH_DB="/etc/ssh/.ssh.db"

# Fungsi utama create ssh
create_ssh() {
    local user="$1"
    local pass="$2"
    local quota="$3"
    local iplimit="$4"
    local masaaktif="$5"
    
    # Validasi parameter
    if [[ -z "$user" || -z "$pass" || -z "$quota" || -z "$iplimit" || -z "$masaaktif" ]]; then
        echo '{"status":"error","message":"Parameter tidak lengkap"}'
        return 1
    fi
    
    # Validasi angka
    if ! [[ "$quota" =~ ^[0-9]+$ && "$iplimit" =~ ^[0-9]+$ && "$masaaktif" =~ ^[0-9]+$ ]]; then
        echo '{"status":"error","message":"Quota, iplimit, dan masaaktif harus angka"}'
        return 1
    fi
    
    # Validasi username
    if ! [[ "$user" =~ ^[a-zA-Z0-9_]+$ ]]; then
        echo '{"status":"error","message":"Username hanya boleh huruf, angka, dan underscore"}'
        return 1
    fi
    
    # Cek apakah user sudah ada
    if getent passwd "$user" >/dev/null 2>&1; then
        echo "{\"status\":\"error\",\"message\":\"User '$user' sudah ada\"}"
        return 1
    fi
    
    # Hitung tanggal expired
    local exp_date=$(date -d "$masaaktif days" +"%Y-%m-%d")
    local exp_readable=$(date -d "$masaaktif days" +"%d %b %Y")
    local created_date=$(date +"%d %b %Y")
    
    # Setup limit IP jika diperlukan
    if [[ $iplimit -gt 0 ]]; then
        mkdir -p "$LIMIT_IP_DIR"
        echo "$iplimit" > "$LIMIT_IP_DIR/$user"
    fi
    
    # Setup quota jika diperlukan
    if [[ $quota -gt 0 ]]; then
        mkdir -p "$QUOTA_DIR"
        local quota_bytes=$((quota * 1024 * 1024 * 1024))
        echo "$quota_bytes" > "$QUOTA_DIR/$user"
    fi
    
    # Buat user
    useradd -e "$exp_date" -s /bin/false -M "$user" &>/dev/null
    echo -e "$pass\n$pass\n" | passwd "$user" &>/dev/null
    
    # Simpan ke database SSH
    mkdir -p "$(dirname "$SSH_DB")"
    sed -i "/\b${user}\b/d" "$SSH_DB" 2>/dev/null
    echo "#ssh# $user $pass $quota $iplimit $exp_readable" >> "$SSH_DB"
    
    # Simpan detail ke file
    mkdir -p /detail/ssh/
    cat > "/detail/ssh/$user.txt" <<-END
====================================
      🔰 SSH ACCOUNT INFO
====================================

---------- 📋 ACCOUNT DETAILS ----------
Host      : $DOMAIN
IP        : $IP
Username  : $user
Password  : $pass
Quota     : $quota GB
IP Limit  : $iplimit IP
SlowDNS   : ${NS}
PubKey    : ${PUB}

---------- 🌐 PORT INFO ----------
OpenSSH   : 22
DNS       : 53, 2222
SSH UDP   : 1-65535
Dropbear  : 22, 109
SSH WS    : 80, 8080, 2086, 8880
SSL WS    : 443, 8443
SSL/TLS   : 443
BadVPN    : 7100, 7300

---------- ⏱️  TIME INFO ----------
Active    : $masaaktif Days
Created   : $created_date
Expires   : $exp_readable

====================================
END
    
    # Di bagian akhir script, ganti printf dengan ini:

# Di bagian akhir script, ganti printf dengan ini:

# Info port SSH
local ssh_ports="22"
local dropbear_ports="109, 143"
local ws_ports="80, 8080, 2086, 8880"
local ssl_ports="443, 8443"
local udp_ports="1-65535"
local dns_ports="53, 2222"
local badvpn_ports="7100, 7300"

# Payload untuk SSH
local payload="GET / HTTP/1.1[crlf]Host: ${DOMAIN}[crlf]Upgrade: websocket[crlf][crlf]"

printf '{"status":"success","username":"%s","password":"%s","domain":"%s","ip":"%s","quota":"%s","iplimit":"%s","expired":"%s","expired_readable":"%s","created":"%s","ssh_port":"%s","dropbear_port":"%s","ws_port":"%s","ssl_port":"%s","udp_port":"%s","dns_port":"%s","badvpn_port":"%s","slowdns":"%s","pubkey":"%s","payload":"%s"}\n' \
    "$user" "$pass" "$DOMAIN" "$IP" "$quota" "$iplimit" "$exp_date" "$exp_readable" "$created_date" \
    "$ssh_ports" "$dropbear_ports" "$ws_ports" "$ssl_ports" "$udp_ports" "$dns_ports" "$badvpn_ports" "$NS" "$PUB" "$payload"
	
    return 0
}

# Eksekusi fungsi utama dengan parameter dari command line
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Parameter: username password quota iplimit days
    create_ssh "$1" "$2" "$3" "$4" "$5"
fi
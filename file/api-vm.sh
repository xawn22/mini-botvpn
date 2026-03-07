#!/bin/bash
# ==========================================
# Script Create VMess untuk Bot Telegram
# Penerima parameter: username days quota iplimit
# ==========================================

# Konfigurasi
XRAY_CONFIG="/etc/xray/config.json"
VMESS_DB="/etc/vmess/.vmess.db"
LIMIT_IP_DIR="/etc/limit/vmess/ip"
QUOTA_DIR="/etc/vmess"
DOMAIN=$(cat /etc/xray/domain 2>/dev/null)
IP=$(curl -sS icanhazip.com)

# Fungsi utama create vmess
create_vmess() {
    local user="$1"
    local masaaktif="$2"
    local quota="$3"
    local iplimit="$4"
    
    # Validasi parameter
    if [[ -z "$user" || -z "$masaaktif" || -z "$quota" || -z "$iplimit" ]]; then
        echo '{"status":"error","message":"Parameter tidak lengkap"}'
        return 1
    fi
    
    # Validasi angka
    if ! [[ "$masaaktif" =~ ^[0-9]+$ && "$quota" =~ ^[0-9]+$ && "$iplimit" =~ ^[0-9]+$ ]]; then
        echo '{"status":"error","message":"masaaktif, quota, dan iplimit harus angka"}'
        return 1
    fi
    
    # Validasi username
    if ! [[ "$user" =~ ^[a-zA-Z0-9_]+$ ]]; then
        echo '{"status":"error","message":"Username hanya boleh huruf, angka, dan underscore"}'
        return 1
    fi
    
    # Cek apakah user sudah ada
    local client_exists=$(grep -w "$user" "$XRAY_CONFIG" | wc -l)
    if [[ $client_exists -gt 0 ]]; then
        echo "{\"status\":\"error\",\"message\":\"User '$user' sudah ada\"}"
        return 1
    fi
    
    # Generate UUID
    local uuid=$(cat /proc/sys/kernel/random/uuid)
    
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
    
    # Tambahkan ke database vmess
    mkdir -p "$(dirname "$VMESS_DB")"
    sed -i "/\b${user}\b/d" "$VMESS_DB" 2>/dev/null
    echo "### $user $exp_date $uuid $quota $iplimit" >> "$VMESS_DB"
    
    # Tambahkan ke config Xray (VMESS WS)
    sed -i '/#vmess$/a\### '"$user $exp_date"'\
},{"id": "'""$uuid""'","alterId": '"0"',"email": "'""$user""'"' "$XRAY_CONFIG"
    
    # Tambahkan ke config Xray (VMESS GRPC)
    sed -i '/#vmessgrpc$/a\### '"$user $exp_date"'\
},{"id": "'""$uuid""'","alterId": '"0"',"email": "'""$user""'"' "$XRAY_CONFIG"
    
    # Restart service
    systemctl restart xray &>/dev/null
    service cron restart &>/dev/null
    
    # Generate links
    local asu=$(cat <<EOF
{
  "v": "2",
  "ps": "${user}",
  "add": "${DOMAIN}",
  "port": "443",
  "id": "${uuid}",
  "aid": "0",
  "net": "ws",
  "path": "/vmess",
  "type": "none",
  "host": "${DOMAIN}",
  "tls": "tls"
}
EOF
)
    
    local ask=$(cat <<EOF
{
  "v": "2",
  "ps": "${user}",
  "add": "${DOMAIN}",
  "port": "80",
  "id": "${uuid}",
  "aid": "0",
  "net": "ws",
  "path": "/vmess",
  "type": "none",
  "host": "${DOMAIN}",
  "tls": "none"
}
EOF
)
    
    local grpc=$(cat <<EOF
{
  "v": "2",
  "ps": "${user}",
  "add": "${DOMAIN}",
  "port": "443",
  "id": "${uuid}",
  "aid": "0",
  "net": "grpc",
  "path": "vmess-grpc",
  "type": "none",
  "host": "${DOMAIN}",
  "tls": "tls"
}
EOF
)
    
    local vmesslink1="vmess://$(echo "$asu" | base64 -w 0)"
    local vmesslink2="vmess://$(echo "$ask" | base64 -w 0)"
    local vmesslink3="vmess://$(echo "$grpc" | base64 -w 0)"
    
    # Simpan detail ke file
    mkdir -p /detail/vmess/
    cat > "/detail/vmess/$user.txt" <<-END
====================================
         📡 VMESS ACCOUNT
====================================

-------- 📋 ACCOUNT DETAILS --------
Remarks       : ${user}
Domain        : ${DOMAIN}
Quota         : ${quota} GB
IP Limit      : ${iplimit} IP

-------- 🔌 CONNECTION INFO --------
Port Non TLS  : 80, 8080, 2082, 2086, 8880
Port TLS      : 443, 8443
ID            : ${uuid}
Alter ID      : 0
Security      : auto
Network       : ws
Path          : /vmess
Service Name  : vmess-grpc

-------- 🔗 LINK & CONFIG --------
TLS Link      : ${vmesslink1}

Non TLS Link  : ${vmesslink2}

gRPC Link     : ${vmesslink3}

-------- ⏱️  TIME INFO --------
Active Period : ${masaaktif} Hari
Created On    : ${created_date}
Expires On    : ${exp_readable}

====================================
END
    
# Info port VMess
local port_tls="443, 8443"
local port_http="80, 8080, 2082, 2086, 8880"
local port_grpc="443"

printf '{"status":"success","username":"%s","uuid":"%s","domain":"%s","ip":"%s","quota":"%s","iplimit":"%s","expired":"%s","expired_readable":"%s","created":"%s","port_tls":"%s","port_http":"%s","port_grpc":"%s","path":"/vmess","service_name":"vmess-grpc","link_tls":"%s","link_http":"%s","link_grpc":"%s","detail_file":"/detail/vmess/%s.txt"}\n' \
    "$user" "$uuid" "$DOMAIN" "$IP" "$quota" "$iplimit" "$exp_date" "$exp_readable" "$created_date" \
    "$port_tls" "$port_http" "$port_grpc" "$vmesslink1" "$vmesslink2" "$vmesslink3" "$user"
	
    return 0
}

# Eksekusi fungsi utama dengan parameter dari command line
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Parameter: username days quota iplimit
    create_vmess "$1" "$2" "$3" "$4"
fi
#!/bin/bash
# ==========================================
# Script Create Trojan untuk Bot Telegram
# Penerima parameter: username days quota iplimit
# ==========================================

# Konfigurasi
XRAY_CONFIG="/etc/xray/config.json"
TROJAN_DB="/etc/trojan/.trojan.db"
LIMIT_IP_DIR="/etc/limit/trojan/ip"
QUOTA_DIR="/etc/trojan"
DOMAIN=$(cat /etc/xray/domain 2>/dev/null)
IP=$(curl -sS icanhazip.com)

# Fungsi utama create trojan
create_trojan() {
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
    
    # Generate password (UUID)
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
    
    # Tambahkan ke config Xray (Trojan WS)
    sed -i '/#trojanws$/a\#! '"$user $exp_date"'\
},{"password": "'""$uuid""'","email": "'""$user""'"' "$XRAY_CONFIG"
    
    # Tambahkan ke config Xray (Trojan GRPC)
    sed -i '/#trojangrpc$/a\#! '"$user $exp_date"'\
},{"password": "'""$uuid""'","email": "'""$user""'"' "$XRAY_CONFIG"
    
    # Generate links
    local trojanlink1="trojan://${uuid}@${DOMAIN}:443?mode=gun&security=tls&type=grpc&serviceName=trojan-grpc&sni=${DOMAIN}#${user}"
    local trojanlink2="trojan://${uuid}@${DOMAIN}:443?path=%2Ftrojan-ws&security=tls&host=${DOMAIN}&type=ws&sni=${DOMAIN}#${user}"
    
    # Restart service
    systemctl restart xray &>/dev/null
    systemctl restart nginx &>/dev/null
    service cron restart &>/dev/null
    
    # Simpan ke database trojan
    mkdir -p "$(dirname "$TROJAN_DB")"
    sed -i "/\b${user}\b/d" "$TROJAN_DB" 2>/dev/null
    echo "#! $user $exp_date $uuid $quota $iplimit" >> "$TROJAN_DB"
    
    # Simpan detail ke file
    mkdir -p /detail/trojan/
    cat > "/detail/trojan/$user.txt" <<-END
====================================
         🛡️ TROJAN ACCOUNT
====================================

-------- 📋 ACCOUNT DETAILS --------
Remarks       : ${user}
Host/IP       : ${DOMAIN}
Quota         : ${quota} GB
IP Limit      : ${iplimit} IP

-------- 🔌 CONNECTION INFO --------
Port          : 443, 8443
Key           : ${uuid}
Path          : /trojan-ws
Service Name  : trojan-grpc

-------- 🔗 LINK & CONFIG ----------
WebSocket TLS : ${trojanlink2}

gRPC Link     : ${trojanlink1}

-------- ⏱️  TIME INFO -------------
Active Period : ${masaaktif} Hari
Created On    : ${created_date}
Expires On    : ${exp_readable}

====================================
END
    
# Info port Trojan
local port_tls="443, 8443"
local port_grpc="443"

printf '{"status":"success","username":"%s","password":"%s","domain":"%s","ip":"%s","quota":"%s","iplimit":"%s","expired":"%s","expired_readable":"%s","created":"%s","port_tls":"%s","port_grpc":"%s","path":"/trojan-ws","service_name":"trojan-grpc","link_ws":"%s","link_grpc":"%s","detail_file":"/detail/trojan/%s.txt"}\n' \
    "$user" "$uuid" "$DOMAIN" "$IP" "$quota" "$iplimit" "$exp_date" "$exp_readable" "$created_date" \
    "$port_tls" "$port_grpc" "$trojanlink2" "$trojanlink1" "$user"
	
    return 0
}

# Eksekusi fungsi utama dengan parameter dari command line
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Parameter: username days quota iplimit
    create_trojan "$1" "$2" "$3" "$4"
fi
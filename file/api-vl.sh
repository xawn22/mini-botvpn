#!/bin/bash
# ==========================================
# Script Create VLess untuk Bot Telegram
# Penerima parameter: username days quota iplimit
# ==========================================

# Konfigurasi
XRAY_CONFIG="/etc/xray/config.json"
VLESS_DB="/etc/vless/.vless.db"
LIMIT_IP_DIR="/etc/limit/vless/ip"
QUOTA_DIR="/etc/vless"
DOMAIN=$(cat /etc/xray/domain 2>/dev/null)
IP=$(curl -sS icanhazip.com)

# Fungsi utama create vless
create_vless() {
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
    
    # Tambahkan ke config Xray (VLess WS)
    sed -i '/#vless$/a\#& '"$user $exp_date"'\
},{"id": "'""$uuid""'","email": "'""$user""'"' "$XRAY_CONFIG"
    
    # Tambahkan ke config Xray (VLess GRPC)
    sed -i '/#vlessgrpc$/a\#& '"$user $exp_date"'\
},{"id": "'""$uuid""'","email": "'""$user""'"' "$XRAY_CONFIG"
    
    # Generate links
    local vlesslink1="vless://${uuid}@${DOMAIN}:443?path=/vless&security=tls&encryption=none&type=ws&host=${DOMAIN}&sni=${DOMAIN}#${user}"
    local vlesslink2="vless://${uuid}@${DOMAIN}:80?path=/vless&encryption=none&type=ws&host=${DOMAIN}#${user}"
    local vlesslink3="vless://${uuid}@${DOMAIN}:443?mode=gun&security=tls&encryption=none&type=grpc&serviceName=vless-grpc&sni=${DOMAIN}#${user}"
    
    # Restart service
    systemctl restart xray &>/dev/null
    systemctl restart nginx &>/dev/null
    
    # Simpan ke database vless
    mkdir -p "$(dirname "$VLESS_DB")"
    sed -i "/\b${user}\b/d" "$VLESS_DB" 2>/dev/null
    echo "#& $user $exp_date $uuid $quota $iplimit" >> "$VLESS_DB"
    
    # Simpan detail ke file
    mkdir -p /detail/vless/
    cat > "/detail/vless/$user.txt" <<-END
====================================
         📡 VLESS ACCOUNT
====================================

-------- 📋 ACCOUNT DETAILS --------
Remarks       : ${user}
Domain        : ${DOMAIN}
Quota         : ${quota} GB
IP Limit      : ${iplimit} IP

-------- 🔌 CONNECTION INFO --------
Port Non TLS  : 80, 8080, 2086, 8880
Port TLS      : 443, 8443
ID            : ${uuid}
Encryption    : none
Path          : /vless
Service Name  : vless-grpc

-------- 🔗 LINK & CONFIG ----------
TLS Link      : ${vlesslink1}

Non TLS Link  : ${vlesslink2}

gRPC Link     : ${vlesslink3}

-------- ⏱️  TIME INFO -------------
Active Period : ${masaaktif} Hari
Created On    : ${created_date}
Expires On    : ${exp_readable}

====================================
END
    
# Info port VLess
local port_tls="443, 8443"
local port_http="80, 8080, 2086, 8880"
local port_grpc="443"

printf '{"status":"success","username":"%s","uuid":"%s","domain":"%s","ip":"%s","quota":"%s","iplimit":"%s","expired":"%s","expired_readable":"%s","created":"%s","port_tls":"%s","port_http":"%s","port_grpc":"%s","path":"/vless","service_name":"vless-grpc","link_tls":"%s","link_http":"%s","link_grpc":"%s","detail_file":"/detail/vless/%s.txt"}\n' \
    "$user" "$uuid" "$DOMAIN" "$IP" "$quota" "$iplimit" "$exp_date" "$exp_readable" "$created_date" \
    "$port_tls" "$port_http" "$port_grpc" "$vlesslink1" "$vlesslink2" "$vlesslink3" "$user"
	
    return 0
}

# Eksekusi fungsi utama dengan parameter dari command line
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Parameter: username days quota iplimit
    create_vless "$1" "$2" "$3" "$4"
fi
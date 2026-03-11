#!/bin/bash
# Script untuk menghitung total client

# SSH Users
ssh="$(awk -F: '$3 >= 1000 && $1 != "nobody" {print $1}' /etc/passwd | wc -l)"

# XRAY Users dari config.json
if [ -f /etc/xray/config.json ]; then
    vms=$(grep -c '###' /etc/xray/config.json)
    vls=$(grep -c '#&' /etc/xray/config.json)
    trj=$(grep -c '#!' /etc/xray/config.json)
    ss=$(grep -c '#@&' /etc/xray/config.json)
    
    # Hitung (karena setiap user punya 2 baris?)
    let vmsx=vms/2
    let vlsx=vls/2
    let trjx=trj/2
    let ssx=ss/1
else
    vmsx=0
    vlsx=0
    trjx=0
    ssx=0
fi

# Total semua
total=$((ssh + vmsx + vlsx + trjx + ssx))

# Output JSON
cat <<EOF
{
  "ssh": $ssh,
  "vmess": $vmsx,
  "vless": $vlsx,
  "trojan": $trjx,
  "shadowsocks": $ssx,
  "total": $total
}
EOF
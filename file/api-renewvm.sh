#!/bin/bash
# Script untuk renew VMess via bot

read USER
read MASAAKTIF
read QUOTA
read IPLIM

exp=$(grep -wE "^### $USER" "/etc/xray/config.json" | cut -d ' ' -f 3 | sort | uniq)

if [ -z "$exp" ]; then
    echo '{"status":"error","message":"User tidak ditemukan"}'
    exit 1
fi

rm -f "/etc/limit/vmess/ip/${USER}" &>/dev/null
rm -f "/etc/vmess/$USER" &>/dev/null

mkdir -p /etc/limit/vmess/ip &>/dev/null
echo "$IPLIM" >> "/etc/limit/vmess/ip/${USER}"

mkdir -p /etc/vmess/ &>/dev/null
if [ -z "$QUOTA" ]; then QUOTA="0"; fi

c=$(echo "$QUOTA" | sed 's/[^0-9]*//g')
d=$(($c * 1024 * 1024 * 1024))
if [[ $c != "0" ]]; then
    echo "$d" >/etc/vmess/${USER}
fi

now=$(date +%Y-%m-%d)
d1=$(date -d "$exp" +%s)
d2=$(date -d "$now" +%s)
exp2=$(( (d1 - d2) / 86400 ))
exp3=$(($exp2 + $MASAAKTIF))
exp4=$(date -d "$exp3 days" +"%Y-%m-%d")

sed -i "/### $USER/c\### $USER $exp4" /etc/xray/config.json
sed -i "/### $USER/c\### $USER $exp4" /etc/vmess/.vmess.db
systemctl restart xray &>/dev/null

echo "{"
echo "  \"status\": \"success\","
echo "  \"username\": \"$USER\","
echo "  \"expired\": \"$exp4\""
echo "}"
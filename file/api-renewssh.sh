#!/bin/bash
# Script untuk renew SSH via bot
# Menerima input: username, days, quota, iplimit

read USERNAME
read DAYS
read QUOTA
read IP_LIMIT

if ! id "$USERNAME" &>/dev/null; then
    echo '{"status":"error","message":"Username tidak ditemukan"}'
    exit 1
fi

TODAY=$(date +%s)
EXTEND_SECONDS=$((DAYS * 86400))
EXPIRY_DATE=$((TODAY + EXTEND_SECONDS))
FORMATTED_EXPIRY=$(date -u --date="1970-01-01 $EXPIRY_DATE sec GMT" +%Y/%m/%d)
EXPIRY_DISPLAY=$(date -u --date="1970-01-01 $EXPIRY_DATE sec GMT" '+%d %b %Y')

passwd -u "$USERNAME" &>/dev/null
usermod -e "$FORMATTED_EXPIRY" "$USERNAME" &>/dev/null

mkdir -p /etc/ssh &>/dev/null
QUOTA_BYTES=$(($QUOTA * 1024 * 1024 * 1024))
echo "$QUOTA_BYTES" > /etc/ssh/$USERNAME

mkdir -p /etc/limit/ssh/ip &>/dev/null
echo "$IP_LIMIT" > /etc/limit/ssh/ip/$USERNAME

# Output JSON
echo "{"
echo "  \"status\": \"success\","
echo "  \"username\": \"$USERNAME\","
echo "  \"expired\": \"$(date -u --date="1970-01-01 $EXPIRY_DATE sec GMT" +%Y-%m-%d)\","
echo "  \"expired_readable\": \"$EXPIRY_DISPLAY\""
echo "}"
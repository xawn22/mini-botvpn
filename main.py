#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT TELEGRAM - Create SSH/VMess/VLess/Trojan
Version: 3.0 - Config from JSON
"""

import subprocess
import asyncio
import json
import re
import os
import logging
import random
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ConversationHandler, MessageHandler, filters, ContextTypes
)

# ==========================================
# LOAD KONFIGURASI DARI JSON
# ==========================================
def load_config():
    """Load konfigurasi dari file config.json"""
    if not os.path.exists('config.json'):
        print("❌ File config.json tidak ditemukan!")
        print("📝 Jalankan dulu: bash install.sh")
        exit(1)
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    return config

config = load_config()

TOKEN = config['token']
ALLOWED_USERS = config['admin_ids']
SCRIPTS = config['scripts']

# ==========================================
# STATE UNTUK CONVERSATION
# ==========================================
PROTOKOL, INPUT_DATA = range(2)

# ==========================================
# LOGGING
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# FUNGSI BANTUAN
# ==========================================
def is_allowed(user_id):
    return user_id in ALLOWED_USERS

def validate_username(username):
    return bool(re.match(r'^[a-zA-Z0-9_]+$', username))

def validate_number(value, min_val, max_val):
    try:
        val = int(value)
        return min_val <= val <= max_val
    except:
        return False

def generate_password(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


async def call_script_async(script_path, args_list):
    """Jalankan script shell secara async tanpa blocking bot"""
    try:
        process = await asyncio.create_subprocess_exec(
            script_path, *args_list,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {"status": "error", "message": "Script timeout"}

        stdout = stdout.decode()
        json_pattern = r'(\{.*\})'
        match = re.search(json_pattern, stdout, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        else:
            return {"status": "error", "message": "Script tidak mengembalikan JSON"}

    except Exception as e:
        logging.error(f"Error call_script_async: {e}")
        return {"status": "error", "message": str(e)}
		

# ==========================================
# ERROR HANDLER (UPDATE)
# ==========================================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    try:
        logger.error(f"Update {update} caused error {context.error}")
        
        # Log detail error
        import traceback
        traceback.print_exc()
        
        # Kasih tahu user kalau error
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Terjadi kesalahan internal.\nSilakan coba lagi."
            )
    except:
        pass
		
# ==========================================
# HANDLER START (VERSI BARU - LANGSUNG TAMPIL STATUS + NOMOR URUT)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Kamu tidak diizinkan menggunakan bot ini.")
        return ConversationHandler.END
    
    # Loading message
    loading = await update.message.reply_text("⏱️ Memuat data...")
    
    # Ambil semua data
    counts = await get_account_counts()
    expired_today, expired_soon = await check_expired_users()
    server_info = await get_server_info()
    
    # Cek script status
    scripts_ok = 0
    scripts_total = len(SCRIPTS)
    for proto, script in SCRIPTS.items():
        if os.path.exists(script):
            scripts_ok += 1
    
    # Buat tampilan status
    status_text = (
        "╭━━━━━━━━━━━━━━━━━━╮\n"
        "┃      🤖 𝗔𝘂𝘁𝗼𝗦𝗰𝗿𝗶𝗽𝘁 𝗔𝗜𝗢 𝗩.1     ┃\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        
        "📦 JUMLAH AKUN\n"
        "──────────────────\n"
        f"🔰 SSH      : {counts['ssh']} Akun\n"
        f"🚀 VMess   : {counts['vmess']} Akun\n"
        f"📡 VLess    : {counts['vless']} Akun\n"
        f"🛡️ Trojan   : {counts['trojan']} Akun\n\n"
    )
    
    # EXPIRED HARI INI (DENGAN NOMOR URUT)
    if expired_today:
        status_text += "⚠️ Expired Hari Ini:\n"
        status_text += "──────────────────\n"
        for i, (proto, user, days, status) in enumerate(expired_today, 1):
            status_text += f"{i}. {user} - {proto} - {status}\n"
        status_text += "\n"
    else:
        status_text += "⚠️ Expired Hari Ini:\n"
        status_text += "──────────────────\n"
        status_text += "• Tidak ada\n\n"
    
    # EXPIRED 7 HARI LAGI (DENGAN NOMOR URUT)
    if expired_soon:
        status_text += "⏳ Expired Mendatang:\n"
        status_text += "──────────────────\n"
        for i, (proto, user, days, text) in enumerate(expired_soon, 1):
            status_text += f"{i}. {user} - {proto} - {text}\n"
        status_text += "\n"
    else:
        status_text += "⏳ Expired Mendatang:\n"
        status_text += "──────────────────\n"
        status_text += "• Tidak ada\n\n"
    
    # SERVER INFO
    status_text += (
        "🖥️ SERVER INFO\n"
        "──────────────────\n"
        f"⏰ Uptime    : {server_info['uptime']}\n"
        f"💾 RAM       : {server_info['ram']}\n"
        f"💿 Disk      : {server_info['disk']}\n"
        f"✅ Script    : {scripts_ok}/{scripts_total} Aktif\n\n"
        
        "👤 USER\n"
        "──────────────────\n"
        f"🆔 ID       : {user_id}\n"
    )
    
    # Hapus loading message
    await loading.delete()
    
    # Buat tombol protokol
    keyboard = [
        [
            InlineKeyboardButton("⚡ SSH", callback_data='proto_ssh'),
            InlineKeyboardButton("🚀 VMess", callback_data='proto_vmess'),
        ],
        [
            InlineKeyboardButton("📡 VLess", callback_data='proto_vless'),
            InlineKeyboardButton("🛡️ Trojan", callback_data='proto_trojan'),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data='proto_batal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Kirim pesan (status + menu)
    await update.message.reply_text(
        f"{status_text}\n\n🚀 <b>Pilih Protokol yang Ingin Dibuat:</b>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return PROTOKOL

# ==========================================
# HANDLER TOMBOL PROTOKOL
# ==========================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'proto_batal':
        await query.edit_message_text("❌ Pembuatan akun dibatalkan.")
        return ConversationHandler.END
    
    # Simpan protokol yang dipilih
    protocol = data.replace('proto_', '')
    context.user_data['selected_protocol'] = protocol
    
    # Mapping nama protokol untuk display
    proto_names = {
        'ssh': '🔰 SSH',
        'vmess': '📡 VMess',
        'vless': '📡 VLess',
        'trojan': '🛡️ Trojan'
    }
    
    await query.edit_message_text(
        f"✅ <b>{proto_names[protocol]}</b>\n\n"
        f"📝 Masukkan data dalam format:\n"
        f"<code>username hari quota iplimit</code>\n\n"
        f"Contoh: <code>myname 1 1 1</code>\n\n"
        f"Keterangan:\n"
        f"• username: huruf/angka/_\n"
        f"• hari: 1-365\n"
        f"• quota: 0-999 GB (0 = unlimited)\n"
        f"• iplimit: 0-100 IP (0 = unlimited)\n\n"
		f"• untuk ssh support custom pw\n\n"
        f"Ketik /batal untuk membatalkan.",
        parse_mode='HTML'
    )
    
    return INPUT_DATA
	

# ==========================================
# FUNGSI AMBIL JUMLAH AKUN (FIX ERROR HANDLING)
# ==========================================
async def get_account_counts():
    """Ambil semua jumlah akun sekaligus dari total-client.sh"""
    # GANTI PATH INI SESUAI LOKASI SCRIPT KAMU!
    script_path = "/etc/conf/server.sh"  # <-- Sesuaikan!
    
    default_counts = {
        'ssh': '0',
        'vmess': '0', 
        'vless': '0',
        'trojan': '0',
        'shadowsocks': '0',
        'total': '0'
    }
    
    try:
        if not os.path.exists(script_path):
            print(f"❌ Script tidak ditemukan: {script_path}")
            return default_counts
        
        # Jalankan script bash
        process = await asyncio.create_subprocess_exec(
            "bash", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return default_counts
        
        # Parse output
        stdout_str = stdout.decode('utf-8', errors='ignore').strip()
        
        # Cari JSON
        json_pattern = r'(\{.*\})'
        match = re.search(json_pattern, stdout_str, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            try:
                data = json.loads(json_str)
                return {
                    'ssh': str(data.get('ssh', '0')),
                    'vmess': str(data.get('vmess', '0')),
                    'vless': str(data.get('vless', '0')),
                    'trojan': str(data.get('trojan', '0')),
                    'shadowsocks': str(data.get('shadowsocks', '0')),
                    'total': str(data.get('total', '0'))
                }
            except:
                return default_counts
        
        return default_counts
        
    except Exception as e:
        print(f"Error di get_account_counts: {e}")
        return default_counts



async def get_server_info():
    """Ambil info server: uptime, RAM, disk"""
    
    info = {
        'uptime': 'N/A',
        'ram': 'N/A',
        'disk': 'N/A'
    }
    
    try:
        # UPTIME
        uptime_proc = await asyncio.create_subprocess_exec(
            "uptime", "-p",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await uptime_proc.communicate()
        uptime_str = stdout.decode().strip().replace('up ', '')
        info['uptime'] = uptime_str if uptime_str else 'N/A'
        
        # RAM USAGE
        ram_proc = await asyncio.create_subprocess_exec(
            "free", "-h",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await ram_proc.communicate()
        ram_lines = stdout.decode().split('\n')
        if len(ram_lines) > 1:
            ram_parts = ram_lines[1].split()
            if len(ram_parts) >= 3:
                info['ram'] = f"{ram_parts[2]}/{ram_parts[1]}"
        
        # DISK USAGE
        disk_proc = await asyncio.create_subprocess_exec(
            "df", "-h", "/",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await disk_proc.communicate()
        disk_lines = stdout.decode().split('\n')
        if len(disk_lines) > 1:
            disk_parts = disk_lines[1].split()
            if len(disk_parts) >= 5:
                info['disk'] = f"{disk_parts[2]}/{disk_parts[1]} ({disk_parts[4]})"
        
    except Exception as e:
        print(f"Error get server info: {e}")
    
    return info
	
	
async def check_expired_users():
    """Cek user expired untuk semua protokol sesuai format config.json - ANTI DUPLIKAT + NOMOR URUT"""
    
    expired_today = []
    expired_soon = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # BUAT SET UNTUK ANTI DUPLIKAT
    processed_users = set()
    
    # 1. CEK SSH
    ssh_db = "/etc/ssh/.ssh.db"
    if os.path.exists(ssh_db):
        try:
            with open(ssh_db, 'r') as f:
                for line in f:
                    if line.startswith('#ssh#'):
                        parts = line.strip().split()
                        if len(parts) >= 8:
                            user = parts[1]
                            
                            # ANTI DUPLIKAT SSH
                            user_key = f"ssh_{user}"
                            if user_key in processed_users:
                                continue
                            processed_users.add(user_key)
                            
                            try:
                                day = parts[5]
                                month = parts[6]
                                year = parts[7]
                                exp_str = f"{day} {month} {year}"
                                exp_date = datetime.strptime(exp_str, '%d %b %Y')
                                exp_date = exp_date.replace(hour=0, minute=0, second=0)
                                
                                diff_days = (exp_date - today).days
                                
                                if diff_days < 0:
                                    expired_today.append(("SSH", user, diff_days, "EXPIRED"))
                                elif diff_days == 0:
                                    expired_today.append(("SSH", user, diff_days, "HARI INI"))
                                elif diff_days <= 7:
                                    expired_soon.append(("SSH", user, diff_days, f"{diff_days} hari"))
                            except:
                                pass
        except:
            pass
    

    xray_config = "/etc/xray/config.json"
    if os.path.exists(xray_config):
        try:
            with open(xray_config, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                
                # CEK VLESS (pattern: #& username YYYY-MM-DD)
                if '#&' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        username = parts[1]
                        exp_str = parts[2]
                        
                        # ANTI DUPLIKAT VLESS
                        user_key = f"vless_{username}"
                        if user_key in processed_users:
                            continue
                        processed_users.add(user_key)
                        
                        try:
                            exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
                            exp_date = exp_date.replace(hour=0, minute=0, second=0)
                            
                            diff_days = (exp_date - today).days
                            
                            if diff_days < 0:
                                expired_today.append(("VLess", username, diff_days, "EXPIRED"))
                            elif diff_days == 0:
                                expired_today.append(("VLess", username, diff_days, "HARI INI"))
                            elif diff_days <= 7:
                                expired_soon.append(("VLess", username, diff_days, f"{diff_days} hari"))
                        except:
                            pass
                
                # CEK VMESS (pattern: ### username YYYY-MM-DD)
                if '###' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        username = parts[1]
                        exp_str = parts[2]
                        
                        # ANTI DUPLIKAT VMESS
                        user_key = f"vmess_{username}"
                        if user_key in processed_users:
                            continue
                        processed_users.add(user_key)
                        
                        try:
                            exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
                            exp_date = exp_date.replace(hour=0, minute=0, second=0)
                            
                            diff_days = (exp_date - today).days
                            
                            if diff_days < 0:
                                expired_today.append(("VMess", username, diff_days, "EXPIRED"))
                            elif diff_days == 0:
                                expired_today.append(("VMess", username, diff_days, "HARI INI"))
                            elif diff_days <= 7:
                                expired_soon.append(("VMess", username, diff_days, f"{diff_days} hari"))
                        except:
                            pass
                
                # CEK TROJAN (pattern: #! username YYYY-MM-DD)
                if '#!' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        username = parts[1]
                        exp_str = parts[2]
                        
                        # ANTI DUPLIKAT TROJAN
                        user_key = f"trojan_{username}"
                        if user_key in processed_users:
                            continue
                        processed_users.add(user_key)
                        
                        try:
                            exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
                            exp_date = exp_date.replace(hour=0, minute=0, second=0)
                            
                            diff_days = (exp_date - today).days
                            
                            if diff_days < 0:
                                expired_today.append(("Trojan", username, diff_days, "EXPIRED"))
                            elif diff_days == 0:
                                expired_today.append(("Trojan", username, diff_days, "HARI INI"))
                            elif diff_days <= 7:
                                expired_soon.append(("Trojan", username, diff_days, f"{diff_days} hari"))
                        except:
                            pass
                            
        except Exception as e:
            print(f"Error baca config.json: {e}")
    
    return expired_today, expired_soon
# ==========================================
# HANDLER INPUT DATA (VERSI BARU - 5 PARAMETER)
# ==========================================
async def input_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Tidak diizinkan")
        return ConversationHandler.END
    
    # Ambil protokol yang dipilih
    protocol = context.user_data.get('selected_protocol')
    if not protocol:
        await update.message.reply_text("❌ Sesi expired. Silakan /start lagi.")
        return ConversationHandler.END
    
    # Parse input
    text = update.message.text.strip()
    parts = text.split()
    
    # CEK JUMLAH PARAMETER (SEKARANG 5 UNTUK SSH, 4 UNTUK LAINNYA)
    if protocol == 'ssh':
        if len(parts) != 5:
            await update.message.reply_text(
                "❌ <b>Format SSH harus:</b> <code>username password hari quota iplimit</code>\n"
                "Contoh: <code>paijo rahasia123 30 10 3</code>\n\n"
                "Keterangan:\n"
                "• username: huruf/angka/_\n"
                "• password: minimal 3 karakter (tanpa spasi)\n"
                "• hari: 1-365\n"
                "• quota: 0-999 GB (0 = unlimited)\n"
                "• iplimit: 0-100 IP (0 = unlimited)\n\n"
                "Ketik /batal untuk membatalkan.",
                parse_mode='HTML'
            )
            return INPUT_DATA
    else:
        if len(parts) != 4:
            await update.message.reply_text(
                "❌ <b>Format SSH harus:</b> <code>username password hari quota iplimit</code>\n"
                "Contoh: <code>paijo rahasia123 30 10 3</code>\n\n"
                "Keterangan:\n"
                "• username: huruf/angka/_\n"
                "• password: minimal 3 karakter (tanpa spasi)\n"
                "• hari: 1-365\n"
                "• quota: 0-999 GB (0 = unlimited)\n"
                "• iplimit: 0-100 IP (0 = unlimited)\n\n"
                "Ketik /batal untuk membatalkan.",
                parse_mode='HTML'
            )
            return INPUT_DATA
    
    # PARSING SESUAI PROTOCOL
    if protocol == 'ssh':
        # SSH: username, password, hari, quota, iplimit
        username, password, days, quota, iplimit = parts
    else:
        # VMess/VLess/Trojan: username, hari, quota, iplimit
        username, days, quota, iplimit = parts
        password = None  # Tidak dipakai untuk selain SSH
    
    # Validasi username
    if not validate_username(username):
        await update.message.reply_text(
            "❌ <b>Username tidak valid.</b>\n"
            "Hanya boleh huruf, angka, dan underscore.\n\n"
            "Silakan coba lagi:",
            parse_mode='HTML'
        )
        return INPUT_DATA
    
    # VALIDASI PASSWORD (khusus SSH)
    if protocol == 'ssh':
        if len(password) < 3:
            await update.message.reply_text(
                "❌ <b>Password terlalu pendek.</b>\n"
                "Minimal 3 karakter.\n\n"
                "Silakan coba lagi:",
                parse_mode='HTML'
            )
            return INPUT_DATA
        
        if ' ' in password:
            await update.message.reply_text(
                "❌ <b>Password tidak boleh mengandung spasi.</b>\n\n"
                "Silakan coba lagi:",
                parse_mode='HTML'
            )
            return INPUT_DATA
    
    # Validasi angka
    if not validate_number(days, 1, 365):
        await update.message.reply_text(
            "❌ <b>Hari harus 1-365.</b>\n\nSilakan coba lagi:",
            parse_mode='HTML'
        )
        return INPUT_DATA
    
    if not validate_number(quota, 0, 999):
        await update.message.reply_text(
            "❌ <b>Quota harus 0-999 GB.</b>\n\nSilakan coba lagi:",
            parse_mode='HTML'
        )
        return INPUT_DATA
    
    if not validate_number(iplimit, 0, 100):
        await update.message.reply_text(
            "❌ <b>Limit IP harus 0-100.</b>\n\nSilakan coba lagi:",
            parse_mode='HTML'
        )
        return INPUT_DATA
    
    # Konversi ke integer
    days = int(days)
    quota = int(quota)
    iplimit = int(iplimit)
    
    # Progress message
    progress = await update.message.reply_text(f"⏱️ Membuat akun {protocol.upper()}...")
    
    # Siapkan parameter sesuai protocol
    script_path = SCRIPTS[protocol]
    
    if protocol == 'ssh':
        # SSH: username, password, quota, iplimit, days
        args_list = [username, password, str(quota), str(iplimit), str(days)]
    elif protocol == 'vmess':
        # VMess: username, days, quota, iplimit
        args_list = [username, str(days), str(quota), str(iplimit)]
    elif protocol == 'vless':
        # VLess: username, days, quota, iplimit
        args_list = [username, str(days), str(quota), str(iplimit)]
    elif protocol == 'trojan':
        # Trojan: username, days, quota, iplimit
        args_list = [username, str(days), str(quota), str(iplimit)]
    else:
        args_list = [username, str(days), str(quota), str(iplimit)]
    
    # Panggil script
    result = await call_script_async(script_path, args_list)
    
    await progress.delete()
    
    # Tampilkan hasil
    if result.get('status') == 'success':
        
        if protocol == 'ssh':
            pesan = (
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  🔰 <b>SSH ACCOUNT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                f"📋 <b>ACCOUNT DETAILS</b>\n"
                f"──────────────────\n"
                f"👤 Username : <code>{username}</code>\n"
                f"🔑 Password : <code>{password}</code>\n"
                f"🌍 Host/IP  : {result.get('domain', 'N/A')}\n"
                f"💾 Quota    : {quota} GB\n"
                f"👥 Limit IP : {iplimit}\n"
                f"📅 Expired  : {result.get('expired_readable', 'N/A')}\n\n"
                
                f"🔌 <b>CONNECTION PORTS</b>\n"
                f"──────────────────\n"
                f"🔹 OpenSSH    : {result.get('ssh_port', '22')}\n"
                f"🔹 Dropbear   : {result.get('dropbear_port', '109, 143')}\n"
                f"🔹 SSH WS     : {result.get('ws_port', '80, 8080, 2086, 8880')}\n"
                f"🔹 SSL/TLS    : {result.get('ssl_port', '443, 8443')}\n"
                f"🔹 SSH UDP    : {result.get('udp_port', '1-65535')}\n"
                f"🔹 DNS        : {result.get('dns_port', '53, 2222')}\n"
                f"🔹 BadVPN     : {result.get('badvpn_port', '7100, 7300')}\n\n"
                
                f"📦 <b>PAYLOAD</b>\n"
                f"──────────────────\n"
                f"<code>{result.get('payload', 'GET / HTTP/1.1[crlf]Host: [host][crlf]Upgrade: websocket[crlf][crlf]')}</code>\n\n"
                
                f"🌐 <b>SLOWDNS</b>\n"
                f"──────────────────\n"
                f"🔹 NS       : {result.get('slowdns', 'N/A')}\n"
                f"🔹 Pubkey   : <code>{result.get('pubkey', 'N/A')}</code>\n"
            )
        
        elif protocol == 'vmess':
            pesan = (
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  📡 <b>VMESS ACCOUNT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                f"📋 <b>ACCOUNT DETAILS</b>\n"
                f"──────────────────\n"
                f"👤 Remarks    : <code>{username}</code>\n"
                f"🔑 UUID       : <code>{result.get('uuid', 'N/A')}</code>\n"
                f"🌍 Host/IP    : {result.get('domain', 'N/A')}\n"
                f"💾 Quota      : {quota} GB\n"
                f"👥 Limit IP   : {iplimit}\n"
                f"📅 Expired    : {result.get('expired_readable', 'N/A')}\n\n"
                
                f"🔌 <b>CONNECTION INFO</b>\n"
                f"──────────────────\n"
                f"🔹 Port TLS   : {result.get('port_tls', '443, 8443')}\n"
                f"🔹 Port HTTP  : {result.get('port_http', '80, 8080, 2086, 8880')}\n"
                f"🔹 Port gRPC  : {result.get('port_grpc', '443')}\n"
                f"🔹 Alter ID   : 0\n"
                f"🔹 Security   : auto\n"
                f"🔹 Network    : ws\n"
                f"🔹 Path       : {result.get('path', '/vmess')}\n"
                f"🔹 Service    : {result.get('service_name', 'vmess-grpc')}\n\n"
                
                f"🔗 <b>LINKS</b>\n"
                f"──────────────────\n"
            )
            
            if result.get('link_tls'):
                pesan += f"🔹 TLS      :\n<code>{result['link_tls']}</code>\n\n"
            if result.get('link_http'):
                pesan += f"🔹 HTTP     :\n<code>{result['link_http']}</code>\n\n"
            if result.get('link_grpc'):
                pesan += f"🔹 gRPC     :\n<code>{result['link_grpc']}</code>\n"
        
        elif protocol == 'vless':
            pesan = (
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  📡 <b>VLESS ACCOUNT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                f"📋 <b>ACCOUNT DETAILS</b>\n"
                f"──────────────────\n"
                f"👤 Remarks    : <code>{username}</code>\n"
                f"🔑 ID         : <code>{result.get('uuid', 'N/A')}</code>\n"
                f"🌍 Host/IP    : {result.get('domain', 'N/A')}\n"
                f"💾 Quota      : {quota} GB\n"
                f"👥 Limit IP   : {iplimit}\n"
                f"📅 Expired    : {result.get('expired_readable', 'N/A')}\n\n"
                
                f"🔌 <b>CONNECTION INFO</b>\n"
                f"──────────────────\n"
                f"🔹 Port TLS   : {result.get('port_tls', '443, 8443')}\n"
                f"🔹 Port HTTP  : {result.get('port_http', '80, 8080, 2086, 8880')}\n"
                f"🔹 Port gRPC  : {result.get('port_grpc', '443')}\n"
                f"🔹 Encryption : none\n"
                f"🔹 Network    : ws\n"
                f"🔹 Path       : {result.get('path', '/vless')}\n"
                f"🔹 Service    : {result.get('service_name', 'vless-grpc')}\n\n"
                
                f"🔗 <b>LINKS</b>\n"
                f"──────────────────\n"
            )
            
            if result.get('link_tls'):
                pesan += f"🔹 TLS      :\n<code>{result['link_tls']}</code>\n\n"
            if result.get('link_http'):
                pesan += f"🔹 HTTP     :\n<code>{result['link_http']}</code>\n\n"
            if result.get('link_grpc'):
                pesan += f"🔹 gRPC     :\n<code>{result['link_grpc']}</code>\n"
        
        elif protocol == 'trojan':
            pesan = (
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  🛡️ <b>TROJAN ACCOUNT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                f"📋 <b>ACCOUNT DETAILS</b>\n"
                f"──────────────────\n"
                f"👤 Remarks    : <code>{username}</code>\n"
                f"🔑 Password   : <code>{result.get('password', 'N/A')}</code>\n"
                f"🌍 Host/IP    : {result.get('domain', 'N/A')}\n"
                f"💾 Quota      : {quota} GB\n"
                f"👥 Limit IP   : {iplimit}\n"
                f"📅 Expired    : {result.get('expired_readable', 'N/A')}\n\n"
                
                f"🔌 <b>CONNECTION INFO</b>\n"
                f"──────────────────\n"
                f"🔹 Port TLS   : {result.get('port_tls', '443, 8443')}\n"
                f"🔹 Port gRPC  : {result.get('port_grpc', '443')}\n"
                f"🔹 Path       : {result.get('path', '/trojan-ws')}\n"
                f"🔹 Service    : {result.get('service_name', 'trojan-grpc')}\n\n"
                
                f"🔗 <b>LINKS</b>\n"
                f"──────────────────\n"
            )
            
            if result.get('link_ws'):
                pesan += f"🔹 WebSocket :\n<code>{result['link_ws']}</code>\n\n"
            if result.get('link_grpc'):
                pesan += f"🔹 gRPC      :\n<code>{result['link_grpc']}</code>\n"
        
        pesan += f"\n━━━━━━━━━━━━━━━━━━━━━━"
        
        # Tombol untuk buat lagi
        keyboard = [[InlineKeyboardButton("Thank You🥳", callback_data='buat_lagi')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(pesan, parse_mode='HTML', reply_markup=reply_markup)
        
    else:
        await update.message.reply_text(
            f"❌ <b>GAGAL</b>\n\n{result.get('message', 'Unknown error')}",
            parse_mode='HTML'
        )
    
    # Hapus data session
    context.user_data.clear()
    return ConversationHandler.END

# ==========================================
# HANDLER BATAL
# ==========================================
async def batal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Pembuatan akun dibatalkan.")
    context.user_data.clear()
    return ConversationHandler.END

# ==========================================
# HANDLER BUAT LAGI
# ==========================================
async def buat_lagi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Reset user data
    context.user_data.clear()
    
    # Tampilkan menu utama
    keyboard = [
        [
            InlineKeyboardButton("⚡ SSH", callback_data='proto_ssh'),
            InlineKeyboardButton("🚀 VMess", callback_data='proto_vmess'),
        ],
        [
            InlineKeyboardButton("📡 VLess", callback_data='proto_vless'),
            InlineKeyboardButton("🛡️ Trojan", callback_data='proto_trojan'),
        ],
        [InlineKeyboardButton("📊 Status Bot", callback_data='menu_status')],
        [InlineKeyboardButton("❌ Batal", callback_data='proto_batal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # EDIT pesan yang sama
    await query.edit_message_text(
        "🚀 <b>Pilih Protokol yang Ingin Dibuat:</b>\n\n"
        "Klik tombol di bawah untuk memilih:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return PROTOKOL

# ==========================================
# HANDLER STATUS (Command)
# ==========================================
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Tidak diizinkan")
        return
    
    status_text = "<b>📊 STATUS BOT</b>\n\n"
    
    for proto, script in SCRIPTS.items():
        if os.path.exists(script):
            status_text += f"✅ {proto.upper()}: <code>{script}</code> (OK)\n"
        else:
            status_text += f"❌ {proto.upper()}: <code>{script}</code> (TIDAK DITEMUKAN)\n"
    
    status_text += f"\n👤 User ID: <code>{user_id}</code>"
    
    await update.message.reply_text(status_text, parse_mode='HTML')

# ==========================================
# MAIN
# ==========================================
def main():
    print("=" * 50)
    print("🚀 BOT TUNNELING - BUTTON VERSION (HTML)")
    print("=" * 50)
    print(f"Token: {TOKEN[:10]}...{TOKEN[-5:]}")
    print(f"Allowed Users: {ALLOWED_USERS}")
    print("=" * 50)
    
    # Cek script
    for proto, script in SCRIPTS.items():
        if os.path.exists(script):
            print(f"✅ {proto.upper()}: {script}")
        else:
            print(f"❌ {proto.upper()}: {script} (TIDAK DITEMUKAN)")
    
    print("=" * 50)
    
    # Buat aplikasi
    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PROTOKOL: [
                CallbackQueryHandler(button_handler, pattern='^proto_'),
            ],
            INPUT_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_data)],
        },
        fallbacks=[
            CommandHandler('batal', batal),
            CallbackQueryHandler(buat_lagi, pattern='^buat_lagi$'),
        ],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("status", status_command))
    
    print("✅ Bot siap! Klik /start untuk memulai")
    app.run_polling(timeout=30, read_timeout=30)

if __name__ == "__main__":
    main()
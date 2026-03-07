#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT TELEGRAM - Create SSH/VMess/VLess/Trojan
Version: 3.0 - Config from JSON
"""

import subprocess
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

def call_script(script_path, args_list):
    try:
        logger.info(f"Running: {script_path} {' '.join(args_list)}")
        
        result = subprocess.run(
            [script_path] + args_list,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        json_pattern = r'(\{.*\})'
        match = re.search(json_pattern, result.stdout, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        else:
            return {"status": "error", "message": "Script tidak mengembalikan JSON"}
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error", "message": str(e)}

# ==========================================
# ERROR HANDLER
# ==========================================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ <b>Terjadi kesalahan internal.</b>\nSilakan coba lagi.",
            parse_mode='HTML'
        )

# ==========================================
# HANDLER START
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Kamu tidak diizinkan menggunakan bot ini.")
        return ConversationHandler.END
    
    # Buat tombol protokol + tombol status
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
    
    await update.message.reply_text(
        "🚀 <b>Pilih Protokol yang Ingin Dibuat:</b>\n\n"
        "Klik tombol di bawah untuk memilih:",
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
        f"Contoh: <code>paijo 30 10 3</code>\n\n"
        f"Keterangan:\n"
        f"• username: huruf/angka/_\n"
        f"• hari: 1-365\n"
        f"• quota: 0-999 GB (0 = unlimited)\n"
        f"• iplimit: 0-100 IP (0 = unlimited)\n\n"
        f"Ketik /batal untuk membatalkan.",
        parse_mode='HTML'
    )
    
    return INPUT_DATA

# ==========================================
# HANDLER MENU STATUS
# ==========================================
async def menu_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk tombol Status"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    status_text = "<b>📊 STATUS BOT</b>\n\n"
    
    for proto, script in SCRIPTS.items():
        if os.path.exists(script):
            status_text += f"✅ {proto.upper()}: <code>{script}</code> (OK)\n"
        else:
            status_text += f"❌ {proto.upper()}: <code>{script}</code> (TIDAK DITEMUKAN)\n"
    
    status_text += f"\n👤 User ID: <code>{user_id}</code>"
    
    # Tombol kembali ke menu
    keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu", callback_data='kembali_ke_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        status_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return PROTOKOL

# ==========================================
# HANDLER KEMBALI KE MENU
# ==========================================
async def kembali_ke_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk tombol Kembali ke Menu"""
    query = update.callback_query
    await query.answer()
    
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
    
    await query.edit_message_text(
        "🚀 <b>Pilih Protokol yang Ingin Dibuat:</b>\n\n"
        "Klik tombol di bawah untuk memilih:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return PROTOKOL

# ==========================================
# HANDLER INPUT DATA
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
    
    if len(parts) != 4:
        await update.message.reply_text(
            "❌ <b>Format harus:</b> <code>username hari quota iplimit</code>\n"
            "Contoh: <code>paijo 30 10 3</code>\n\n"
            "Silakan coba lagi:",
            parse_mode='HTML'
        )
        return INPUT_DATA
    
    username, days, quota, iplimit = parts
    
    # Validasi username
    if not validate_username(username):
        await update.message.reply_text(
            "❌ <b>Username tidak valid.</b>\n"
            "Hanya boleh huruf, angka, dan underscore.\n\n"
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
    
    # Konversi
    days = int(days)
    quota = int(quota)
    iplimit = int(iplimit)
    
    # Progress message
    progress = await update.message.reply_text(f"⏱️ Membuat akun {protocol.upper()}...")
    
    # Siapkan parameter
    script_path = SCRIPTS[protocol]
    
    if protocol == 'ssh':
        password = generate_password()
        args_list = [username, password, str(quota), str(iplimit), str(days)]
    else:
        args_list = [username, str(days), str(quota), str(iplimit)]
    
    # Panggil script
    result = call_script(script_path, args_list)
    
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
                CallbackQueryHandler(menu_status, pattern='^menu_status$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
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
    app.run_polling()

if __name__ == "__main__":
    main()

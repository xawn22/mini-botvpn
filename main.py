#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT TELEGRAM - Create SSH/VMess/VLess/Trojan
Version: 22.0 - COMPLETE WITH REGION & STOCK MANAGEMENT
Fitur: Create, Renew, Trial, Voucher, Auto Renew, Topup QRIS, Log Channel, Broadcast, Region, Stock Management
"""

import subprocess
import asyncio
import json
import re
import os
import sys
import logging
import random
import string
import sqlite3
import shutil
import secrets
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ConversationHandler, MessageHandler, filters, ContextTypes
)
from pakasir_core import (
    get_pakasir, 
    init_pakasir, 
    generate_qr_image,
    delete_pakasir_transaction,
    save_pakasir_transaction
)

# ==========================================
# SUPPRESS WARNINGS
# ==========================================
warnings.filterwarnings("ignore", category=UserWarning, module='telegram.ext')
logging.getLogger('telegram.ext.ConversationHandler').setLevel(logging.ERROR)

def load_config():
    """Load konfigurasi dari file config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    print(f"📁 Mencari config di: {config_path}")
    
    if not os.path.exists(config_path):
        print("❌ File config.json tidak ditemukan!")
        print("📝 Jalankan dulu: bash install.sh")
        exit(1)
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"✅ Config loaded: {list(config.keys())}")
    return config

# ==========================================
# DEFINISIKAN CONFIG DULU
# ==========================================
config = load_config()

# ==========================================
# AMBIL SEMUA KONFIGURASI DARI JSON
# ==========================================
TOKEN = config['token']
ALLOWED_USERS = config['admin_ids']
OWNER_ID = config.get('owner_id', ALLOWED_USERS[0] if ALLOWED_USERS else 1668998643)

# KONFIGURASI CHANNEL
CHANNEL_ID = config.get('channel', {}).get('id', -1003804380159)
CHANNEL_URL = config.get('channel', {}).get('url', "https://t.me/mytesssssyyyy")

# SCRIPTS
SCRIPTS = config['scripts']
RENEW_SCRIPTS = config.get('renew_scripts', {})

# HARGA
if 'prices' in config:
    PRICES = config['prices']
    print(f"✅ Harga dari config.json: {PRICES}")
else:
    PRICES = {
        'ssh': 500,
        'vmess': 700,
        'vless': 700,
        'trojan': 800
    }
    print("⚠️ Harga menggunakan default (config.json tidak punya 'prices')")

# DEFAULT SETTINGS
if 'defaults' in config:
    DEFAULT_IP_LIMIT = config['defaults'].get('ip_limit', 4)
    DEFAULT_QUOTA = config['defaults'].get('quota', 250)
else:
    DEFAULT_IP_LIMIT = 4
    DEFAULT_QUOTA = 250

# TRIAL CONFIG
if 'trial' in config:
    TRIAL_CONFIG = config['trial']
    print(f"✅ Trial config dari config.json: {TRIAL_CONFIG}")
else:
    TRIAL_CONFIG = {
        'enabled': True,
        'duration_hours': 1,
        'quota': 1,
        'iplimit': 2,
        'max_per_day': 2,
        'username_prefix': 'trial'
    }
    print("⚠️ Trial config menggunakan default")

# QRIS PATH
QRIS_IMAGE_PATH = config.get('qris_path', "/etc/conf/qris.jpg")

print(f"💰 Harga SSH: {PRICES['ssh']}")
print(f"💰 Harga VMess: {PRICES['vmess']}")
print(f"💰 Harga VLess: {PRICES['vless']}")
print(f"💰 Harga Trojan: {PRICES['trojan']}")

# ==========================================
# STATE UNTUK CONVERSATION
# ==========================================
(
    PROTOKOL, 
    INPUT_USERNAME, 
    INPUT_PASSWORD, 
    INPUT_DAYS, 
    TOPUP_NOMINAL,
    TOPUP_BUKTI,
    VOUCHER_MENU,
    VOUCHER_GENERATE,
    VOUCHER_GENERATE_VALUE,
    VOUCHER_GENERATE_LIMIT,
    VOUCHER_GENERATE_EXPIRE,
    VOUCHER_GENERATE_MIN_BALANCE,
    RESET_SALDO_MENU,
    RESET_SALDO_INPUT,
    VOUCHER_REDEEM,
    RENEW_MENU,
    RENEW_USERNAME,
    RENEW_DAYS,
    TRIAL_MENU,
    AUTO_RENEW_MENU,
    AUTO_RENEW_USERNAME,
    AUTO_RENEW_SETTING,
    EDIT_HARGA_MENU,
    EDIT_HARGA_INPUT,
    BROADCAST_MENU,
    BROADCAST_INPUT,
    STOCK_MENU,
    STOCK_INPUT_ADD,
    STOCK_INPUT_REMOVE,
    STOCK_INPUT_SET
) = range(30)

# ==========================================
# KONFIGURASI HARGA & DATABASE
# ==========================================
DB_PATH = "/etc/conf/bot.db"

# ==========================================
# KONFIGURASI VOUCHER
# ==========================================
VOUCHER_TYPES = {
    'saldo': '💰 Saldo',
    'ssh': '🚀 SSH Account',
    'vmess': '📡 VMess Account',
    'vless': '📡 VLess Account',
    'trojan': '🛡️ Trojan Account'
}

# ==========================================
# KONFIGURASI LOG
# ==========================================
LOG_FILE = "/etc/conf/log.json"

def init_log_file():
    """Inisialisasi file log jika belum ada"""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            json.dump([], f)

# ==========================================
# DATABASE USER UNTUK BROADCAST
# ==========================================
def init_user_db():
    """Inisialisasi database user untuk broadcast"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS bot_users
                     (user_id INTEGER PRIMARY KEY,
                      username TEXT,
                      first_name TEXT,
                      last_name TEXT,
                      first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.commit()
        conn.close()
        print("✅ Database user untuk broadcast initialized")
        return True
    except Exception as e:
        print(f"❌ Gagal init user database: {e}")
        return False

def register_user(user_id, username, first_name, last_name):
    """Registrasi user ke database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Cek apakah tabel ada
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_users'")
        if not c.fetchone():
            c.execute('''CREATE TABLE IF NOT EXISTS bot_users
                         (user_id INTEGER PRIMARY KEY,
                          username TEXT,
                          first_name TEXT,
                          last_name TEXT,
                          first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('''INSERT OR REPLACE INTO bot_users 
                     (user_id, username, first_name, last_name, last_seen)
                     VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                  (user_id, username or "", first_name or "", last_name or ""))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Gagal register user {user_id}: {e}")
        return False

def get_all_users():
    """Ambil semua user yang pernah mengakses bot"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_users'")
        if not c.fetchone():
            conn.close()
            return []
        
        c.execute("SELECT user_id, username, first_name FROM bot_users ORDER BY last_seen DESC")
        users = c.fetchall()
        conn.close()
        return users
    except Exception as e:
        print(f"❌ Gagal get all users: {e}")
        return []

def get_user_count():
    """Hitung jumlah user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_users'")
        if not c.fetchone():
            conn.close()
            return 0
        
        c.execute("SELECT COUNT(*) FROM bot_users")
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"❌ Gagal get user count: {e}")
        return 0

# ==========================================
# FUNGSI SENSOR USERNAME
# ==========================================
def sensor_username(username, visible_chars=2):
    """Sensor username: Aw******"""
    if not username or len(username) <= visible_chars:
        return username
    
    prefix = username[:visible_chars]
    return prefix + "*" * (len(username) - visible_chars)

def sensor_nama(nama, visible_chars=2):
    """Sensor nama: St***"""
    if not nama or len(nama) <= visible_chars:
        return nama
    
    prefix = nama[:visible_chars]
    return prefix + "*" * (len(nama) - visible_chars)

def sensor_username_minimal(username, visible_chars=5):
    """Sensor username minimal: Setiaxxxxx"""
    if not username or len(username) <= visible_chars:
        return username
    
    prefix = username[:visible_chars]
    return prefix + "x" * (len(username) - visible_chars)

def sensor_transaksi_id(transaksi_id, prefix_chars=4, suffix_chars=4):
    """Sensor transaction ID: TRX1****2230"""
    if not transaksi_id or len(transaksi_id) <= (prefix_chars + suffix_chars):
        return transaksi_id
    
    prefix = transaksi_id[:prefix_chars]
    suffix = transaksi_id[-suffix_chars:]
    middle = "*" * (len(transaksi_id) - prefix_chars - suffix_chars)
    
    return f"{prefix}{middle}{suffix}"

def get_active_auto_renew(user_id):
    """Ambil daftar akun yang auto renew aktif"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT protocol, account_username, days_before 
                 FROM auto_renew_settings 
                 WHERE user_id = ? AND is_active = 1
                 ORDER BY protocol''', (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def update_harga_in_config(protocol, harga_baru):
    """Update harga di file config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if 'prices' not in config:
            config['prices'] = {}
        
        config['prices'][protocol] = harga_baru
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        global PRICES
        PRICES[protocol] = harga_baru
        
        return True, f"Harga {protocol.upper()} berhasil diupdate menjadi Rp {harga_baru:,}"
    except Exception as e:
        return False, f"Error: {str(e)}"

# ==========================================
# FUNGSI DETEKSI REGION (IPINFO.IO)
# ==========================================
def get_server_region():
    """Deteksi region server menggunakan ipinfo.io"""
    try:
        result = subprocess.run(['curl', '-s', 'https://ipinfo.io/json'], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            country = data.get('country', 'Unknown')
            city = data.get('city', 'Unknown')
            
            country_map = {
                'ID': '🇮🇩 ID',
                'SG': '🇸🇬 SG',
                'MY': '🇲🇾 Malaysia',
                'US': '🇺🇸 United States',
                'JP': '🇯🇵 Japan',
                'DE': '🇩🇪 Germany',
                'NL': '🇳🇱 Netherlands',
                'GB': '🇬🇧 United Kingdom',
                'FR': '🇫🇷 France',
                'AU': '🇦🇺 Australia',
                'CA': '🇨🇦 Canada',
                'IN': '🇮🇳 India',
                'KR': '🇰🇷 South Korea',
                'BR': '🇧🇷 Brazil',
                'RU': '🇷🇺 Russia',
                'IT': '🇮🇹 Italy',
                'ES': '🇪🇸 Spain',
                'MX': '🇲🇽 Mexico',
                'ZA': '🇿🇦 South Africa',
            }
            
            country_name = country_map.get(country, f"🌍 {country}")
            
            if city and city != 'Unknown':
                return f"{country_name} ({city})"
            return country_name
    except Exception as e:
        print(f"❌ Gagal deteksi region: {e}")
    
    try:
        with open('/etc/region.conf', 'r') as f:
            return f.readline().strip()
    except:
        pass
    
    return "🇸🇬 Singapore (Default)"

# ==========================================
# FUNGSI MANAJEMEN STOK
# ==========================================
def init_stock_db():
    """Inisialisasi database stok"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS stock_settings
                 (id INTEGER PRIMARY KEY CHECK (id = 1),
                  max_stock INTEGER DEFAULT 100,
                  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''INSERT OR IGNORE INTO stock_settings (id, max_stock) VALUES (1, 100)''')
    
    conn.commit()
    conn.close()
    print("✅ Database stok initialized")

def update_max_stock(new_max_stock):
    """Update maksimal stok"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE stock_settings SET max_stock = ?, last_updated = CURRENT_TIMESTAMP
                 WHERE id = 1''', (new_max_stock,))
    conn.commit()
    conn.close()

def get_max_stock():
    """Ambil maksimal stok dari database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT max_stock FROM stock_settings WHERE id = 1''')
    result = c.fetchone()
    conn.close()
    return result[0] if result else 100

def count_all_accounts():
    """Hitung total semua akun yang ada di sistem"""
    total = 0
    
    # Hitung SSH accounts dari /etc/passwd
    try:
        result = subprocess.run(['awk', '-F:', '$3 >= 1000 && $1 != "nobody" {print $1}', '/etc/passwd'], 
                               capture_output=True, text=True)
        ssh_users = result.stdout.strip().split('\n')
        total += len([u for u in ssh_users if u])
    except:
        pass
    
    # Hitung XRAY accounts dari config.json
    xray_config = "/etc/xray/config.json"
    if os.path.exists(xray_config):
        try:
            with open(xray_config, 'r') as f:
                content = f.read()
                total += content.count('###')  # vmess
                total += content.count('#&')   # vless
                total += content.count('#!')   # trojan
        except:
            pass
    
    return total

def get_global_stock_info():
    """Ambil info stok global dengan hitung akun yang ada"""
    total_accounts = count_all_accounts()
    max_stock = get_max_stock()
    
    return {
        'current': total_accounts,
        'max': max_stock,
        'available': max_stock - total_accounts
    }
    
def check_stock_available():
    """Cek apakah stok masih tersedia"""
    stock_info = get_global_stock_info()
    if stock_info['available'] <= 0:
        return False, f"❌ <b>STOK AKUN HABIS TUAN</b>\n\n📦 Stok tersedia: {stock_info['available']}\n\nSilakan hubungi @WaanSuka_Turu untuk menambah stok."
    return True, f"✅ Stok tersedia: {stock_info['available']}"
    
# ==========================================
# BROADCAST FUNCTIONS
# ==========================================
async def broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu broadcast - hanya untuk owner"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != OWNER_ID:
        await query.edit_message_text("❌ Hanya owner yang bisa akses fitur ini!")
        return VOUCHER_MENU
    
    user_count = get_user_count()
    
    text = (
        f"📢 <b>BROADCAST MESSAGE</b>\n\n"
        f"👥 Total user terdaftar: <b>{user_count}</b> user\n\n"
        f"Pilih tipe broadcast:\n"
        f"• <b>Text Message</b> - Kirim pesan teks\n"
        f"• <b>Photo + Caption</b> - Kirim foto dengan caption\n\n"
        f"Ketik /broadcast_text untuk broadcast text\n"
        f"Ketik /broadcast_photo untuk broadcast foto"
    )
    
    keyboard = [
        [InlineKeyboardButton("📝 Broadcast Text", callback_data='broadcast_text')],
        [InlineKeyboardButton("🖼️ Broadcast Photo", callback_data='broadcast_photo')],
        [InlineKeyboardButton("📊 Lihat Daftar User", callback_data='broadcast_list')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='voucher_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
    return BROADCAST_MENU

async def broadcast_text_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mulai broadcast text"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != OWNER_ID:
        await query.edit_message_text("❌ Hanya owner yang bisa akses fitur ini!")
        return VOUCHER_MENU
    
    await query.edit_message_text(
        "📝 <b>BROADCAST TEXT</b>\n\n"
        "Kirimkan pesan yang ingin di-broadcast ke semua user.\n\n"
        "Pesan bisa menggunakan <b>HTML formatting</b>.\n"
        "Ketik <code>/batal</code> untuk membatalkan.",
        parse_mode='HTML'
    )
    
    return BROADCAST_INPUT

async def broadcast_photo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mulai broadcast photo"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != OWNER_ID:
        await query.edit_message_text("❌ Hanya owner yang bisa akses fitur ini!")
        return VOUCHER_MENU
    
    await query.edit_message_text(
        "🖼️ <b>BROADCAST PHOTO</b>\n\n"
        "Kirimkan <b>FOTO</b> yang ingin di-broadcast ke semua user.\n"
        "Foto bisa disertai <b>caption</b> (HTML formatting).\n\n"
        "Ketik <code>/batal</code> untuk membatalkan.",
        parse_mode='HTML'
    )
    
    return BROADCAST_INPUT

async def broadcast_process_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proses broadcast text"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya owner yang bisa akses fitur ini!")
        return ConversationHandler.END
    
    message_text = update.message.text
    users = get_all_users()
    
    if not users:
        await update.message.reply_text("❌ Belum ada user yang terdaftar!")
        return ConversationHandler.END
    
    progress_msg = await update.message.reply_text(
        f"⏱️ Memulai broadcast ke {len(users)} user...\n"
        f"📝 Pesan: {message_text[:50]}..."
    )
    
    success_count = 0
    fail_count = 0
    failed_users = []
    
    for i, (user_id, username, first_name) in enumerate(users):
        try:
            personalized_msg = message_text.replace("{name}", first_name or "User")
            personalized_msg = personalized_msg.replace("{username}", username or "User")
            
            await context.bot.send_message(
                chat_id=user_id,
                text=personalized_msg,
                parse_mode='HTML'
            )
            success_count += 1
            
            if (i + 1) % 10 == 0:
                await progress_msg.edit_text(
                    f"⏱️ Broadcast berjalan...\n"
                    f"✅ Berhasil: {success_count}\n"
                    f"❌ Gagal: {fail_count}\n"
                    f"📊 Progres: {i+1}/{len(users)}"
                )
            
            await asyncio.sleep(0.05)
            
        except Exception as e:
            fail_count += 1
            failed_users.append(user_id)
            print(f"❌ Gagal kirim ke {user_id}: {e}")
    
    report = (
        f"✅ <b>BROADCAST SELESAI!</b>\n\n"
        f"📊 Total user: {len(users)}\n"
        f"✅ Berhasil: {success_count}\n"
        f"❌ Gagal: {fail_count}\n\n"
    )
    
    if failed_users and len(failed_users) <= 10:
        report += f"❌ Gagal ke user: {', '.join(map(str, failed_users))}"
    elif failed_users:
        report += f"❌ Gagal ke {len(failed_users)} user (tidak ditampilkan)"
    
    await progress_msg.edit_text(report, parse_mode='HTML')
    
    try:
        channel_msg = (
            f"📢 <b>BROADCAST TERKIRIM</b>\n\n"
            f"👤 Owner: @{update.effective_user.username}\n"
            f"📊 Total user: {len(users)}\n"
            f"✅ Berhasil: {success_count}\n"
            f"❌ Gagal: {fail_count}\n"
            f"📝 Pesan: {message_text[:100]}..."
        )
        await send_to_channel(context, channel_msg)
    except:
        pass
    
    context.user_data.clear()
    return PROTOKOL

async def broadcast_process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proses broadcast photo"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya owner yang bisa akses fitur ini!")
        return ConversationHandler.END
    
    if not update.message.photo:
        await update.message.reply_text("❌ Kirimkan FOTO untuk broadcast!")
        return BROADCAST_INPUT
    
    photo = update.message.photo[-1]
    caption = update.message.caption or ""
    users = get_all_users()
    
    if not users:
        await update.message.reply_text("❌ Belum ada user yang terdaftar!")
        return ConversationHandler.END
    
    progress_msg = await update.message.reply_text(
        f"⏱️ Memulai broadcast foto ke {len(users)} user...\n"
        f"📝 Caption: {caption[:50]}..."
    )
    
    success_count = 0
    fail_count = 0
    
    for i, (user_id, username, first_name) in enumerate(users):
        try:
            personalized_caption = caption.replace("{name}", first_name or "User")
            personalized_caption = personalized_caption.replace("{username}", username or "User")
            
            await context.bot.send_photo(
                chat_id=user_id,
                photo=photo.file_id,
                caption=personalized_caption,
                parse_mode='HTML'
            )
            success_count += 1
            
            if (i + 1) % 10 == 0:
                await progress_msg.edit_text(
                    f"⏱️ Broadcast berjalan...\n"
                    f"✅ Berhasil: {success_count}\n"
                    f"❌ Gagal: {fail_count}\n"
                    f"📊 Progres: {i+1}/{len(users)}"
                )
            
            await asyncio.sleep(0.05)
            
        except Exception as e:
            fail_count += 1
            print(f"❌ Gagal kirim ke {user_id}: {e}")
    
    report = (
        f"✅ <b>BROADCAST FOTO SELESAI!</b>\n\n"
        f"📊 Total user: {len(users)}\n"
        f"✅ Berhasil: {success_count}\n"
        f"❌ Gagal: {fail_count}"
    )
    
    await progress_msg.edit_text(report, parse_mode='HTML')
    
    try:
        channel_msg = (
            f"📢 <b>BROADCAST FOTO TERKIRIM</b>\n\n"
            f"👤 Owner: @{update.effective_user.username}\n"
            f"📊 Total user: {len(users)}\n"
            f"✅ Berhasil: {success_count}\n"
            f"❌ Gagal: {fail_count}"
        )
        await send_to_channel(context, channel_msg)
    except:
        pass
    
    context.user_data.clear()
    return PROTOKOL

async def broadcast_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lihat daftar user"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != OWNER_ID:
        await query.edit_message_text("❌ Hanya owner yang bisa akses fitur ini!")
        return VOUCHER_MENU
    
    users = get_all_users()
    
    if not users:
        await query.edit_message_text("📭 Belum ada user yang terdaftar.")
        return BROADCAST_MENU
    
    text = "📊 <b>DAFTAR USER TERDAFTAR</b>\n\n"
    text += f"Total: {len(users)} user\n\n"
    
    for i, (user_id, username, first_name) in enumerate(users[:20]):
        display_name = first_name[:15] if first_name else "Unknown"
        if username:
            text += f"{i+1}. @{username[:15]} ({display_name})\n   🆔 <code>{user_id}</code>\n"
        else:
            text += f"{i+1}. {display_name}\n   🆔 <code>{user_id}</code>\n"
    
    if len(users) > 20:
        text += f"\n... dan {len(users) - 20} user lainnya"
    
    keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data='broadcast_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
    return BROADCAST_MENU

# ==========================================
# EDIT HARGA MENU
# ==========================================
async def edit_harga_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu edit harga - hanya untuk owner"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != OWNER_ID:
        await query.edit_message_text("❌ Hanya owner yang bisa akses fitur ini!")
        return VOUCHER_MENU
    
    text = "💰 <b>EDIT HARGA PER PROTOKOL</b>\n\n"
    text += "Harga saat ini:\n"
    text += f"🚀 SSH      : Rp {PRICES['ssh']:,}/hari\n"
    text += f"📡 VMess    : Rp {PRICES['vmess']:,}/hari\n"
    text += f"📡 VLess    : Rp {PRICES['vless']:,}/hari\n"
    text += f"🛡️ Trojan   : Rp {PRICES['trojan']:,}/hari\n\n"
    text += "Pilih protokol yang ingin diedit:"
    
    keyboard = [
        [
            InlineKeyboardButton("🚀 SSH", callback_data='edit_harga_ssh'),
            InlineKeyboardButton("📡 VMess", callback_data='edit_harga_vmess'),
        ],
        [
            InlineKeyboardButton("📡 VLess", callback_data='edit_harga_vless'),
            InlineKeyboardButton("🛡️ Trojan", callback_data='edit_harga_trojan'),
        ],
        [InlineKeyboardButton("🔙 Kembali", callback_data='voucher_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
    return EDIT_HARGA_MENU

async def edit_harga_pilih_protokol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pilih protokol untuk edit harga"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != OWNER_ID:
        await query.edit_message_text("❌ Hanya owner yang bisa akses fitur ini!")
        return VOUCHER_MENU
    
    protocol = query.data.replace('edit_harga_', '')
    context.user_data['edit_harga_protocol'] = protocol
    
    proto_names = {
        'ssh': '🚀 SSH',
        'vmess': '📡 VMess',
        'vless': '📡 VLess',
        'trojan': '🛡️ Trojan'
    }
    
    harga_sekarang = PRICES.get(protocol, 0)
    
    text = (
        f"💰 <b>EDIT HARGA {proto_names[protocol]}</b>\n\n"
        f"Harga saat ini: Rp {harga_sekarang:,}/hari\n\n"
        f"📝 Masukkan harga baru (dalam Rupiah):\n"
        f"Contoh: <code>1000</code>\n\n"
        f"Ketik /batal untuk membatalkan."
    )
    
    keyboard = [[InlineKeyboardButton("❌ Batal", callback_data='edit_harga_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
    return EDIT_HARGA_INPUT

async def edit_harga_proses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proses input harga baru"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Hanya owner yang bisa akses fitur ini!")
        return ConversationHandler.END
    
    text = update.message.text.strip()
    protocol = context.user_data.get('edit_harga_protocol')
    
    if not protocol:
        await update.message.reply_text("❌ Sesi expired. Silakan mulai ulang.")
        return PROTOKOL
    
    try:
        harga_baru = int(text)
        if harga_baru < 100:
            await update.message.reply_text("❌ Harga minimal Rp 100")
            return EDIT_HARGA_INPUT
        if harga_baru > 10000:
            await update.message.reply_text("❌ Harga maksimal Rp 10.000")
            return EDIT_HARGA_INPUT
        
        success, message = update_harga_in_config(protocol, harga_baru)
        
        if success:
            try:
                channel_msg = (
                    f"💰 <b>HARGA DIUPDATE</b>\n\n"
                    f"👤 Owner: @{update.effective_user.username}\n"
                    f"📦 Protokol: {protocol.upper()}\n"
                    f"💵 Harga baru: Rp {harga_baru:,}/hari"
                )
                await send_to_channel(context, channel_msg)
            except:
                pass
            
            await update.message.reply_text(
                f"✅ <b>HARGA BERHASIL DIUPDATE</b>\n\n"
                f"📦 Protokol: {protocol.upper()}\n"
                f"💵 Harga baru: Rp {harga_baru:,}/hari",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(f"❌ Gagal update harga: {message}")
        
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka yang valid!")
        return EDIT_HARGA_INPUT
    
    await edit_harga_menu(update, context)
    return EDIT_HARGA_MENU

async def send_to_channel(context: ContextTypes.DEFAULT_TYPE, message: str, photo_path=None):
    """Kirim pesan ke channel"""
    try:
        if not CHANNEL_ID or CHANNEL_ID == 0:
            print("⚠️ CHANNEL_ID tidak valid, skip notifikasi")
            return False
        
        if isinstance(CHANNEL_ID, str) and CHANNEL_ID.startswith('@'):
            chat_id = CHANNEL_ID
        else:
            chat_id = int(CHANNEL_ID)
        
        if photo_path and os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=message,
                    parse_mode='HTML'
                )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
        print("✅ Berhasil kirim ke channel")
        return True
        
    except Exception as e:
        print(f"❌ Gagal kirim ke channel: {e}")
        return False
        
# ==========================================
# FUNGSI SAVE ACCOUNT LOG
# ==========================================
def save_account_log(update, username, protocol, days, quota, iplimit, 
                     expired_date, password=None, uuid=None, 
                     result_data=None, status="success", notes="", action="create"):
    """Simpan log pembuatan/renew akun dan kirim ke channel"""
    
    user_id = update.effective_user.id
    user_username = update.effective_user.username or "Tidak ada username"
    user_first = update.effective_user.first_name or ""
    user_last = update.effective_user.last_name or ""
    
    try:
        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)
    except:
        logs = []
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "user": {
            "id": user_id,
            "username": user_username,
            "first_name": user_first,
            "last_name": user_last,
            "full_name": f"{user_first} {user_last}".strip()
        },
        "account": {
            "username": username,
            "protocol": protocol,
            "days": days,
            "quota": quota,
            "iplimit": iplimit,
            "expired_date": expired_date,
        },
        "status": status,
        "notes": notes
    }
    
    if protocol == 'ssh':
        log_entry["account"]["password"] = password
    elif protocol in ['vmess', 'vless']:
        log_entry["account"]["uuid"] = uuid or (result_data.get('uuid') if result_data else None)
    elif protocol == 'trojan':
        log_entry["account"]["password"] = password or (result_data.get('password') if result_data else None)
    
    if result_data:
        log_entry["account"]["domain"] = result_data.get('domain')
        log_entry["account"]["expired_readable"] = result_data.get('expired_readable')
        if protocol in ['vmess', 'vless', 'trojan']:
            log_entry["account"]["links"] = {
                'tls': result_data.get('link_tls'),
                'http': result_data.get('link_http'),
                'grpc': result_data.get('link_grpc'),
                'ws': result_data.get('link_ws')
            }
    
    logs.append(log_entry)
    
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)
    
    if status == "success" and (action == "create" or action == "renew"):
        try:
            asyncio.create_task(send_log_to_channel(update, log_entry, action.upper()))
            print(f"📤 Task kirim ke channel dibuat untuk {action}")
        except Exception as e:
            print(f"❌ Gagal membuat task kirim ke channel: {e}")
    
    return log_entry

async def send_log_to_channel(update, log_entry, action):
    """Kirim log ke channel"""
    try:
        if hasattr(update, 'get_bot'):
            bot = update.get_bot()
        elif hasattr(update, 'bot'):
            bot = update.bot
        elif update.callback_query:
            bot = update.callback_query.get_bot()
        elif update.message:
            bot = update.message.get_bot()
        else:
            print("❌ Tidak bisa mendapatkan bot dari update")
            return
        
        user_info = log_entry['user']
        account_info = log_entry['account']
        
        raw_username = user_info['username']
        if raw_username != "Tidak ada username":
            clean_username = raw_username.replace('@', '')
            sensor_username = sensor_username_minimal(clean_username, 5)
            user_display = f"@{sensor_username}"
        else:
            user_display = "User"
        
        transaksi_id = f"TRX{user_info['id']}{datetime.now().strftime('%Y%m%d%H%M%S')}"
        sensor_trx = sensor_transaksi_id(transaksi_id, 4, 4)
        
        icons = {
            'ssh': '🔰',
            'vmess': '📡',
            'vless': '📡',
            'trojan': '🛡️'
        }
        icon = icons.get(account_info['protocol'], '📦')
        
        waktu = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        message = (
            f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            f"┃     📢 TRANSAKSI BARU     ┃\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ Waktu: {waktu}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Pembeli: {user_display}\n"
            f"🆔 TRX ID: <code>{sensor_trx}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 DETAIL TRANSAKSI\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Aksi: {action}\n"
            f"{icon} Akun: {account_info['protocol'].upper()}\n"
            f"📅 Masa Aktif: {account_info['days']} hari\n"
            f"⏰ Exp: {account_info['expired_date']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 BOT AUTO ORDER\n"
            f"🤖 @autobuy_produk_bot\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        channel_id = CHANNEL_ID
        if not channel_id or channel_id == 0:
            print("⚠️ CHANNEL_ID tidak valid, skip notifikasi channel")
            return
        
        if isinstance(channel_id, str):
            try:
                channel_id = int(channel_id)
            except ValueError:
                pass
        
        await bot.send_message(
            chat_id=channel_id,
            text=message,
            parse_mode='HTML'
        )
        print("✅ Berhasil kirim ke channel")
        
    except Exception as e:
        print(f"❌ Error di send_log_to_channel: {e}")

# ==========================================
# LOGGING
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# FUNGSI DATABASE SALDO
# ==========================================
def init_db():
    """Inisialisasi database saldo"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS saldo
                 (user_id INTEGER PRIMARY KEY, 
                  balance INTEGER DEFAULT 0,
                  total_topup INTEGER DEFAULT 0,
                  last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS transaksi
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  type TEXT,
                  amount INTEGER,
                  description TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_balance(user_id):
    """Ambil saldo user"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance FROM saldo WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def update_balance(user_id, amount, description):
    """Update saldo user"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT balance FROM saldo WHERE user_id = ?", (user_id,))
    if c.fetchone():
        c.execute("UPDATE saldo SET balance = balance + ?, last_update = CURRENT_TIMESTAMP WHERE user_id = ?", 
                  (amount, user_id))
    else:
        c.execute("INSERT INTO saldo (user_id, balance) VALUES (?, ?)", 
                  (user_id, amount if amount > 0 else 0))
    
    c.execute("INSERT INTO transaksi (user_id, type, amount, description) VALUES (?, ?, ?, ?)",
              (user_id, 'credit' if amount > 0 else 'debit', abs(amount), description))
    
    conn.commit()
    conn.close()

def calculate_price(protocol, days):
    """Hitung total harga"""
    base_price = PRICES.get(protocol, 500)
    return base_price * days

# ==========================================
# FUNGSI DATABASE VOUCHER
# ==========================================
def init_voucher_db():
    """Inisialisasi database voucher"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS vouchers
                 (code TEXT PRIMARY KEY,
                  type TEXT,
                  value INTEGER,
                  days INTEGER DEFAULT 0,
                  quota INTEGER DEFAULT 250,
                  iplimit INTEGER DEFAULT 4,
                  max_uses INTEGER DEFAULT 1,
                  used_count INTEGER DEFAULT 0,
                  created_by INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  expires_at TIMESTAMP,
                  is_active INTEGER DEFAULT 1)''')
    
    c.execute("PRAGMA table_info(vouchers)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'min_balance' not in columns:
        c.execute("ALTER TABLE vouchers ADD COLUMN min_balance INTEGER DEFAULT 0")
        print("✅ Kolom min_balance berhasil ditambahkan")
    
    c.execute('''CREATE TABLE IF NOT EXISTS voucher_uses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  code TEXT,
                  user_id INTEGER,
                  used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(code) REFERENCES vouchers(code))''')
    
    conn.commit()
    conn.close()

def generate_voucher_code(length=8):
    """Generate kode voucher unik"""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choice(chars) for _ in range(length))
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT code FROM vouchers WHERE code = ?", (code,))
        exists = c.fetchone()
        conn.close()
        if not exists:
            return code

def create_voucher(created_by, voucher_type, value, days=0, 
                   max_users=1, expires_days=30, min_balance=0):
    """Buat voucher baru"""
    
    code = generate_voucher_code()
    expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("PRAGMA table_info(vouchers)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'min_balance' in columns:
        c.execute('''INSERT INTO vouchers 
                     (code, type, value, days, max_uses, used_count, created_by, expires_at, min_balance)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (code, voucher_type, value, days, max_users, 0, created_by, expires_at, min_balance))
    else:
        c.execute('''INSERT INTO vouchers 
                     (code, type, value, days, max_uses, used_count, created_by, expires_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (code, voucher_type, value, days, max_users, 0, created_by, expires_at))
    
    conn.commit()
    conn.close()
    
    return code

def use_voucher(code, user_id):
    """Gunakan voucher dengan cek expired"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("PRAGMA table_info(vouchers)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'min_balance' in columns:
        c.execute('''SELECT type, value, days, max_uses, used_count, is_active, 
                     expires_at, min_balance
                     FROM vouchers WHERE code = ?''', (code,))
        result = c.fetchone()
        if result:
            v_type, v_value, v_days, max_uses, used_count, is_active, expires_at, min_balance = result
    else:
        c.execute('''SELECT type, value, days, max_uses, used_count, is_active, 
                     expires_at
                     FROM vouchers WHERE code = ?''', (code,))
        result = c.fetchone()
        if result:
            v_type, v_value, v_days, max_uses, used_count, is_active, expires_at = result
            min_balance = 0
    
    if not result:
        conn.close()
        return {'success': False, 'message': '❌ Voucher tidak ditemukan'}
    
    if not is_active:
        conn.close()
        return {'success': False, 'message': '❌ Voucher sudah tidak aktif'}
    
    now = datetime.now()
    if expires_at and now > datetime.fromisoformat(expires_at):
        c.execute("UPDATE vouchers SET is_active = 0 WHERE code = ?", (code,))
        conn.commit()
        conn.close()
        return {'success': False, 'message': '❌ Voucher sudah expired'}
    
    if used_count >= max_uses:
        conn.close()
        return {'success': False, 'message': f'❌ Voucher sudah mencapai maksimal {max_uses} user'}
    
    c.execute('''SELECT COUNT(*) FROM voucher_uses 
                 WHERE code = ? AND user_id = ?''', (code, user_id))
    user_uses = c.fetchone()[0]
    if user_uses > 0:
        conn.close()
        return {'success': False, 'message': '❌ Kamu sudah pernah menggunakan voucher ini'}
    
    if v_type == 'saldo' and min_balance > 0:
        current_balance = get_balance(user_id)
        if current_balance < min_balance:
            conn.close()
            return {'success': False, 'message': f'❌ Minimal saldo Rp {min_balance:,} untuk redeem voucher ini'}
    
    c.execute("UPDATE vouchers SET used_count = used_count + 1 WHERE code = ?", (code,))
    c.execute("INSERT INTO voucher_uses (code, user_id) VALUES (?, ?)", (code, user_id))
    
    conn.commit()
    conn.close()
    
    return {
        'success': True,
        'type': v_type,
        'value': v_value,
        'days': v_days
    }
    
# ==========================================
# FUNGSI DATABASE AUTO RENEW
# ==========================================
def init_auto_renew_db():
    """Inisialisasi database auto renew"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS auto_renew_settings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  protocol TEXT,
                  account_username TEXT,
                  is_active INTEGER DEFAULT 0,
                  days_before INTEGER DEFAULT 4,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(user_id, protocol, account_username))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS auto_renew_notifications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  protocol TEXT,
                  account_username TEXT,
                  days_before INTEGER,
                  notification_date DATE,
                  sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(user_id, protocol, account_username, days_before))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS auto_renew_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  protocol TEXT,
                  account_username TEXT,
                  action TEXT,
                  amount INTEGER,
                  status TEXT,
                  message TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
    print("✅ Database auto renew initialized")

def get_auto_renew_status(user_id, protocol, username):
    """Cek status auto renew untuk akun tertentu"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT is_active, days_before FROM auto_renew_settings 
                 WHERE user_id = ? AND protocol = ? AND account_username = ?''',
              (user_id, protocol, username))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {"is_active": bool(result[0]), "days_before": result[1]}
    return {"is_active": False, "days_before": 4}

def set_auto_renew(user_id, protocol, username, is_active, days_before=4):
    """Set status auto renew untuk akun"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT OR REPLACE INTO auto_renew_settings 
                 (user_id, protocol, account_username, is_active, days_before, updated_at)
                 VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
              (user_id, protocol, username, 1 if is_active else 0, days_before))
    conn.commit()
    conn.close()
    
    action = "diaktifkan" if is_active else "dinonaktifkan"
    print(f"📝 Auto renew {action} untuk {username} ({protocol})")

# ==========================================
# DATABASE TRIAL
# ==========================================
def init_trial_db():
    """Inisialisasi database trial"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS trial_accounts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  protocol TEXT,
                  password TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  expires_at TIMESTAMP,
                  is_active INTEGER DEFAULT 1)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS trial_usage
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  trial_date DATE DEFAULT CURRENT_DATE,
                  use_count INTEGER DEFAULT 0,
                  UNIQUE(user_id, trial_date))''')
    conn.commit()
    conn.close()

def can_use_trial(user_id):
    """Cek apakah user bisa trial hari ini"""
    today = datetime.now().date().isoformat()
    max_per_day = TRIAL_CONFIG['max_per_day']
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT use_count FROM trial_usage 
                 WHERE user_id = ? AND trial_date = ?''',
              (user_id, today))
    result = c.fetchone()
    
    if not result:
        c.execute('''INSERT INTO trial_usage (user_id, trial_date, use_count)
                     VALUES (?, ?, 1)''', (user_id, today))
        conn.commit()
        conn.close()
        return True, f"Boleh trial {max_per_day - 1}x lagi hari ini"
    
    use_count = result[0]
    if use_count >= max_per_day:
        conn.close()
        return False, f"Sudah mencapai maksimal {max_per_day}x trial hari ini"
    
    c.execute('''UPDATE trial_usage SET use_count = use_count + 1
                 WHERE user_id = ? AND trial_date = ?''',
              (user_id, today))
    conn.commit()
    conn.close()
    
    remaining = max_per_day - (use_count + 1)
    return True, f"Boleh trial {remaining}x lagi hari ini"

def generate_random_username(protocol, length=4):
    """Generate username random: trial_ssh_a1b2"""
    chars = string.ascii_lowercase + string.digits
    random_part = ''.join(random.choice(chars) for _ in range(length))
    return f"{TRIAL_CONFIG['username_prefix']}_{protocol}_{random_part}"

def save_trial_account(username, protocol, password, hours=1):
    """Simpan akun trial ke database"""
    now = datetime.now()
    expires_at = (now + timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''DELETE FROM trial_accounts WHERE username = ?''', (username,))
    
    c.execute('''INSERT INTO trial_accounts (username, protocol, password, expires_at)
                 VALUES (?, ?, ?, ?)''', (username, protocol, password, expires_at))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Trial saved: {username} expires at {expires_at}")

async def get_trial_count_today(user_id):
    """Ambil jumlah trial user hari ini"""
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT use_count FROM trial_usage 
                 WHERE user_id = ? AND trial_date = ?''',
              (user_id, today))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

# ==========================================
# FUNGSI HITUNG PENGUNJUNG
# ==========================================
def get_visitor_count():
    """Hitung jumlah pengunjung unik"""
    visitor_file = "/etc/conf/visitors.txt"
    if os.path.exists(visitor_file):
        with open(visitor_file, 'r') as f:
            count = int(f.read().strip())
    else:
        count = 0
        with open(visitor_file, 'w') as f:
            f.write("0")
    return count

def update_visitor_count():
    """Update jumlah pengunjung"""
    visitor_file = "/etc/conf/visitors.txt"
    count = get_visitor_count() + 1
    with open(visitor_file, 'w') as f:
        f.write(str(count))

# ==========================================
# FUNGSI VALIDASI
# ==========================================
def validate_username(username):
    return bool(re.match(r'^[a-zA-Z0-9_]+$', username))

def get_protocol_icon(protocol):
    icons = {
        'ssh': '🚀',
        'vmess': '📡',
        'vless': '📡',
        'trojan': '🛡️'
    }
    return icons.get(protocol, '📦')

# ==========================================
# FUNGSI CALL SCRIPT
# ==========================================
async def call_script_async(script_path, args_list):
    """Jalankan script shell secara async"""
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
# FUNGSI RENEW DENGAN SCRIPT BASH
# ==========================================
async def renew_with_script(protocol, username, days, quota, iplimit):
    """Panggil script renew sesuai protokol"""
    
    script_path = RENEW_SCRIPTS.get(protocol)
    if not script_path or not os.path.exists(script_path):
        return {"status": "error", "message": f"Script renew {protocol} tidak ditemukan"}
    
    try:
        process = await asyncio.create_subprocess_exec(
            "bash", script_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        input_data = f"{username}\n{days}\n{quota}\n{iplimit}\n"
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_data.encode()), 
                timeout=30
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {"status": "error", "message": "Script timeout"}
        
        output = stdout.decode()
        json_pattern = r'(\{.*\})'
        match = re.search(json_pattern, output, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        else:
            return {"status": "error", "message": "Script tidak mengembalikan JSON"}
        
    except Exception as e:
        logging.error(f"Error renew {protocol}: {e}")
        return {"status": "error", "message": str(e)}

# ==========================================
# FUNGSI GET USER ACCOUNTS
# ==========================================
async def get_user_accounts(user_id):
    """Ambil semua akun yang dimiliki user"""
    accounts = []
    
    try:
        result = subprocess.run(['awk', '-F:', '$3 >= 1000 && $1 != "nobody" {print $1}', '/etc/passwd'], 
                               capture_output=True, text=True)
        ssh_users = result.stdout.strip().split('\n')
        
        for username in ssh_users:
            if username:
                try:
                    chage_output = subprocess.run(['chage', '-l', username], 
                                                 capture_output=True, text=True)
                    for line in chage_output.stdout.split('\n'):
                        if 'Account expires' in line:
                            exp_str = line.split(':')[1].strip()
                            if exp_str != 'never':
                                exp_date = datetime.strptime(exp_str, '%b %d, %Y')
                                accounts.append({
                                    'username': username,
                                    'protocol': 'ssh',
                                    'expired': exp_date.isoformat(),
                                    'expired_display': exp_date.strftime('%d/%m/%Y')
                                })
                            break
                except:
                    pass
    except:
        pass
    
    xray_config = "/etc/xray/config.json"
    if os.path.exists(xray_config):
        try:
            with open(xray_config, 'r') as f:
                lines = f.readlines()
            
            patterns = {
                '###': 'vmess',
                '#&': 'vless',
                '#!': 'trojan'
            }
            
            for pattern, protocol in patterns.items():
                for line in lines:
                    if pattern in line:
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            username = parts[1]
                            exp_str = parts[2]
                            try:
                                exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
                                accounts.append({
                                    'username': username,
                                    'protocol': protocol,
                                    'expired': exp_date.isoformat(),
                                    'expired_display': exp_date.strftime('%d/%m/%Y')
                                })
                            except:
                                pass
        except:
            pass
    
    return accounts

# ==========================================
# ERROR HANDLER
# ==========================================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    try:
        logger.error(f"Update {update} caused error {context.error}")
        import traceback
        traceback.print_exc()
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Terjadi kesalahan internal.\nSilakan coba lagi."
            )
    except:
        pass
        
# ==========================================
# FUNGSI PROSES CREATE AKUN
# ==========================================
async def process_create_account(update: Update, context: ContextTypes.DEFAULT_TYPE, skip_balance=False):
    """Proses pembuatan akun"""
    user_id = update.effective_user.id
    
    protocol = context.user_data.get('selected_protocol')
    username = context.user_data.get('username')
    password = context.user_data.get('password', None)
    days = context.user_data.get('days')
    quota = DEFAULT_QUOTA
    iplimit = DEFAULT_IP_LIMIT
    
    can_create, stock_msg = check_stock_available()
    if not can_create:
        await context.bot.send_message(
            chat_id=user_id,
            text=stock_msg,
            parse_mode='HTML'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    print("=" * 50)
    print("🔍 PROCESS CREATE ACCOUNT DIPANGGIL")
    print(f"🔍 User ID: {user_id}")
    print(f"🔍 Protocol: {protocol}")
    print(f"🔍 Username: {username}")
    print(f"🔍 Days: {days}")
    print(f"🔍 Skip Balance: {skip_balance}")
    print("=" * 50)
    
    if not protocol:
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ <b>ERROR</b>\n\nProtokol tidak ditemukan.",
            parse_mode='HTML'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    if not username:
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ <b>ERROR</b>\n\nUsername tidak valid.",
            parse_mode='HTML'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    if not days or days < 1 or days > 365:
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ <b>ERROR</b>\n\nJumlah hari tidak valid (1-365).",
            parse_mode='HTML'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    if protocol == 'ssh' and skip_balance and not password:
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(8))
        print(f"🔑 Generated password: {password}")
    
    script_path = SCRIPTS.get(protocol)
    if not script_path:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ <b>ERROR</b>\n\nScript untuk {protocol.upper()} tidak ditemukan.",
            parse_mode='HTML'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    if not os.path.exists(script_path):
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ <b>ERROR</b>\n\nFile script tidak ditemukan:\n<code>{script_path}</code>",
            parse_mode='HTML'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    total_price = 0
    
    if not skip_balance:
        total_price = calculate_price(protocol, days)
        current_balance = get_balance(user_id)
        
        if current_balance < total_price:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ <b>Saldo tidak mencukupi!</b>\n\n"
                     f"💰 Harga: Rp {total_price:,}\n"
                     f"💵 Saldo: Rp {current_balance:,}",
                parse_mode='HTML'
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        update_balance(user_id, -total_price, f"Beli akun {protocol} {days} hari")
    
    progress = await context.bot.send_message(
        chat_id=user_id,
        text=f"⏱️ Membuat akun {protocol.upper()}..."
    )
    
    if protocol == 'ssh':
        args_list = [username, password, str(quota), str(iplimit), str(days)]
    else:
        args_list = [username, str(days), str(quota), str(iplimit)]
    
    result = await call_script_async(script_path, args_list)
    
    await progress.delete()
    
    if result.get('status') == 'success':
        expired_date = result.get('expired_readable', 'N/A')
        try:
            exp_date = datetime.strptime(expired_date, '%d %b %Y').strftime('%Y-%m-%d')
        except:
            exp_date = expired_date
        
        save_account_log(
            update=update,
            username=username,
            protocol=protocol,
            days=days,
            quota=quota,
            iplimit=iplimit,
            expired_date=exp_date,
            password=password if protocol == 'ssh' else None,
            result_data=result,
            status="success",
            action="create"
        )
        
        if protocol == 'ssh':
            pesan = (
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  🚀 <b>SSH ACCOUNT</b>\n"
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
                f"🔹 SSH WS     : 80, 8080, 2086, 8880\n"
                f"🔹 SSL/TLS    : 443, 8443\n"
                f"🔹 SSH UDP    : 1-65535\n"
                f"🔹 DNS        : 53, 2222\n"
                f"🔹 BadVPN     : 7100, 7300\n\n"
                
                f"📦 <b>PAYLOAD</b>\n"
                f"──────────────────\n"
                f"<code>GET / HTTP/1.1[crlf]Host: [host][crlf]Upgrade: websocket[crlf][crlf]</code>\n\n"
                
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
        
        keyboard = [[InlineKeyboardButton("Thank You🥳", callback_data='buat_lagi')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text=pesan,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
    else:
        if not skip_balance:
            update_balance(user_id, total_price, f"Refund gagal buat {protocol}")
            refund_text = f"💰 Saldo dikembalikan: Rp {total_price:,}"
        else:
            refund_text = "💡 Akun tidak jadi dibuat."
        
        save_account_log(
            update=update,
            username=username,
            protocol=protocol,
            days=days,
            quota=quota,
            iplimit=iplimit,
            expired_date=None,
            status="failed",
            notes=result.get('message', 'Unknown error'),
            action="create"
        )
        
        error_msg = result.get('message', 'Unknown error')
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ <b>GAGAL</b>\n\n{error_msg}\n\n{refund_text}",
            parse_mode='HTML'
        )
    
    context.user_data.clear()
    return ConversationHandler.END

# ==========================================
# HANDLER START (DENGAN REGISTRASI USER & INFO REGION & STOK)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Tidak ada username"
    first_name = update.effective_user.first_name or "User"
    last_name = update.effective_user.last_name or ""
    
    register_user(user_id, username, first_name, last_name)
    
    if context.user_data:
        context.user_data.clear()
    
    if update.message:
        loading = await update.message.reply_text("🔁️ Memuat data.....")
    else:
        query = update.callback_query
        loading = await query.message.reply_text("🔁️ Memuat data.....")
    
    update_visitor_count()
    balance = get_balance(user_id)
    await loading.delete()
    
    # ========== AMBIL INFO REGION & STOK ==========
    region = get_server_region()
    stock_info = get_global_stock_info()
    
    if stock_info['available'] <= 5:
        stok_status = f"⚠️ Sisa {stock_info['available']} akun"
    elif stock_info['available'] <= 0:
        stok_status = "❌ HABIS"
    else:
        stok_status = f"{stock_info['available']}"
    
    welcome_text = (
		f"╔═══════════════════════════╗\n"
		f"║           ⚡ 𝗪𝗮𝗮𝗻𝗦𝘁𝗼𝗿𝗲 𝗩𝗣𝗡 𝗣𝗔𝗡𝗘𝗟 ⚡          ║\n"
        f"╚═══════════════════════════╝\n\n"
        
        f"┌──📝 𝗜𝗡𝗙𝗢𝗥𝗠𝗔𝗦𝗜 𝗔𝗞𝗨𝗡\n"
        f"│💳 Saldo Kamu: Rp {balance:,}\n"
        f"│👤 Nama: {first_name}\n"
        f"│🆔 ID: {user_id}\n"
        f"└──────────────────────────\n"
        
        f"┌──🚀 𝗜𝗡𝗙𝗢 𝗦𝗘𝗥𝗩𝗘𝗥\n"
        f"│🌐 Region: {region}\n"
        f"│📦 Stok Akun: {stok_status}\n"
        f"│👥 Pengunjung: {get_visitor_count()} orang\n"
        f"└──────────────────────────\n"
        
        f"┌──🛍️ 𝗛𝗔𝗥𝗚𝗔 𝗟𝗔𝗬𝗔𝗡𝗔𝗡\n"
        f"│🔰 Harian ( Rp{PRICES['ssh']} )\n"
        f"│🔰 Mingguan ( Rp{PRICES['ssh']*7:,} )\n"
        f"│🔰 Bulanan ( Rp{PRICES['ssh']*30:,} )\n"
        f"└──────────────────────────\n"
        f" Admin : @WaanSuka_Turu\n\n"
        
        f"Silakan pilih kategori di bawah:\n\n"
    )
    
    keyboard = [
	    [
            InlineKeyboardButton("🛍️ 𝗠𝗘𝗡𝗨 𝗩𝗣𝗡", callback_data='vpn_menu'),
        ],
        [
            InlineKeyboardButton("🧩 𝗩𝗢𝗨𝗖𝗛𝗘𝗥   ", callback_data='voucher_menu'),
            InlineKeyboardButton("🖥️ 𝗛𝗜𝗦𝗧𝗢𝗥𝗬 ", callback_data='cek_saldo'),
		],
        [
            InlineKeyboardButton("💳 𝗧𝗼𝗽𝗨𝗽 𝗦𝗮𝗹𝗱𝗼", callback_data='topup_saldo'),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            welcome_text,
            parse_mode=None,
            reply_markup=reply_markup
        )
    else:
        await query.message.reply_text(
            welcome_text,
            parse_mode=None,
            reply_markup=reply_markup
        )
        try:
            await query.message.delete()
        except:
            pass
    
    return PROTOKOL
	
# ==========================================
# HANDLER VPN MENU
# ==========================================
async def vpn_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """VPN MENU - Tampil 7 opsi"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Buat SSH", callback_data='proto_ssh'),
        InlineKeyboardButton("Buat VMess", callback_data='proto_vmess')],
        [InlineKeyboardButton("Buat VLess", callback_data='proto_vless'),
        InlineKeyboardButton("Buat Trojan", callback_data='proto_trojan')],
        [InlineKeyboardButton("Trial Menu", callback_data='trial_menu')],
        [InlineKeyboardButton("Perpanjang Manual", callback_data='renew_menu')],
        [InlineKeyboardButton("Perpanjang Otomatis", callback_data='auto_renew_menu')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='kembali_ke_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "    🛒 PROTOCOL VPN MENU 🛒\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
		"🔵Contact Suppprt @WaanSuka_Turu\n"
		"🟣Channel Update @wnstore_vip\n\n"
        "Pilih layanan yang diinginkan:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return PROTOKOL
    
# ==========================================
# SUB MENU LAINNYA
# ==========================================
async def sub_menu_lainnya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu Lainnya - berisi tombol-tombol yang dipindahkan"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🛠️ Otomatis Perpanjang", callback_data='auto_renew_menu')],
        [InlineKeyboardButton("🔄 Perpanjang Manual", callback_data='renew_menu')],
        [InlineKeyboardButton("📊 History / Cek Saldo", callback_data='cek_saldo')],
        [InlineKeyboardButton("🛍️ Voucher", callback_data='voucher_menu')],
        [InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data='kembali_ke_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📦 <b>MENU LAINNYA</b>\n\n"
        "Silakan pilih opsi di bawah:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return PROTOKOL

# ==========================================
# HANDLER AUTO RENEW
# ==========================================
async def auto_renew_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aktifkan auto renew dan kembali ke menu"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    username = context.user_data.get('auto_username')
    protocol = context.user_data.get('auto_protocol')
    
    if not username or not protocol:
        await query.edit_message_text("❌ Sesi expired. Silakan mulai ulang.")
        return PROTOKOL
    
    set_auto_renew(user_id, protocol, username, True)
    
    active_renews = get_active_auto_renew(user_id)
    
    active_text = "✅ <b>AUTO RENEW AKTIF:</b>\n"
    for p, u, d in active_renews:
        icon = get_protocol_icon(p)
        active_text += f"{icon} <code>{u}</code> ({p.upper()})\n"
    
    keyboard = [
        [
            InlineKeyboardButton("🚀 SSH", callback_data='auto_proto_ssh'),
            InlineKeyboardButton("🧩 VMess", callback_data='auto_proto_vmess'),
        ],
        [
            InlineKeyboardButton("⚡ VLess", callback_data='auto_proto_vless'),
            InlineKeyboardButton("🫟️ Trojan", callback_data='auto_proto_trojan'),
        ],
        [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data='vpn_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ <b>AUTO RENEW DIAKTIFKAN</b>\n\n"
        f"{active_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Pilih protokol untuk menambah akun lain:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return AUTO_RENEW_MENU

async def auto_renew_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Nonaktifkan auto renew dan kembali ke menu"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    username = context.user_data.get('auto_username')
    protocol = context.user_data.get('auto_protocol')
    
    if not username or not protocol:
        await query.edit_message_text("❌ Sesi expired. Silakan mulai ulang.")
        return PROTOKOL
    
    set_auto_renew(user_id, protocol, username, False)
    
    active_renews = get_active_auto_renew(user_id)
    
    if active_renews:
        active_text = "✅ <b>AUTO RENEW AKTIF:</b>\n"
        for p, u, d in active_renews:
            icon = get_protocol_icon(p)
            active_text += f"{icon} <code>{u}</code> ({p.upper()})\n"
    else:
        active_text = "📭 <b>Belum ada akun dengan auto renew aktif</b>"
    
    keyboard = [
        [
            InlineKeyboardButton("🚀 SSH", callback_data='auto_proto_ssh'),
            InlineKeyboardButton("📡 VMess", callback_data='auto_proto_vmess'),
        ],
        [
            InlineKeyboardButton("📡 VLess", callback_data='auto_proto_vless'),
            InlineKeyboardButton("🛡️ Trojan", callback_data='auto_proto_trojan'),
        ],
        [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data='vpn_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"❌ <b>AUTO RENEW DINONAKTIFKAN</b>\n\n"
        f"{active_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Pilih protokol untuk menambah akun lain:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return AUTO_RENEW_MENU

async def auto_renew_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu auto renew - tampilkan list aktif + pilih protokol"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    active_renews = get_active_auto_renew(user_id)
    
    active_text = ""
    if active_renews:
        active_text = "✅ <b>AUTO RENEW AKTIF:</b>\n"
        for protocol, username, days_before in active_renews:
            icon = get_protocol_icon(protocol)
            active_text += f"{icon} <code>{username}</code> ({protocol.upper()})\n"
        active_text += "\n"
    else:
        active_text = "📭 <b>Belum ada akun dengan auto renew aktif</b>\n\n"
    
    keyboard = [
        [
            InlineKeyboardButton("🚀 SSH", callback_data='auto_proto_ssh'),
            InlineKeyboardButton("📡 VMess", callback_data='auto_proto_vmess'),
        ],
        [
            InlineKeyboardButton("📡 VLess", callback_data='auto_proto_vless'),
            InlineKeyboardButton("🛡️ Trojan", callback_data='auto_proto_trojan'),
        ],
        [InlineKeyboardButton("🔙 Kembali", callback_data='vpn_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🔄 <b>AUTO RENEW AKUN</b>\n\n"
        f"{active_text}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Pilih protokol untuk menambah akun baru:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return AUTO_RENEW_MENU

async def auto_renew_proto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User pilih protokol, lalu minta username"""
    query = update.callback_query
    await query.answer()
    
    protocol = query.data.replace('auto_proto_', '')
    context.user_data['auto_protocol'] = protocol
    
    proto_names = {
        'ssh': '🚀 SSH',
        'vmess': '📡 VMess',
        'vless': '📡 VLess',
        'trojan': '🛡️ Trojan'
    }
    
    keyboard = [[InlineKeyboardButton("❌ Batal", callback_data='auto_renew_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🔄 <b>AUTO RENEW {proto_names[protocol]}</b>\n\n"
        f"📝 Silahkan masukkan <b>Username</b> akun {protocol.upper()}:\n"
        f"Contoh: <code>myname</code>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return AUTO_RENEW_USERNAME

async def auto_renew_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proses input username auto renew"""
    username = update.message.text.strip()
    protocol = context.user_data.get('auto_protocol')
    user_id = update.effective_user.id
    
    if not protocol:
        await update.message.reply_text("❌ Sesi expired. Silakan mulai ulang.")
        return PROTOKOL
    
    accounts = await get_user_accounts(user_id)
    user_accounts = [acc for acc in accounts if acc['protocol'] == protocol and acc['username'] == username]
    
    if not user_accounts:
        keyboard = [[InlineKeyboardButton("❌ Coba Lagi", callback_data='auto_renew_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"❌ Akun <code>{username}</code> ({protocol}) tidak ditemukan!",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return AUTO_RENEW_USERNAME
    
    context.user_data['auto_username'] = username
    
    status = get_auto_renew_status(user_id, protocol, username)
    
    keyboard = [
        [
            InlineKeyboardButton("✅ AKTIFKAN", callback_data='auto_renew_on'),
            InlineKeyboardButton("❌ NONAKTIFKAN", callback_data='auto_renew_off'),
        ],
        [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data='auto_renew_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status_text = "✅ AKTIF" if status['is_active'] else "❌ NONAKTIF"
    icon = get_protocol_icon(protocol)
    
    await update.message.reply_text(
        f"🔄 <b>PENGATURAN AUTO RENEW</b>\n\n"
        f"{icon} Akun: <code>{username}</code> ({protocol.upper()})\n"
        f"📊 Status: {status_text}\n\n"
        f"Pilih aksi:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return AUTO_RENEW_SETTING
    
# ==========================================
# HANDLER TRIAL
# ==========================================
async def trial_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu trial otomatis"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    used = await get_trial_count_today(user_id)
    max_trial = TRIAL_CONFIG['max_per_day']
    remaining = max_trial - used
    
    keyboard = []
    row = []
    for protocol in ['ssh', 'vmess', 'vless', 'trojan']:
        icon = get_protocol_icon(protocol)
        button = InlineKeyboardButton(f"{icon} {protocol.upper()}", callback_data=f'auto_trial_{protocol}')
        row.append(button)
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data='vpn_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"         🎁 TRIAL GENERATOR       \n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>KETENTUAN TRIAL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• Durasi: {TRIAL_CONFIG['duration_hours']} jam\n"
        f"• Quota: {TRIAL_CONFIG['quota']} GB\n"
        f"• IP Limit: {TRIAL_CONFIG['iplimit']}\n"
        f"• Maks: {TRIAL_CONFIG['max_per_day']}x per hari\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>PENGGUNAAN TRIAL ANDA</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Total: {used}/{max_trial} kali\n"
        f"⏰ Sisa: {remaining} kali\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Pilih protokol untuk trial:\n",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return TRIAL_MENU

async def auto_trial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buat trial otomatis"""
    query = update.callback_query
    await query.answer()
    
    protocol = query.data.replace('auto_trial_', '')
    user_id = update.effective_user.id
    username_tele = update.effective_user.username or "Tidak ada username"
    first_name = update.effective_user.first_name or ""
    
    can_create, stock_msg = check_stock_available()
    if not can_create:
        await query.edit_message_text(stock_msg, parse_mode='HTML')
        return TRIAL_MENU
    
    if not TRIAL_CONFIG['enabled']:
        await query.edit_message_text("❌ Trial sedang tidak tersedia.")
        return PROTOKOL
    
    can_trial, message = can_use_trial(user_id)
    
    if not can_trial:
        await query.edit_message_text(
            f"❌ <b>Limit Trial Hari Ini Habis</b>\n\n{message}",
            parse_mode='HTML'
        )
        return TRIAL_MENU
    
    await query.edit_message_text(f"⏱️ Membuat trial {protocol.upper()} 1 jam...")
    
    username = generate_random_username(protocol)
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(8))
    
    config = TRIAL_CONFIG
    days = 1
    
    script_path = SCRIPTS.get(protocol)
    
    if protocol == 'ssh':
        args_list = [username, password, str(config['quota']), str(config['iplimit']), str(days)]
    else:
        args_list = [username, str(days), str(config['quota']), str(config['iplimit'])]
    
    result = await call_script_async(script_path, args_list)
    
    if result.get('status') == 'success':
        save_trial_account(username, protocol, password, hours=config['duration_hours'])
        
        used = await get_trial_count_today(user_id)
        remaining = config['max_per_day'] - used
        expired_time = (datetime.now() + timedelta(hours=config['duration_hours'])).strftime('%H:%M %d/%m/%Y')
        
        try:
            if username_tele != "Tidak ada username":
                clean_user = username_tele.replace('@', '')
                sensor_user = clean_user[:5] + "x" * (len(clean_user)-5) if len(clean_user) > 5 else clean_user
                user_display = f"@{sensor_user}"
            else:
                user_display = first_name[:5] + "x" * (len(first_name)-5) if len(first_name) > 5 else first_name
            
            channel_msg = (
                f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                f"                     🎁 TRIAL AKTIF        \n"
                f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏰ Waktu: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 Pembeli: {user_display}\n"
                f"{get_protocol_icon(protocol)} Protokol: {protocol.upper()}\n"
                f"👤 Username: <code>{username}</code>\n"
                f"⏰ Expired: {expired_time}\n"
                f"📊 Sisa trial: {remaining}x\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            
            channel_id = CHANNEL_ID
            if isinstance(channel_id, str):
                channel_id = int(channel_id)
            
            await context.bot.send_message(
                chat_id=channel_id,
                text=channel_msg,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"❌ Gagal kirim notifikasi: {e}")
        
        if protocol == 'ssh':
            pesan = (
                f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                f"┃     🎁 TRIAL SSH 1 JAM    ┃\n"
                f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 <b>ACCOUNT DETAILS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Username : <code>{username}</code>\n"
                f"🔑 Password : <code>{password}</code>\n"
                f"🌍 Host/IP  : {result.get('domain', 'N/A')}\n"
                f"💾 Quota    : {config['quota']} GB\n"
                f"👥 Limit IP : {config['iplimit']}\n"
                f"📅 Expired  : {expired_time}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔌 <b>CONNECTION PORTS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔹 OpenSSH    : {result.get('ssh_port', '22')}\n"
                f"🔹 Dropbear   : {result.get('dropbear_port', '109, 143')}\n"
                f"🔹 SSH WS     : 80, 8080, 2086, 8880\n"
                f"🔹 SSL/TLS    : 443, 8443\n"
                f"🔹 SSH UDP    : 1-65535\n"
                f"🔹 DNS        : 53, 2222\n"
                f"🔹 BadVPN     : 7100, 7300\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 <b>INFORMASI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• Akun akan otomatis dihapus setelah 1 jam\n"
                f"• Sisa trial hari ini: {remaining}x\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        
        elif protocol == 'vmess':
            pesan = (
                f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                f"┃   🎁 TRIAL VMESS 1 JAM    ┃\n"
                f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 <b>ACCOUNT DETAILS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Remarks</b> : {username}\n"
                f"🔑 <b>UUID</b> : {result.get('uuid', 'N/A')}\n"
                f"🌍 <b>Host/IP</b> : {result.get('domain', 'N/A')}\n"
                f"💾 <b>Quota</b> : {config['quota']} GB\n"
                f"👥 <b>Limit IP</b> : {config['iplimit']}\n"
                f"📅 <b>Expired</b> : {expired_time}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔌 <b>CONNECTION INFO</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔹 <b>Port TLS</b>   : {result.get('port_tls', '443, 8443')}\n"
                f"🔹 <b>Port HTTP</b>  : {result.get('port_http', '80, 8080, 2082, 2086, 8880')}\n"
                f"🔹 <b>Port gRPC</b>  : {result.get('port_grpc', '443')}\n"
                f"🔹 <b>Alter ID</b>   : 0\n"
                f"🔹 <b>Security</b>   : auto\n"
                f"🔹 <b>Network</b>    : ws\n"
                f"🔹 <b>Path</b>       : {result.get('path', '/vmess')}\n"
                f"🔹 <b>Service</b>    : {result.get('service_name', 'vmess-grpc')}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔗 <b>LINKS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            
            if result.get('link_tls'):
                pesan += f"\n⚡ <b>TLS :</b>\n<code>{result['link_tls']}</code>\n"
            if result.get('link_http'):
                pesan += f"\n⚡ <b>HTTP :</b>\n<code>{result['link_http']}</code>\n"
            if result.get('link_grpc'):
                pesan += f"\n⚡ <b>gRPC :</b>\n<code>{result['link_grpc']}</code>\n"
            
            pesan += (
                f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 <b>INFORMASI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• Akun akan otomatis dihapus setelah 1 jam\n"
                f"• Sisa trial hari ini: {remaining}x\n"
                f"• Copy link ke aplikasi VMess client\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        
        elif protocol == 'vless':
            pesan = (
                f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                f"┃   🎁 TRIAL VLESS 1 JAM    ┃\n"
                f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 <b>ACCOUNT DETAILS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Remarks</b> : {username}\n"
                f"🔑 <b>ID</b> : {result.get('uuid', 'N/A')}\n"
                f"🌍 <b>Host/IP</b> : {result.get('domain', 'N/A')}\n"
                f"💾 <b>Quota</b> : {config['quota']} GB\n"
                f"👥 <b>Limit IP</b> : {config['iplimit']}\n"
                f"📅 <b>Expired</b> : {expired_time}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔌 <b>CONNECTION INFO</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔹 <b>Port TLS</b>   : {result.get('port_tls', '443, 8443')}\n"
                f"🔹 <b>Port HTTP</b>  : {result.get('port_http', '80, 8080, 2082, 2086, 8880')}\n"
                f"🔹 <b>Port gRPC</b>  : {result.get('port_grpc', '443')}\n"
                f"🔹 <b>Encryption</b> : none\n"
                f"🔹 <b>Network</b>    : ws\n"
                f"🔹 <b>Path</b>       : {result.get('path', '/vless')}\n"
                f"🔹 <b>Service</b>    : {result.get('service_name', 'vless-grpc')}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔗 <b>LINKS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            
            if result.get('link_tls'):
                pesan += f"\n⚡ <b>TLS :</b>\n<code>{result['link_tls']}</code>\n"
            if result.get('link_http'):
                pesan += f"\n⚡ <b>HTTP :</b>\n<code>{result['link_http']}</code>\n"
            if result.get('link_grpc'):
                pesan += f"\n⚡ <b>gRPC :</b>\n<code>{result['link_grpc']}</code>\n"
            
            pesan += (
                f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 <b>INFORMASI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• Akun akan otomatis dihapus setelah 1 jam\n"
                f"• Sisa trial hari ini: {remaining}x\n"
                f"• Copy link ke aplikasi VLess client\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        
        elif protocol == 'trojan':
            pesan = (
                f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                f"┃   🎁 TRIAL TROJAN 1 JAM   ┃\n"
                f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 <b>ACCOUNT DETAILS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Remarks</b> : {username}\n"
                f"🔑 <b>Password</b> : {result.get('password', password)}\n"
                f"🌍 <b>Host/IP</b> : {result.get('domain', 'N/A')}\n"
                f"💾 <b>Quota</b> : {config['quota']} GB\n"
                f"👥 <b>Limit IP</b> : {config['iplimit']}\n"
                f"📅 <b>Expired</b> : {expired_time}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔌 <b>CONNECTION INFO</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔹 <b>Port TLS</b>   : {result.get('port_tls', '443, 8443')}\n"
                f"🔹 <b>Port gRPC</b>  : {result.get('port_grpc', '443')}\n"
                f"🔹 <b>Path</b>       : {result.get('path', '/trojan-ws')}\n"
                f"🔹 <b>Service</b>    : {result.get('service_name', 'trojan-grpc')}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔗 <b>LINKS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            
            if result.get('link_ws'):
                pesan += f"\n⚡ <b>WebSocket :</b>\n<code>{result['link_ws']}</code>\n"
            if result.get('link_grpc'):
                pesan += f"\n⚡ <b>gRPC :</b>\n<code>{result['link_grpc']}</code>\n"
            
            pesan += (
                f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 <b>INFORMASI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• Akun akan otomatis dihapus setelah 1 jam\n"
                f"• Sisa trial hari ini: {remaining}x\n"
                f"• Copy link ke aplikasi Trojan client\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        
        await query.edit_message_text(pesan, parse_mode='HTML')
        
    else:
        await query.edit_message_text(
            f"❌ <b>GAGAL</b>\n\n{result.get('message', 'Unknown error')}",
            parse_mode='HTML'
        )
    
    return PROTOKOL

# ==========================================
# HANDLER RENEW AKUN
# ==========================================
async def renew_account_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu untuk renew - pilih protokol dulu"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("🚀 SSH", callback_data='renew_proto_ssh'),
            InlineKeyboardButton("📡 VMess", callback_data='renew_proto_vmess'),
        ],
        [
            InlineKeyboardButton("📡 VLess", callback_data='renew_proto_vless'),
            InlineKeyboardButton("🛡️ Trojan", callback_data='renew_proto_trojan'),
        ],
        [InlineKeyboardButton("🔙 Kembali", callback_data='vpn_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔄 <b>RENEW/PERPANJANG AKUN</b>\n\n"
        "Pilih protokol akun yang ingin diperpanjang:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return RENEW_MENU

async def renew_select_protocol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User pilih protokol, lalu minta username"""
    query = update.callback_query
    await query.answer()
    
    protocol = query.data.replace('renew_proto_', '')
    context.user_data['renew_protocol'] = protocol
    
    proto_names = {
        'ssh': '🚀 SSH',
        'vmess': '📡 VMess',
        'vless': '📡 VLess',
        'trojan': '🛡️ Trojan'
    }
    
    keyboard = [[InlineKeyboardButton("❌ Batal", callback_data='renew_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🔄 <b>RENEW AKUN {proto_names[protocol]}</b>\n\n"
        f"📝 Masukkan <b>Username</b> akun yang ingin diperpanjang:\n"
        f"Contoh: <code>myname</code>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return RENEW_USERNAME

async def renew_input_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Terima username yang akan direnew"""
    username = update.message.text.strip()
    protocol = context.user_data.get('renew_protocol')
    
    user_id = update.effective_user.id
    accounts = await get_user_accounts(user_id)
    
    user_accounts = [acc for acc in accounts if acc['protocol'] == protocol and acc['username'] == username]
    
    if not user_accounts:
        keyboard = [[InlineKeyboardButton("❌ Coba Lagi", callback_data='renew_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"❌ Username <code>{username}</code> tidak ditemukan!",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return RENEW_USERNAME
    
    context.user_data['renew_username'] = username
    
    acc = user_accounts[0]
    await update.message.reply_text(
        f"✅ Akun ditemukan:\n\n"
        f"👤 Username: <code>{username}</code>\n"
        f"📦 Protokol: {protocol.upper()}\n"
        f"⏰ Expired: {acc['expired_display']}\n\n"
        f"📝 Masukkan <b>jumlah hari</b> perpanjangan:",
        parse_mode='HTML'
    )
    
    await show_renew_days_table(update, context, username, protocol)
    return RENEW_DAYS
    
async def show_renew_days_table(update: Update, context: ContextTypes.DEFAULT_TYPE, username, protocol):
    """Tabel pilih hari untuk renew"""
    
    if 'selected_numbers' not in context.user_data:
        context.user_data['selected_numbers'] = []
    
    selected = context.user_data['selected_numbers']
    price = PRICES.get(protocol, 500)
    
    total_days = 0
    total_price = 0
    if selected:
        days_str = ''.join(map(str, selected))
        total_days = int(days_str)
        total_price = price * total_days
    
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data='rnum_1'),
            InlineKeyboardButton("2️⃣", callback_data='rnum_2'),
            InlineKeyboardButton("3️⃣", callback_data='rnum_3'),
            InlineKeyboardButton("4️⃣", callback_data='rnum_4'),
            InlineKeyboardButton("5️⃣", callback_data='rnum_5'),
        ],
        [
            InlineKeyboardButton("6️⃣", callback_data='rnum_6'),
            InlineKeyboardButton("7️⃣", callback_data='rnum_7'),
            InlineKeyboardButton("8️⃣", callback_data='rnum_8'),
            InlineKeyboardButton("9️⃣", callback_data='rnum_9'),
            InlineKeyboardButton("0️⃣", callback_data='rnum_0'),
        ],
        [
            InlineKeyboardButton("✅ Konfirmasi", callback_data='renew_confirm'),
            InlineKeyboardButton("🔄 Reset", callback_data='rnum_reset'),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data='renew_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    selected_text = "• Belum ada" if not selected else ' '.join(map(str, selected))
    
    await update.message.reply_text(
        f"🔄 <b>RENEW AKUN {protocol.upper()}</b>\n\n"
        f"👤 Username: <code>{username}</code>\n\n"
        f"📌 Angka dipilih: {selected_text}\n"
        f"📊 Total hari: <b>{total_days} hari</b>\n"
        f"💰 Total harga: <b>Rp {total_price:,}</b>\n\n"
        f"Tekan <b>✅ Konfirmasi</b> untuk melanjutkan.",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def renew_number_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    num = int(query.data.replace('rnum_', ''))
    
    if 'selected_numbers' not in context.user_data:
        context.user_data['selected_numbers'] = []
    
    if len(context.user_data['selected_numbers']) < 3:
        context.user_data['selected_numbers'].append(num)
    else:
        await query.answer("Maksimal 3 digit!", show_alert=True)
        return
    
    selected = context.user_data['selected_numbers']
    protocol = context.user_data.get('renew_protocol')
    username = context.user_data.get('renew_username')
    price = PRICES.get(protocol, 500)
    
    days_str = ''.join(map(str, selected))
    total_days = int(days_str)
    total_price = price * total_days
    
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data='rnum_1'),
            InlineKeyboardButton("2️⃣", callback_data='rnum_2'),
            InlineKeyboardButton("3️⃣", callback_data='rnum_3'),
            InlineKeyboardButton("4️⃣", callback_data='rnum_4'),
            InlineKeyboardButton("5️⃣", callback_data='rnum_5'),
        ],
        [
            InlineKeyboardButton("6️⃣", callback_data='rnum_6'),
            InlineKeyboardButton("7️⃣", callback_data='rnum_7'),
            InlineKeyboardButton("8️⃣", callback_data='rnum_8'),
            InlineKeyboardButton("9️⃣", callback_data='rnum_9'),
            InlineKeyboardButton("0️⃣", callback_data='rnum_0'),
        ],
        [
            InlineKeyboardButton("✅ Konfirmasi", callback_data='renew_confirm'),
            InlineKeyboardButton("🔄 Reset", callback_data='rnum_reset'),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data='renew_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🔄 <b>RENEW AKUN {protocol.upper()}</b>\n\n"
        f"👤 Username: <code>{username}</code>\n\n"
        f"📌 Angka dipilih: {' '.join(map(str, selected))}\n"
        f"📊 Total hari: <b>{total_days} hari</b>\n"
        f"💰 Total harga: <b>Rp {total_price:,}</b>\n\n"
        f"Tekan <b>✅ Konfirmasi</b> untuk melanjutkan.",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def renew_reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['selected_numbers'] = []
    
    protocol = context.user_data.get('renew_protocol')
    username = context.user_data.get('renew_username')
    
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data='rnum_1'),
            InlineKeyboardButton("2️⃣", callback_data='rnum_2'),
            InlineKeyboardButton("3️⃣", callback_data='rnum_3'),
            InlineKeyboardButton("4️⃣", callback_data='rnum_4'),
            InlineKeyboardButton("5️⃣", callback_data='rnum_5'),
        ],
        [
            InlineKeyboardButton("6️⃣", callback_data='rnum_6'),
            InlineKeyboardButton("7️⃣", callback_data='rnum_7'),
            InlineKeyboardButton("8️⃣", callback_data='rnum_8'),
            InlineKeyboardButton("9️⃣", callback_data='rnum_9'),
            InlineKeyboardButton("0️⃣", callback_data='rnum_0'),
        ],
        [
            InlineKeyboardButton("✅ Konfirmasi", callback_data='renew_confirm'),
            InlineKeyboardButton("🔄 Reset", callback_data='rnum_reset'),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data='renew_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🔄 <b>RENEW AKUN {protocol.upper()}</b>\n\n"
        f"👤 Username: <code>{username}</code>\n\n"
        f"📌 Angka dipilih: • Belum ada\n"
        f"📊 Total hari: <b>0 hari</b>\n"
        f"💰 Total harga: <b>Rp 0</b>\n\n"
        f"Tekan angka untuk memilih.",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def renew_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proses renew akun dengan script bash"""
    query = update.callback_query
    await query.answer()
    
    selected = context.user_data.get('selected_numbers', [])
    
    if not selected:
        await query.answer("Pilih jumlah hari dulu!", show_alert=True)
        return RENEW_DAYS
    
    days_str = ''.join(map(str, selected))
    days = int(days_str)
    
    if days < 1 or days > 365:
        await query.answer("Maksimal 365 hari!", show_alert=True)
        return RENEW_DAYS
    
    user_id = update.effective_user.id
    username = context.user_data.get('renew_username')
    protocol = context.user_data.get('renew_protocol')
    
    quota = DEFAULT_QUOTA
    iplimit = DEFAULT_IP_LIMIT
    
    total_price = calculate_price(protocol, days)
    current_balance = get_balance(user_id)
    
    if current_balance < total_price:
        await query.edit_message_text(
            f"❌ <b>Saldo tidak mencukupi!</b>\n\n"
            f"💰 Harga: Rp {total_price:,}\n"
            f"💵 Saldo: Rp {current_balance:,}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💰 Topup", callback_data='topup_saldo'),
                InlineKeyboardButton("🔙 Kembali", callback_data='renew_menu')
            ]])
        )
        return PROTOKOL
    
    update_balance(user_id, -total_price, f"Renew akun {protocol} {username} +{days} hari")
    
    result = await renew_with_script(protocol, username, days, quota, iplimit)
    
    if result.get('status') == 'success':
        save_account_log(
            update=update,
            username=username,
            protocol=protocol,
            days=days,
            quota=quota,
            iplimit=iplimit,
            expired_date=result.get('expired'),
            status="success",
            notes=f"Perpanjang {days} hari",
            action="renew"
        )
        
        await query.edit_message_text(
            f"✅ <b>RENEW AKUN BERHASIL!</b>\n\n"
            f"👤 Username: <code>{username}</code>\n"
            f"📦 Protokol: {protocol.upper()}\n"
            f"📅 Perpanjang: {days} hari\n"
            f"💰 Total: Rp {total_price:,}\n"
            f"💵 Sisa saldo: Rp {get_balance(user_id):,}\n\n"
            f"⏰ Expired baru: {result.get('expired', 'N/A')}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Renew Lagi", callback_data='renew_menu'),
                InlineKeyboardButton("🏠 Menu", callback_data='kembali_ke_menu')
            ]])
        )
    else:
        update_balance(user_id, total_price, f"Refund gagal renew {protocol} {username}")
        
        save_account_log(
            update=update,
            username=username,
            protocol=protocol,
            days=days,
            quota=quota,
            iplimit=iplimit,
            expired_date=None,
            status="failed",
            notes=result.get('message', 'Unknown error'),
            action="renew"
        )
        
        await query.edit_message_text(
            f"❌ <b>RENEW GAGAL!</b>\n\n{result.get('message', 'Unknown error')}\n\n💰 Saldo dikembalikan: Rp {total_price:,}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Kembali", callback_data='renew_menu')
            ]])
        )
    
    context.user_data.clear()
    return PROTOKOL

# ==========================================
# HANDLER CEK SALDO
# ==========================================
async def cek_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    balance = get_balance(user_id)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT type, amount, description, timestamp FROM transaksi WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5", 
              (user_id,))
    trans = c.fetchall()
    conn.close()
    
    pesan = (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"         💰 INFO SALDO    \n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 User ID: <code>{user_id}</code>\n"
        f"💵 Saldo: <b>Rp {balance:,}</b>\n\n"
        f"📋 Harga Akun per Hari:\n"
        f"──────────────────\n"
        f"🚀 SSH      : Rp {PRICES['ssh']:,}\n"
        f"🚀 VMess    : Rp {PRICES['vmess']:,}\n"
        f"📡 VLess    : Rp {PRICES['vless']:,}\n"
        f"🛡️ Trojan   : Rp {PRICES['trojan']:,}\n\n"
    )
    
    if trans:
        pesan += "📜 LOG USER :\n"
        pesan += "──────────────────\n"
        for t in trans:
            icon = "✅" if t[0] == 'credit' else "❌"
            pesan += f"{icon} {t[2]}: Rp {t[1]:,}\n   ({t[3][:16]})\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Kembali", callback_data='kembali_ke_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(pesan, parse_mode='HTML', reply_markup=reply_markup)
    
    return PROTOKOL

async def topup_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """MENU TOPUP SALDO"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        keyboard = [[InlineKeyboardButton("❌ Batal", callback_data='batal_topup_custom')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "💰 <b>TOP UP SALDO</b>\n\n"
            "📝 Masukkan nominal topup (dalam Rupiah):\n"
            "Contoh: <code>10000</code>\n\n"
            "Minimal: Rp 1.000\n"
            "🎁 Bonus: <b>Rp 1.000</b> per transaksi\n"
            "⏰ QRIS Exp: <b>15 menit</b>\n\n"
            "Ketik angka langsung di chat ini",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return TOPUP_NOMINAL
    else:
        await update.message.reply_text(
            "💰 <b>TOP UP SALDO</b>\n\n"
            "Silakan klik tombol Topup di menu.",
            parse_mode='HTML'
        )
        return TOPUP_NOMINAL


async def input_nominal_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """INPUT NOMINAL TOPUP"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if not text.isdigit():
        await update.message.reply_text(
            "❌ <b>INPUT TIDAK VALID!</b>\n\n"
            "Masukkan <b>ANGKA</b> untuk nominal topup.\n"
            "Contoh: <code>50000</code>",
            parse_mode='HTML'
        )
        return TOPUP_NOMINAL
    
    amount = int(text)
    
    if amount < 1000:
        await update.message.reply_text(
            "❌ Minimal topup Rp 1.000\n\n"
            "Silakan masukkan nominal yang lebih besar.",
            parse_mode='HTML'
        )
        return TOPUP_NOMINAL
    
    if amount > 1000000:
        await update.message.reply_text(
            "❌ Maksimal topup Rp 1.000.000\n\n"
            "Silakan masukkan nominal yang lebih kecil.",
            parse_mode='HTML'
        )
        return TOPUP_NOMINAL
    
    context.user_data['topup_amount'] = amount
    context.user_data['topup_user'] = user_id
    
    loading_msg = await update.message.reply_text(
        "⏳ <b>MEMPROSES...</b>\n\nMohon tunggu sebentar.",
        parse_mode='HTML'
    )
    
    await proses_topup_qris_from_message(update, context, amount, loading_msg)
    
    return PROTOKOL

async def proses_topup_qris(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int):
    """
    PROSES TOPUP VIA QRIS - DARI CALLBACK QUERY - FIXED
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or "Customer"
    
    try:
        pakasir = get_pakasir()
        if pakasir is None:
            pakasir = init_pakasir(context.bot)
            print("✅ Pakasir diinisialisasi")
        
        result = await pakasir.create_deposit(
            user_id=user_id,
            amount=amount,
            username=username
        )
        
        if not result.get('success'):
            error_msg = result.get('error', 'Unknown error')
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ <b>GAGAL MEMBUAT INVOICE</b>\n\n"
                     f"Error: {error_msg}\n\n"
                     f"Silakan coba lagi atau hubungi admin.",
                parse_mode='HTML'
            )
            return
        
        order_id = result.get('order_id')
        payment_number = result.get('payment_number', '')
        total_payment = result.get('total_payment', amount)
        expired_time = result.get('expired_time', 10)
        
        print(f"✅ Invoice created: {order_id} | Amount: {amount}")
        
        qr_image = generate_qr_image(payment_number)
        
        caption = (
            f"💳 <b>PEMBAYARAN QRIS</b>\n\n"
            f"💰 Nominal: Rp {amount:,}\n"
            f"💵 Total Dibayar: Rp {total_payment:,}\n"
            f"🆔 Order ID: <code>{order_id}</code>\n\n"
            f"📱 <b>INSTRUKSI:</b>\n"
            f"1. Scan QR Code di atas\n"
            f"2. Lakukan pembayaran\n"
            f"3. Saldo akan otomatis bertambah setelah pembayaran sukses\n\n"
            f"⏳ Waktu kadaluarsa: {expired_time} menit"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Cek Status", callback_data=f'cek_status_{order_id}')],
            [InlineKeyboardButton("❌ Batal", callback_data=f'batal_topup_{order_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            if update.callback_query:
                await update.callback_query.delete_message()
        except Exception as e:
            print(f"⚠️ Gagal delete loading message: {e}")
        
        if qr_image:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=qr_image,
                caption=caption,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"{caption}\n\n⚠️ Gagal generate QR Code. Silakan hubungi admin.",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        
        context.user_data['topup_order_id'] = order_id
        context.user_data['topup_amount'] = amount
        
        asyncio.create_task(start_polling_topup(context, order_id, user_id, amount))
        
    except Exception as e:
        print(f"❌ Error di proses_topup_qris: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ <b>TERJADI KESALAHAN</b>\n\n{str(e)}",
            parse_mode='HTML'
        )
		
# ==========================================
# GENERATE QRIS DENGAN DESAIN BIRU & PUTIH
# ==========================================
from PIL import Image, ImageDraw, ImageFont
import io

def generate_qr_image_with_design(payment_number, amount="50.000"):
    """Generate QRIS dengan background putih dan top bar biru"""
    try:
        # STEP 1: Generate QR code biasa dulu
        qr_image_plain = generate_qr_image(payment_number)
        
        if not qr_image_plain:
            print("❌ QR code gagal di-generate")
            return None
        
        # STEP 2: Konversi ke PIL Image
        if isinstance(qr_image_plain, bytes):
            qr_img = Image.open(io.BytesIO(qr_image_plain))
        else:
            qr_img = qr_image_plain
        
        # STEP 3: Resize QR code
        qr_size = 280
        qr_img = qr_img.resize((qr_size, qr_size))
        
        # STEP 4: Buat background canvas PUTIH
        bg_width = 400
        bg_height = 600
        background = Image.new('RGB', (bg_width, bg_height), color='#FFFFFF')
        
        # STEP 5: Draw top bar BIRU
        draw = ImageDraw.Draw(background)
        draw.rectangle(
            [(0, 0), (bg_width, 80)],
            fill='#1E3A8A'  # Biru gelap
        )
        
        # STEP 6: Gradient effect (biru lebih muda di bawah top bar)
        for y in range(80, 100):
            # Buat gradient transisi dari biru ke putih
            intensity = int(30 + (y - 80) * 2)
            color = f'#{0x1E3A8A + intensity}'
            draw.line([(0, y), (bg_width, y)], fill='#E8EEFF')
        
        # STEP 7: Paste QR code ke tengah
        qr_x = (bg_width - qr_size) // 2
        qr_y = 120
        background.paste(qr_img, (qr_x, qr_y))
        
        # STEP 8: Load font
        try:
            font_title = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20
            )
            font_text = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14
            )
            font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12
            )
        except:
            font_title = ImageFont.load_default()
            font_text = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # STEP 9: Draw text di top bar BIRU (putih)
        text_header = "PEMBAYARAN QRIS"
        bbox = draw.textbbox((0, 0), text_header, font=font_title)
        text_width = bbox[2] - bbox[0]
        text_x = (bg_width - text_width) // 2
        draw.text(
            (text_x, 25),
            text_header,
            fill='#FFFFFF',
            font=font_title
        )
        
        # STEP 10: Draw border QR code (BIRU)
        border_x1 = qr_x - 10
        border_y1 = qr_y - 10
        border_x2 = qr_x + qr_size + 10
        border_y2 = qr_y + qr_size + 10
        draw.rectangle(
            [(border_x1, border_y1), (border_x2, border_y2)],
            outline='#1E3A8A',
            width=3
        )
        
        # STEP 11: Draw info section (background putih dengan border biru)
        info_y = qr_y + qr_size + 30
        draw.rectangle(
            [(20, info_y), (bg_width - 20, bg_height - 10)],
            outline='#1E3A8A',
            width=2,
            fill='#F8FAFF'  # Putih sedikit kebiruan
        )
        
        # STEP 12: Draw text "SCAN UNTUK BAYAR"
        text_scan = "📱 SCAN UNTUK BAYAR"
        bbox = draw.textbbox((0, 0), text_scan, font=font_title)
        text_width = bbox[2] - bbox[0]
        text_x = (bg_width - text_width) // 2
        draw.text(
            (text_x, info_y + 15),
            text_scan,
            fill='#1E3A8A',
            font=font_title
        )
        
        # STEP 13: Draw nominal
        text_nominal = f"Rp {amount}"
        bbox = draw.textbbox((0, 0), text_nominal, font=font_text)
        text_width = bbox[2] - bbox[0]
        text_x = (bg_width - text_width) // 2
        draw.text(
            (text_x, info_y + 55),
            text_nominal,
            fill='#000000',
            font=font_text
        )
        
        # STEP 14: Draw info berlaku
        text_info = "⏰ Berlaku 15 menit"
        bbox = draw.textbbox((0, 0), text_info, font=font_small)
        text_width = bbox[2] - bbox[0]
        text_x = (bg_width - text_width) // 2
        draw.text(
            (text_x, info_y + 90),
            text_info,
            fill='#1E3A8A',
            font=font_small
        )
        
        # STEP 15: Draw decoration line
        draw.line(
            [(40, info_y + 125), (bg_width - 40, info_y + 125)],
            fill='#1E3A8A',
            width=1
        )
        
        # STEP 16: Convert ke bytes dan return
        img_bytes = io.BytesIO()
        background.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        print("✅ QRIS dengan desain biru-putih berhasil di-generate")
        return img_bytes
        
    except Exception as e:
        print(f"❌ Error generate QRIS design: {e}")
        import traceback
        traceback.print_exc()
        return None

async def proses_topup_qris_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                          amount: int, loading_msg):
    """PROSES TOPUP - DETAIL LENGKAP"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Customer"
    first_name = update.effective_user.first_name or ""
    last_name = update.effective_user.last_name or ""
    
    try:
        pakasir = get_pakasir()
        if pakasir is None:
            pakasir = init_pakasir(context.bot)
        
        # ===== HITUNG =====
        FEE_MERCHANT = 255
        bonus_amount = 1000
        total_payment = amount + FEE_MERCHANT
        net_amount = amount + bonus_amount
        expired_time = 15  # 15 MENIT
        
        # ===== KIRIM KE PAKASIR =====
        result = await pakasir.create_deposit(
            user_id=user_id,
            amount=total_payment,
            username=username
        )
        
        if not result.get('success'):
            error_msg = result.get('error', 'Unknown error')
            await loading_msg.edit_text(
                f"❌ <b>GAGAL</b>\n\n{error_msg}",
                parse_mode='HTML'
            )
            return
        
        order_id = result.get('order_id')
        payment_number = result.get('payment_number', '')
        
        # ===== HITUNG EXPIRED =====
        expired_datetime = datetime.now() + timedelta(minutes=expired_time)
        expired_time_str = expired_datetime.strftime('%H:%M:%S')
        expired_date_str = expired_datetime.strftime('%d/%m/%Y %H:%M:%S')
        
        print(f"✅ [TOPUP] expired_datetime: {expired_datetime.isoformat()}")
        
        # ===== SIMPAN DATA DENGAN EXPIRED_AT =====
        trx_data = {
            'amount': amount,
            'fee': FEE_MERCHANT,
            'total_payment': total_payment,
            'bonus': bonus_amount,
            'net': net_amount,
            'expired_at': expired_datetime.isoformat(),  # <-- PASTIKAN TERSIMPAN
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'order_id': order_id,
            'status': 'pending',
            'balance_added': False,
            'expired_notified': False
        }
        save_pakasir_transaction(order_id, trx_data)
        
        print(f"✅ [TOPUP] Transaksi disimpan: {order_id}")
        print(f"   - amount: {amount}, fee: {FEE_MERCHANT}, total: {total_payment}")
        print(f"   - expired_at: {expired_datetime.isoformat()}")
        
        qr_image = generate_qr_image(payment_number)
        
        caption = (
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"          🛍️ QRIS PAYMENT 🛍\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"<code>💵 Nominal TopUp :</code> <b>Rp {amount:,}</b>\n"
            f"<code>🎁 Bonus Saldo   :</code> <b>Rp {bonus_amount:,}</b>\n"
            f"<code>📊 Kode Unik     :</code> <b>Rp {FEE_MERCHANT:,}</b>\n"
            f"─────────────────────\n"
            f"🆔 Order ID : <b>{order_id}</b>\n"
            f"💳 Total Bayar  : <b>Rp {total_payment:,}</b>\n"
            f"─────────────────────\n"
            f"📅 QRIS Exp : {expired_date_str}\n"
            f"─────────────────────\n"
            f"<b>QRIS berlaku 15 menit untuk 1x pembayaran</b>\n"
			f"<b>Silahkan hubungi admin jika ada kendala</b>\n\n"
			f"<i>Scan QRIS di atas ini untuk pembayaran</i>\n"
			f"<i>Saldo otomatis masuk setelah pembayaran</i>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Cek Status", callback_data=f'cek_status_{order_id}')],
            [InlineKeyboardButton("❌ Batalkan", callback_data=f'batal_topup_{order_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await loading_msg.delete()
        except:
            pass
        
        if qr_image:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=qr_image,
                caption=caption,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"{caption}\n\n⚠️ Gagal generate QR.",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        
        context.user_data['topup_order_id'] = order_id
        context.user_data['topup_amount'] = amount
        
        # START POLLING
        asyncio.create_task(start_polling_topup(context, order_id, user_id, amount))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        await loading_msg.edit_text(
            f"❌ <b>ERROR</b>\n\n{str(e)}",
            parse_mode='HTML'
        )
		
		
async def kirim_pengingat_expired(context: ContextTypes.DEFAULT_TYPE, 
                                   order_id: str, user_id: int, 
                                   amount: int, expired_at: datetime):
    """Kirim pengingat 5 menit sebelum expired"""
    try:
        # Tunggu 10 menit (600 detik)
        await asyncio.sleep(600)
        
        # CEK APAKAH TRANSAKSI MASIH ADA
        pakasir = get_pakasir()
        if pakasir is None:
            return
        
        trx = pakasir.get_transaction(order_id)
        if not trx:
            return
        
        # CEK STATUS
        result = await pakasir.check_status(order_id)
        if result.get('status') == 'pending':
            # HITUNG SISA WAKTU
            now = datetime.now()
            sisa_menit = int((expired_at - now).seconds / 60)
            
            if sisa_menit > 0 and sisa_menit <= 5:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"⏰ <b>PENGINGAT!</b>\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🆔 Order: <code>{order_id}</code>\n"
                        f"💰 Nominal: Rp {amount:,}\n"
                        f"⏳ Sisa waktu: <b>{sisa_menit} menit</b>\n\n"
                        f"⚠️ Segera selesaikan pembayaran sebelum transaksi expired!\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    parse_mode='HTML'
                )
                print(f"✅ [PENGINGAT] Terkirim ke {user_id}, sisa {sisa_menit} menit")
                
    except Exception as e:
        print(f"❌ Gagal kirim pengingat: {e}")

async def start_polling_topup(context: ContextTypes.DEFAULT_TYPE, 
                               order_id: str, user_id: int, amount: int):
    """
    POLLING STATUS PEMBAYARAN - AUTO EXPIRED + NOTIFIKASI
    """
    pakasir = get_pakasir()
    if pakasir is None:
        print("❌ Pakasir tidak terinialisasi")
        return
    
    trx = pakasir.get_transaction(order_id)
    if not trx:
        print(f"⚠️ Transaksi {order_id} tidak ditemukan")
        return
    
    # ===== AMBIL DATA DARI TRX =====
    FEE_MERCHANT = 250
    bonus_amount = 1000
    total_payment = trx.get('total_payment', amount + FEE_MERCHANT)
    net_amount = trx.get('net', amount + bonus_amount)
    amount_asli = trx.get('amount', amount)
    
    # AMBIL EXPIRED AT
    expired_at_str = trx.get('expired_at')
    if expired_at_str:
        expired_at = datetime.fromisoformat(expired_at_str)
    else:
        expired_at = datetime.now() + timedelta(minutes=15)
        trx['expired_at'] = expired_at.isoformat()
        save_pakasir_transaction(order_id, trx)
    
    print(f"🔍 [POLLING] Mulai polling untuk {order_id}")
    print(f"🔍 [POLLING] total_payment: {total_payment}")
    print(f"🔍 [POLLING] Expired at: {expired_at.strftime('%H:%M:%S')}")
    print(f"🔍 [POLLING] Sisa waktu: {(expired_at - datetime.now()).seconds // 60} menit")
    
    max_retries = 180 # 15 menit
    notifikasi_terkirim = False
    pengingat_terkirim = False
    
    for attempt in range(max_retries):
        # CEK APAKAH TRANSAKSI MASIH ADA
        trx_check = pakasir.get_transaction(order_id)
        if not trx_check:
            print(f"🛑 [POLLING] Transaksi {order_id} dibatalkan/dihapus")
            return
        
        now = datetime.now()
        sisa_menit = int((expired_at - now).seconds / 60)
        
        # LOG SETIAP 30 DETIK
        if attempt % 6 == 0:
            print(f"🔍 [POLLING] {order_id}: sisa={sisa_menit} menit (attempt {attempt+1})")
        
        # ===== KIRIM PENGINGAT 5 MENIT SEBELUM EXPIRED =====
        if not pengingat_terkirim and sisa_menit <= 5 and sisa_menit > 0 and attempt > 0:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"<b>❗PERINGATAN...</b>\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🆔 Order: <code>{order_id}</code>\n"
                        f"💰 Nominal: Rp {amount_asli:,}\n"
                        f"💳 Total Bayar: Rp {total_payment:,}\n"
                        f"⏳ Sisa waktu: <b>{sisa_menit} menit</b>\n\n"
                        f"⚠️ Segera selesaikan pembayaran sebelum transaksi expired!\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    parse_mode='HTML'
                )
                pengingat_terkirim = True
                print(f"✅ [PENGINGAT] Terkirim ke {user_id}, sisa {sisa_menit} menit")
            except Exception as e:
                print(f"❌ Gagal kirim pengingat: {e}")
        
        # ===== CEK EXPIRED =====
        if now >= expired_at:
            print(f"⏰ [POLLING] Transaksi {order_id} EXPIRED")
            
            if not notifikasi_terkirim:
                try:
                    # UPDATE STATUS DI PAKASIR
                    await pakasir._update_status(order_id, 'expired')
                    
                    # KIRIM NOTIFIKASI EXPIRED KE USER
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"⏰ <b>⚠️ TRANSAKSI KADALUARSA!</b>\n\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"💳 <b>DETAIL TRANSAKSI</b>\n"
                            f"─────────────────────\n"
                            f"🆔 Order ID: <code>{order_id}</code>\n"
                            f"💰 Nominal Topup: Rp {amount_asli:,}\n"
                            f"💳 Total Bayar: Rp {total_payment:,}\n"
                            f"⏰ Expired pada: {expired_at.strftime('%H:%M:%S')}\n"
                            f"📅 Tanggal: {expired_at.strftime('%d/%m/%Y')}\n\n"
                            f"❌ Transaksi otomatis dibatalkan karena tidak dibayar.\n"
                            f"💡 Silakan lakukan topup ulang jika masih ingin.\n\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        parse_mode='HTML'
                    )
                    
                    notifikasi_terkirim = True
                    trx_check['expired_notified'] = True
                    save_pakasir_transaction(order_id, trx_check)
                    
                    print(f"✅ [POLLING] Notifikasi expired terkirim ke {user_id}")
                    
                except Exception as e:
                    print(f"❌ [POLLING] Gagal kirim notifikasi expired: {e}")
            
            delete_pakasir_transaction(order_id)
            print(f"🗑️ [POLLING] Transaksi {order_id} dihapus setelah expired")
            return
        
        # ===== CEK STATUS =====
        try:
            result = await pakasir.check_status(order_id, amount=total_payment)
            
            if not result.get('success'):
                await asyncio.sleep(5)
                continue
            
            status = result.get('status', 'pending')
            
            if status == 'completed':
                # UPDATE SALDO
                update_balance(user_id, net_amount, f"Topup via QRIS (Bonus +{bonus_amount}) ID: {order_id}")
                new_balance = get_balance(user_id)
                
                # NOTIFIKASI SUKSES
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"<b>PEMBAYARAN BERHASIL...</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"<code>💵 Nominal TopUp :</code> <b>Rp {amount_asli:,}</b>\n"
                        f"<code>📊 Kode Unik     :</code> <b>Rp {FEE_MERCHANT:,}</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"<code>💳 Total Bayar   :</code> <b>Rp {total_payment:,}</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"<code>🎁 Bonus Saldo   :</code> <b>Rp {bonus_amount:,}</b>\n"
                        f"<code>✅ Saldo Masuk   :</code> <b>Rp {net_amount:,}</b>\n"
                        f"<code>💵 Saldo Baru    :</code> <b>Rp {new_balance:,}</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    ),
                    parse_mode='HTML'
                )
                
                # LOG KE CHANNEL
                await send_topup_log_to_channel(
                    context, 
                    user_id=user_id,
                    order_id=order_id,
                    amount=amount_asli,
                    fee=FEE_MERCHANT,
                    bonus=bonus_amount,
                    total_payment=total_payment,
                    net_amount=net_amount,
                    new_balance=new_balance
                )
                
                delete_pakasir_transaction(order_id)
                print(f"✅ [POLLING] Transaksi {order_id} selesai (completed)")
                return
            
            elif status in ['expired', 'failed', 'timeout']:
                if not notifikasi_terkirim:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"⏰ <b>TRANSAKSI KADALUARSA!</b>\n\n"
                            f"🆔 Order ID: <code>{order_id}</code>\n"
                            f"💰 Nominal: Rp {amount_asli:,}\n\n"
                            f"❌ Transaksi otomatis dibatalkan."
                        ),
                        parse_mode='HTML'
                    )
                    notifikasi_terkirim = True
                
                delete_pakasir_transaction(order_id)
                return
            
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"❌ [POLLING] Error polling {order_id}: {e}")
            await asyncio.sleep(5)
    
    # TIMEOUT
    if not notifikasi_terkirim:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"<b>PEMBAYARAN TIDAK TERDETEKSI</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 Order ID: <code>{order_id}</code>\n"
                    f"💰 Nominal: Rp {amount_asli:,}\n\n"
                    f"⚠️ Sistem tidak dapat memverifikasi pembayaran.\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                parse_mode='HTML'
            )
        except:
            pass
    
    delete_pakasir_transaction(order_id)
    print(f"🗑️ [POLLING] Transaksi {order_id} dihapus (timeout)")
	
	
async def send_topup_log_to_channel(context: ContextTypes.DEFAULT_TYPE, 
                                     user_id: int, 
                                     order_id: str,
                                     amount: int,
                                     fee: int,
                                     bonus: int,
                                     total_payment: int,
                                     net_amount: int,
                                     new_balance: int):
    """Kirim log topup sukses ke channel Telegram"""
    try:
        # AMBIL INFO USER
        try:
            user = await context.bot.get_chat(user_id)
            username = user.username or "Tidak ada username"
            first_name = user.first_name or "User"
            last_name = user.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
        except:
            username = "Unknown"
            full_name = "Unknown User"
        
        # SENSOR USERNAME
        if username != "Tidak ada username" and username != "Unknown":
            clean_username = username.replace('@', '')
            if len(clean_username) > 5:
                sensor_username = clean_username[:5] + "x" * (len(clean_username) - 5)
            else:
                sensor_username = clean_username
            user_display = f"@{sensor_username}"
        else:
            if len(full_name) > 5:
                sensor_name = full_name[:5] + "x" * (len(full_name) - 5)
            else:
                sensor_name = full_name
            user_display = sensor_name
        
        # SENSOR ORDER ID
        if len(order_id) > 8:
            sensor_order = order_id[:4] + "****" + order_id[-4:]
        else:
            sensor_order = order_id
        
        waktu = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        message = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"                ✅ TOPUP BERHASIL   \n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ Waktu: {waktu}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Pembeli: {full_name}\n"
            f"🆔 Order ID: <code>{sensor_order}</code>\n\n"
            f"<code>💵 Nominal TopUp :</code> <b>Rp {amount:,}</b>\n"
            f"<code>🎁 Bonus Saldo   :</code> <b>Rp {bonus:,}</b>\n"
            f"<code>✅ Saldo Masuk   :</code> <b>Rp {net_amount:,}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 BOT AUTO ORDER\n"
            f"🤖 @autobuy_produk_bot\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
			f"Terimakasih telah menggunakan layanan kami"
        )
        
        # ===== KIRIM KE CHANNEL =====
        channel_id = CHANNEL_ID
        if not channel_id or channel_id == 0:
            print("⚠️ CHANNEL_ID tidak valid, skip notifikasi channel")
            return False
        
        if isinstance(channel_id, str):
            try:
                channel_id = int(channel_id)
            except ValueError:
                pass
        
        await context.bot.send_message(
            chat_id=channel_id,
            text=message,
            parse_mode='HTML'
        )
        print(f"✅ Log topup terkirim ke channel: {channel_id}")
        return True
        
    except Exception as e:
        print(f"❌ Gagal kirim log ke channel: {e}")
        return False

async def cek_status_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """CEK STATUS - DETAIL LENGKAP + LOG KE CHANNEL"""
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith('cek_status_'):
        await query.answer("❌ Callback tidak valid", show_alert=True)
        return TOPUP_NOMINAL
    
    order_id = query.data.replace('cek_status_', '')
    user_id = update.effective_user.id
    
    loading_msg = await context.bot.send_message(
        chat_id=user_id,
        text="⏳ <b>MENGECEK STATUS...</b>",
        parse_mode='HTML'
    )
    
    try:
        pakasir = get_pakasir()
        if pakasir is None:
            await loading_msg.edit_text("❌ Sistem sibuk")
            return TOPUP_NOMINAL
        
        trx_data = pakasir.get_transaction(order_id)
        if not trx_data:
            await loading_msg.edit_text(
                f"❌ Transaksi tidak ditemukan\n🆔 {order_id}",
                parse_mode='HTML'
            )
            return TOPUP_NOMINAL
        
        # ===== AMBIL DATA DARI TRX =====
        amount = trx_data.get('amount', 0)
        FEE_MERCHANT = 250
        bonus_amount = 1000
        total_payment = trx_data.get('total_payment', amount + FEE_MERCHANT)
        net_amount = trx_data.get('net', amount + bonus_amount)
        expired_at = datetime.fromisoformat(trx_data.get('expired_at', datetime.now().isoformat()))
        
        # ===== CEK STATUS =====
        result = await pakasir.check_status(order_id, amount=total_payment)
        status = result.get('status', 'pending')
        
        now = datetime.now()
        is_expired = now >= expired_at
        
        text = (
            f"💰 <b>STATUS PEMBAYARAN</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Order: <code>{order_id}</code>\n"
            f"📊 Status: {status.upper()}\n\n"
        )
        
        if is_expired and status == 'pending':
            text += f"⏰ <b>TRANSAKSI KADALUARSA!</b>\n\n"
            # UPDATE STATUS JIKA EXPIRED
            await pakasir._update_status(order_id, 'expired')
            status = 'expired'
        elif status == 'pending':
            remaining = int((expired_at - now).seconds / 60)
            if remaining > 0:
                text += f"⏳ Sisa: {remaining} menit\n"
                text += f"⏰ Expired: {expired_at.strftime('%H:%M:%S')}\n\n"
            else:
                text += f"⏰ Transaksi akan expired dalam beberapa detik...\n\n"
        elif status == 'expired':
            text += f"⏰ Expired pada: {expired_at.strftime('%H:%M:%S')}\n\n"
        
        text += (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>RINCIAN</b>\n"
            f"─────────────────────\n"
            f"💵 Nominal     : Rp {amount:,}\n"
            f"📊 Kode Unik   : +Rp {FEE_MERCHANT:,}\n"
            f"💳 Total Bayar : <b>Rp {total_payment:,}</b>\n"
            f"─────────────────────\n"
            f"🎁 Bonus       : +Rp {bonus_amount:,}\n"
            f"✅ Saldo Masuk : <b>Rp {net_amount:,}</b>\n"
        )
        
        keyboard = []
        if status == 'pending' and not is_expired:
            keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data=f'cek_status_{order_id}')])
            keyboard.append([InlineKeyboardButton("❌ Batal", callback_data=f'batal_topup_{order_id}')])
        elif status == 'completed':
            keyboard.append([InlineKeyboardButton("🏠 Menu", callback_data='kembali_ke_menu')])
        else:
            keyboard.append([InlineKeyboardButton("💰 Topup Lagi", callback_data='topup_saldo')])
            keyboard.append([InlineKeyboardButton("🏠 Menu", callback_data='kembali_ke_menu')])
        
        await loading_msg.edit_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )
        
        # AUTO ADD SALDO JIKA COMPLETED
        if status == 'completed' and not trx_data.get('balance_added', False):
            new_balance = get_balance(user_id) + net_amount
            update_balance(user_id, net_amount, f"Topup QRIS (Bonus +{bonus_amount}) ID: {order_id}")
            trx_data['balance_added'] = True
            save_pakasir_transaction(order_id, trx_data)
            
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ Saldo +Rp {net_amount:,}\n💵 Saldo baru: Rp {get_balance(user_id):,}",
                parse_mode='HTML'
            )
            
            await send_topup_log_to_channel(
                context,
                user_id=user_id,
                order_id=order_id,
                amount=amount,
                fee=FEE_MERCHANT,
                bonus=bonus_amount,
                total_payment=total_payment,
                net_amount=net_amount,
                new_balance=get_balance(user_id)
            )
        
        return TOPUP_NOMINAL
        
    except Exception as e:
        await loading_msg.edit_text(f"❌ Error: {str(e)}")
        return TOPUP_NOMINAL

async def batal_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """BATALKAN TOPUP - LANGSUNG HAPUS & STOP POLLING"""
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.replace('batal_topup_', '')
    user_id = update.effective_user.id
    
    loading_msg = await context.bot.send_message(
        chat_id=user_id,
        text="⏳ Membatalkan...",
        parse_mode='HTML'
    )
    
    try:
        pakasir = get_pakasir()
        if pakasir:
            trx = pakasir.get_transaction(order_id)
            if trx:
                delete_pakasir_transaction(order_id)
                print(f"✅ Transaksi {order_id} dihapus oleh user")
        
        keyboard = [
            [InlineKeyboardButton("💰 Topup Lagi", callback_data='topup_saldo')],
            [InlineKeyboardButton("🏠 Menu", callback_data='kembali_ke_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(
            f"❌ <b>TOPUP DIBATALKAN</b>\n\n"
            f"🆔 Order ID: <code>{order_id}</code>\n\n"
            f"Silakan lakukan topup ulang jika ingin menambah saldo.",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
        return PROTOKOL
        
    except Exception as e:
        await loading_msg.edit_text(f"❌ Error: {str(e)}")
        return PROTOKOL

async def batal_topup_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """BATAL TOPUP"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "❌ <b>TOPUP DIBATALKAN</b>\n\n"
        "Silakan pilih menu lain.",
        parse_mode='HTML'
    )
    
    await start(update, context)
    return PROTOKOL

# ==========================================
# HANDLER MENU VOUCHER
# ==========================================
async def voucher_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    is_owner = (user_id == OWNER_ID)
    
    keyboard = [
        [InlineKeyboardButton("🎟️ Redeem Voucher", callback_data='voucher_redeem')]
    ]
    
    if is_owner:
        keyboard.insert(0, [InlineKeyboardButton("✨ Generate Voucher", callback_data='voucher_generate')])
        keyboard.insert(1, [InlineKeyboardButton("⚙️ Reset Saldo User", callback_data='reset_saldo_menu')])
        keyboard.insert(2, [InlineKeyboardButton("📢 Broadcast Message", callback_data='broadcast_menu')])
        keyboard.insert(3, [InlineKeyboardButton("📦 Manajemen Stok", callback_data='stock_menu')])
        keyboard.append([InlineKeyboardButton("📋 Daftar Voucher", callback_data='voucher_list')])
        keyboard.append([InlineKeyboardButton("💰 Edit Harga", callback_data='edit_harga_menu')])
    
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data='kembali_ke_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎟️ <b>MENU VOUCHER</b>\n\nPilih opsi di bawah:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return VOUCHER_MENU

# ==========================================
# HANDLER VOUCHER GENERATE
# ==========================================
async def voucher_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != OWNER_ID:
        await query.edit_message_text("❌ Hanya owner yang bisa generate voucher!")
        return VOUCHER_MENU
    
    keyboard = [
        [InlineKeyboardButton("💰 Saldo", callback_data='gen_saldo'), InlineKeyboardButton("🚀 SSH", callback_data='gen_ssh')],
        [InlineKeyboardButton("📡 VMess", callback_data='gen_vmess'), InlineKeyboardButton("📡 VLess", callback_data='gen_vless')],
        [InlineKeyboardButton("🛡️ Trojan", callback_data='gen_trojan'), InlineKeyboardButton("🔙 Kembali", callback_data='voucher_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("✨ <b>GENERATE VOUCHER</b>\n\nPilih tipe voucher:", parse_mode='HTML', reply_markup=reply_markup)
    return VOUCHER_GENERATE

async def voucher_generate_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    v_type = query.data.replace('gen_', '')
    context.user_data['voucher_type'] = v_type
    
    if v_type == 'saldo':
        prompt = "💰 Masukkan <b>nominal saldo</b> (Rp):\nContoh: 50000"
    else:
        prompt = f"📅 Masukkan <b>jumlah hari</b>:\nContoh: 30"
    
    await query.edit_message_text(
        f"✨ <b>Generate {v_type.upper()}</b>\n\n{prompt}",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data='voucher_menu')]])
    )
    return VOUCHER_GENERATE_VALUE

async def voucher_generate_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    try:
        value = int(text)
        if value <= 0:
            raise ValueError
    except:
        await update.message.reply_text("❌ Masukkan angka yang valid!")
        return VOUCHER_GENERATE_VALUE
    
    context.user_data['voucher_value'] = value
    await show_user_limit_table(update, context)
    return VOUCHER_GENERATE_LIMIT

async def show_user_limit_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'selected_user_limit' not in context.user_data:
        context.user_data['selected_user_limit'] = []
    
    selected = context.user_data['selected_user_limit']
    total_users = 0
    if selected:
        users_str = ''.join(map(str, selected))
        total_users = int(users_str)
    
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data='ulimit_1'),
            InlineKeyboardButton("2️⃣", callback_data='ulimit_2'),
            InlineKeyboardButton("3️⃣", callback_data='ulimit_3'),
            InlineKeyboardButton("4️⃣", callback_data='ulimit_4'),
            InlineKeyboardButton("5️⃣", callback_data='ulimit_5'),
        ],
        [
            InlineKeyboardButton("6️⃣", callback_data='ulimit_6'),
            InlineKeyboardButton("7️⃣", callback_data='ulimit_7'),
            InlineKeyboardButton("8️⃣", callback_data='ulimit_8'),
            InlineKeyboardButton("9️⃣", callback_data='ulimit_9'),
            InlineKeyboardButton("0️⃣", callback_data='ulimit_0'),
        ],
        [
            InlineKeyboardButton("✅ Konfirmasi", callback_data='ulimit_confirm'),
            InlineKeyboardButton("🔄 Reset", callback_data='ulimit_reset'),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data='voucher_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    selected_text = "• Belum ada" if not selected else ' '.join(map(str, selected))
    
    await update.message.reply_text(
        f"👥 <b>ATUR JUMLAH USER</b>\n\n"
        f"📌 Angka dipilih: {selected_text}\n"
        f"👥 Total user: <b>{total_users} user</b>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def user_limit_number_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    num = int(query.data.replace('ulimit_', ''))
    
    if 'selected_user_limit' not in context.user_data:
        context.user_data['selected_user_limit'] = []
    
    if len(context.user_data['selected_user_limit']) < 3:
        context.user_data['selected_user_limit'].append(num)
    else:
        await query.answer("Maksimal 3 digit!", show_alert=True)
        return
    
    selected = context.user_data['selected_user_limit']
    users_str = ''.join(map(str, selected))
    total_users = int(users_str)
    
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data='ulimit_1'),
            InlineKeyboardButton("2️⃣", callback_data='ulimit_2'),
            InlineKeyboardButton("3️⃣", callback_data='ulimit_3'),
            InlineKeyboardButton("4️⃣", callback_data='ulimit_4'),
            InlineKeyboardButton("5️⃣", callback_data='ulimit_5'),
        ],
        [
            InlineKeyboardButton("6️⃣", callback_data='ulimit_6'),
            InlineKeyboardButton("7️⃣", callback_data='ulimit_7'),
            InlineKeyboardButton("8️⃣", callback_data='ulimit_8'),
            InlineKeyboardButton("9️⃣", callback_data='ulimit_9'),
            InlineKeyboardButton("0️⃣", callback_data='ulimit_0'),
        ],
        [
            InlineKeyboardButton("✅ Konfirmasi", callback_data='ulimit_confirm'),
            InlineKeyboardButton("🔄 Reset", callback_data='ulimit_reset'),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data='voucher_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"👥 <b>ATUR JUMLAH USER</b>\n\n"
        f"📌 Angka dipilih: {' '.join(map(str, selected))}\n"
        f"👥 Total user: <b>{total_users} user</b>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def user_limit_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    selected = context.user_data.get('selected_user_limit', [])
    
    if not selected:
        await query.answer("Pilih jumlah user dulu!", show_alert=True)
        return
    
    users_str = ''.join(map(str, selected))
    max_users = int(users_str)
    
    if max_users < 1:
        await query.answer("Minimal 1 user!", show_alert=True)
        return
    
    context.user_data['voucher_max_users'] = max_users
    
    keyboard = [
        [InlineKeyboardButton("7 Hari", callback_data='expire_7'), InlineKeyboardButton("30 Hari", callback_data='expire_30')],
        [InlineKeyboardButton("90 Hari", callback_data='expire_90'), InlineKeyboardButton("1 Tahun", callback_data='expire_365')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='voucher_generate')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⏰ <b>ATUR MASA BERLAKU</b>\n\n👥 Maksimal user: {max_users} orang",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return VOUCHER_GENERATE_EXPIRE
    
async def voucher_generate_expire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    expire_days = int(query.data.replace('expire_', ''))
    
    v_type = context.user_data.get('voucher_type')
    value = context.user_data.get('voucher_value')
    max_users = context.user_data.get('voucher_max_users')
    
    code = create_voucher(
        created_by=update.effective_user.id,
        voucher_type=v_type,
        value=value,
        days=value if v_type != 'saldo' else 0,
        max_users=max_users,
        expires_days=expire_days,
        min_balance=0
    )
    
    await query.edit_message_text(
        f"✅ <b>VOUCHER BERHASIL!</b>\n\n"
        f"🎟️ Kode: <code>{code}</code>\n"
        f"📦 Tipe: {v_type.upper()}\n"
        f"💰 Nilai: {value} {'hari' if v_type != 'saldo' else 'rupiah'}\n"
        f"👥 Maks user: {max_users} orang\n"
        f"⏰ Berlaku: {expire_days} hari",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Menu Utama", callback_data='kembali_ke_menu')
        ]])
    )
    
    context.user_data.clear()
    return PROTOKOL

async def user_limit_reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['selected_user_limit'] = []
    
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data='ulimit_1'),
            InlineKeyboardButton("2️⃣", callback_data='ulimit_2'),
            InlineKeyboardButton("3️⃣", callback_data='ulimit_3'),
            InlineKeyboardButton("4️⃣", callback_data='ulimit_4'),
            InlineKeyboardButton("5️⃣", callback_data='ulimit_5'),
        ],
        [
            InlineKeyboardButton("6️⃣", callback_data='ulimit_6'),
            InlineKeyboardButton("7️⃣", callback_data='ulimit_7'),
            InlineKeyboardButton("8️⃣", callback_data='ulimit_8'),
            InlineKeyboardButton("9️⃣", callback_data='ulimit_9'),
            InlineKeyboardButton("0️⃣", callback_data='ulimit_0'),
        ],
        [
            InlineKeyboardButton("✅ Konfirmasi", callback_data='ulimit_confirm'),
            InlineKeyboardButton("🔄 Reset", callback_data='ulimit_reset'),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data='voucher_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"👥 <b>ATUR JUMLAH USER</b>\n\n"
        f"📌 Angka dipilih: • Belum ada\n"
        f"👥 Total user: <b>0 user</b>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    return VOUCHER_GENERATE_LIMIT

async def voucher_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "🎟️ <b>REDEEM VOUCHER</b>\n\nMasukkan kode voucher:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data='voucher_menu')]])
        )
    else:
        await update.message.reply_text("🎟️ <b>REDEEM VOUCHER</b>\n\nMasukkan kode voucher:", parse_mode='HTML')
    
    return VOUCHER_REDEEM

async def voucher_redeem_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.strip().upper()
    
    result = use_voucher(code, user_id)
    
    if not result['success']:
        await update.message.reply_text(result['message'])
        return ConversationHandler.END
    
    if result['type'] == 'saldo':
        update_balance(user_id, result['value'], f"Redeem voucher {code}")
        await update.message.reply_text(
            f"✅ <b>REDEEM BERHASIL!</b>\n\n"
            f"💰 Saldo: +Rp {result['value']:,}\n"
            f"💵 Saldo sekarang: Rp {get_balance(user_id):,}",
            parse_mode='HTML'
        )
    
    elif result['type'] in ['ssh', 'vmess', 'vless', 'trojan']:
    
        can_create, stock_msg = check_stock_available()
        if not can_create:
            await update.message.reply_text(stock_msg, parse_mode='HTML')
            return ConversationHandler.END
      
        context.user_data['selected_protocol'] = result['type']
        context.user_data['days'] = result['value']
        context.user_data['voucher_redeem'] = True
        
        await update.message.reply_text(
            f"✅ <b>VOUCHER VALID!</b>\n\n"
            f"Anda akan mendapat akun {result['type'].upper()} {result['value']} hari.\n\n"
            f"📝 Masukkan <b>Username</b>:",
            parse_mode='HTML'
        )
        return INPUT_USERNAME
    
    await start(update, context)
    return PROTOKOL

async def voucher_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != OWNER_ID:
        await query.edit_message_text("❌ Hanya owner yang bisa melihat daftar voucher!")
        return VOUCHER_MENU
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    now = datetime.now().isoformat()
    c.execute('''SELECT code, type, value, days, used_count, max_uses, created_at, expires_at 
                 FROM vouchers WHERE is_active = 1 AND expires_at > ? ORDER BY created_at DESC LIMIT 10''', (now,))
    vouchers = c.fetchall()
    conn.close()
    
    if not vouchers:
        await query.edit_message_text("📋 Belum ada voucher aktif.")
        return VOUCHER_MENU
    
    text = "📋 <b>DAFTAR VOUCHER AKTIF</b>\n\n"
    for v in vouchers:
        code, v_type, value, days, used, max_uses, created, expires = v
        exp_date = expires[:10]
        text += f"✅ <code>{code}</code> | {v_type} | {used}/{max_uses} user | Exp: {exp_date}\n\n"
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data='voucher_menu')]]))

# ==========================================
# HANDLER RESET SALDO
# ==========================================
async def reset_saldo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != OWNER_ID:
        await query.edit_message_text("❌ Hanya owner yang bisa akses fitur ini!")
        return VOUCHER_MENU
    
    keyboard = [
        [InlineKeyboardButton("💰 Reset Saldo User", callback_data='reset_saldo_input')],
        [InlineKeyboardButton("📋 Lihat Semua Saldo", callback_data='reset_saldo_list')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='voucher_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("⚙️ <b>MANAJEMEN SALDO USER</b>\n\nPilih opsi di bawah:", parse_mode='HTML', reply_markup=reply_markup)
    return RESET_SALDO_MENU

async def reset_saldo_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "💰 <b>RESET SALDO USER</b>\n\nMasukkan User ID yang ingin direset:\nContoh: <code>1668998643</code>\n\nAtau ketik <code>ALL</code> untuk reset semua user.",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data='reset_saldo_menu')]])
    )
    return RESET_SALDO_INPUT

async def reset_saldo_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya owner yang bisa akses fitur ini!")
        return ConversationHandler.END
    
    text = update.message.text.strip()
    
    if text.upper() == 'ALL':
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE saldo SET balance = 0")
        c.execute("DELETE FROM transaksi WHERE type = 'debit' AND description LIKE 'Beli akun%'")
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ <b>SEMUA SALDO USER TELAH DIRESET!</b>")
    else:
        try:
            user_id = int(text)
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT balance FROM saldo WHERE user_id = ?", (user_id,))
            result = c.fetchone()
            
            if result:
                old_balance = result[0]
                c.execute("UPDATE saldo SET balance = 0 WHERE user_id = ?", (user_id,))
                conn.commit()
                conn.close()
                await update.message.reply_text(
                    f"✅ <b>SALDO USER DIRESET!</b>\n\n"
                    f"👤 User ID: <code>{user_id}</code>\n"
                    f"💰 Saldo lama: Rp {old_balance:,}\n"
                    f"💰 Saldo baru: Rp 0",
                    parse_mode='HTML'
                )
            else:
                conn.close()
                await update.message.reply_text(f"❌ User ID <code>{user_id}</code> tidak ditemukan!")
        except ValueError:
            await update.message.reply_text("❌ Masukkan User ID yang valid!")
            return RESET_SALDO_INPUT
    
    await start(update, context)
    return PROTOKOL

async def reset_saldo_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT user_id, balance FROM saldo WHERE balance > 0 ORDER BY balance DESC LIMIT 20''')
    users = c.fetchall()
    conn.close()
    
    if not users:
        await query.edit_message_text("📋 Belum ada user dengan saldo.")
        return RESET_SALDO_MENU
    
    text = "📋 <b>DAFTAR SALDO USER</b>\n\n"
    for user_id, balance in users:
        text += f"👤 <code>{user_id}</code> : Rp {balance:,}\n"
    
    keyboard = [
        [InlineKeyboardButton("💰 Reset Semua", callback_data='reset_saldo_all_confirm')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='reset_saldo_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
    return RESET_SALDO_MENU

async def reset_saldo_all_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("✅ Ya, Reset Semua", callback_data='reset_saldo_all_yes'),
         InlineKeyboardButton("❌ Tidak", callback_data='reset_saldo_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚠️ <b>PERINGATAN!</b>\n\nAnda akan mereset SALDO SEMUA USER menjadi 0.\nYakin ingin melanjutkan?",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    return RESET_SALDO_MENU

async def reset_saldo_all_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE saldo SET balance = 0")
    c.execute("DELETE FROM transaksi WHERE type = 'debit' AND description LIKE 'Beli akun%'")
    conn.commit()
    conn.close()
    
    await query.edit_message_text("✅ <b>SEMUA SALDO USER TELAH DIRESET!</b>")
    await start(update, context)
    return PROTOKOL

# ==========================================
# HANDLER STOK UNTUK OWNER
# ==========================================
async def stock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu manajemen stok - hanya untuk owner"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != OWNER_ID:
        await query.edit_message_text("❌ Hanya owner yang bisa akses fitur ini!")
        return VOUCHER_MENU
    
    stock_info = get_global_stock_info()
    
    text = (
        f"📦 <b>MANAJEMEN STOK AKUN</b>\n\n"
        f"📊 Status Saat Ini:\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 Maksimal Stok: <b>{stock_info['max']}</b> akun\n"
        f"📉 Stok Terpakai: <b>{stock_info['current']}</b> akun\n"
        f"✅ Stok Tersedia: <b>{stock_info['available']}</b> akun\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ Stok ini berlaku untuk SEMUA protokol\n"
        f"(SSH, VMess, VLess, Trojan)\n\n"
        f"Pilih aksi di bawah:"
    )
    
    keyboard = [
        [InlineKeyboardButton("➕ Tambah Stok", callback_data='stock_add')],
        [InlineKeyboardButton("➖ Kurangi Stok", callback_data='stock_remove')],
        [InlineKeyboardButton("🔢 Set Stok Manual", callback_data='stock_set')],
        [InlineKeyboardButton("🔄 Update & Hitung Ulang", callback_data='stock_refresh')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='voucher_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
    return STOCK_MENU

async def stock_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tambah stok"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➕ <b>TAMBAH STOK</b>\n\n"
        "Masukkan jumlah stok yang ingin ditambahkan:\n"
        "Contoh: <code>10</code> (menambah 10 stok)\n\n"
        "Ketik /batal untuk membatalkan.",
        parse_mode='HTML'
    )
    return STOCK_INPUT_ADD

async def stock_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kurangi stok"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➖ <b>KURANGI STOK</b>\n\n"
        "Masukkan jumlah stok yang ingin dikurangi:\n"
        "Contoh: <code>5</code> (mengurangi 5 stok)\n\n"
        "Ketik /batal untuk membatalkan.",
        parse_mode='HTML'
    )
    return STOCK_INPUT_REMOVE

async def stock_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set stok manual"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔢 <b>SET STOK MANUAL</b>\n\n"
        "Masukkan jumlah MAKSIMAL stok yang diinginkan:\n"
        "Contoh: <code>200</code> (mengatur maksimal stok menjadi 200)\n\n"
        "Ketik /batal untuk membatalkan.",
        parse_mode='HTML'
    )
    return STOCK_INPUT_SET

async def stock_process_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proses tambah stok"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya owner yang bisa akses fitur ini!")
        return ConversationHandler.END
    
    try:
        amount = int(update.message.text.strip())
        if amount <= 0:
            await update.message.reply_text("❌ Masukkan angka positif!")
            return STOCK_INPUT_ADD
        
        current_max = get_max_stock()
        new_max = current_max + amount
        update_max_stock(new_max)
        
        stock_info = get_global_stock_info()
        await update.message.reply_text(
            f"✅ <b>STOK BERHASIL DITAMBAH!</b>\n\n"
            f"➕ Ditambah: +{amount} akun\n"
            f"📈 Maksimal Stok Baru: <b>{new_max}</b> akun\n"
            f"✅ Stok Tersedia: <b>{stock_info['available']}</b> akun",
            parse_mode='HTML'
        )
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka yang valid!")
        return STOCK_INPUT_ADD
    
    await stock_menu(update, context)
    return STOCK_MENU

async def stock_process_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proses kurangi stok"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya owner yang bisa akses fitur ini!")
        return ConversationHandler.END
    
    try:
        amount = int(update.message.text.strip())
        if amount <= 0:
            await update.message.reply_text("❌ Masukkan angka positif!")
            return STOCK_INPUT_REMOVE
        
        current_max = get_max_stock()
        new_max = current_max - amount
        
        if new_max < 0:
            await update.message.reply_text("❌ Stok tidak bisa kurang dari 0!")
            return STOCK_INPUT_REMOVE
        
        update_max_stock(new_max)
        
        stock_info = get_global_stock_info()
        await update.message.reply_text(
            f"✅ <b>STOK BERHASIL DIKURANGI!</b>\n\n"
            f"➖ Dikurangi: -{amount} akun\n"
            f"📈 Maksimal Stok Baru: <b>{new_max}</b> akun\n"
            f"✅ Stok Tersedia: <b>{stock_info['available']}</b> akun",
            parse_mode='HTML'
        )
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka yang valid!")
        return STOCK_INPUT_REMOVE
    
    await stock_menu(update, context)
    return STOCK_MENU

async def stock_process_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proses set stok manual"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya owner yang bisa akses fitur ini!")
        return ConversationHandler.END
    
    try:
        new_max = int(update.message.text.strip())
        if new_max < 0:
            await update.message.reply_text("❌ Stok tidak bisa kurang dari 0!")
            return STOCK_INPUT_SET
        
        update_max_stock(new_max)
        
        stock_info = get_global_stock_info()
        await update.message.reply_text(
            f"✅ <b>STOK BERHASIL DIUBAH!</b>\n\n"
            f"📈 Maksimal Stok Baru: <b>{new_max}</b> akun\n"
            f"📉 Stok Terpakai: <b>{stock_info['current']}</b> akun\n"
            f"✅ Stok Tersedia: <b>{stock_info['available']}</b> akun",
            parse_mode='HTML'
        )
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka yang valid!")
        return STOCK_INPUT_SET
    
    await stock_menu(update, context)
    return STOCK_MENU

async def stock_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh/update stok (hitung ulang akun yang ada)"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != OWNER_ID:
        await query.edit_message_text("❌ Hanya owner yang bisa akses fitur ini!")
        return VOUCHER_MENU
    
    current = count_all_accounts()
    max_stock = get_max_stock()
    
    text = (
        f"🔄 <b>STOK TELAH DIREFRESH!</b>\n\n"
        f"📊 Total akun terdeteksi: <b>{current}</b> akun\n"
        f"📈 Maksimal Stok: <b>{max_stock}</b> akun\n"
        f"✅ Stok Tersedia: <b>{max_stock - current}</b> akun"
    )
    
    await query.edit_message_text(text, parse_mode='HTML')
    await stock_menu(update, context)
    return STOCK_MENU

# ==========================================
# HANDLER KEMBALI KE MENU & BATAL
# ==========================================
async def kembali_ke_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        context.user_data.clear()
        await start(update, context)
        return PROTOKOL
    except Exception as e:
        print(f"Error: {e}")
        return PROTOKOL

async def batal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        context.user_data.clear()
        await query.edit_message_text("❌ Dibatalkan.")
        await start(update, context)
        return PROTOKOL
    except:
        return PROTOKOL

async def buat_lagi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await start(update, context)
    return PROTOKOL

async def input_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    protocol = context.user_data.get('selected_protocol')
    
    print(f"🔍 [input_username] username={username}, protocol={protocol}")  # DEBUG
    
    if not validate_username(username):
        await update.message.reply_text(
            "❌ Username tidak valid! (hanya huruf, angka, underscore)\n"
            "Contoh: <code>myname_90</code>",
            parse_mode='HTML'
        )
        return INPUT_USERNAME
    
    context.user_data['username'] = username
    print(f"✅ [input_username] username disimpan: {username}")
    
    # CEK APAKAH DARI VOUCHER REDEEM
    if context.user_data.get('voucher_redeem'):
        print("🔍 [input_username] Voucher redeem mode, skip balance")
        await process_create_account(update, context, skip_balance=True)
        return ConversationHandler.END
    
    # LANJUTKAN KE PASSWORD ATAU DAYS
    if protocol == 'ssh':
        await update.message.reply_text(
            f"✅ Username: <code>{username}</code>\n\n"
            f"📝 Langkah 2/3: Masukkan <b>Password</b>\n"
            f"• Minimal 3 karakter\n"
            f"• Tidak boleh ada spasi\n"
            f"• Contoh: <code>mypass123</code>",
            parse_mode='HTML'
        )
        return INPUT_PASSWORD  # ← PASTIKAN RETURN INI
    else:
        # UNTUK VMESS, VLESS, TROJAN - LANGSUNG KE DAYS
        print(f"🔍 [input_username] Protocol {protocol}, langsung ke days")
        context.user_data['selected_numbers'] = []
        await show_days_table(update, context)
        return INPUT_DAYS  # ← PASTIKAN RETURN INI

async def input_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    protocol = context.user_data.get('selected_protocol')
    username = context.user_data.get('username')
    
    print(f"🔍 [input_password] password={password}, protocol={protocol}, username={username}")  # DEBUG
    
    if len(password) < 3:
        await update.message.reply_text(
            "❌ Password minimal 3 karakter!\n"
            "Silakan masukkan password yang lebih panjang.",
            parse_mode='HTML'
        )
        return INPUT_PASSWORD
    
    if ' ' in password:
        await update.message.reply_text(
            "❌ Password tidak boleh mengandung spasi!\n"
            "Silakan masukkan password tanpa spasi.",
            parse_mode='HTML'
        )
        return INPUT_PASSWORD
    
    context.user_data['password'] = password
    print(f"✅ [input_password] password disimpan: {password}")
    
    await show_days_table(update, context)
    return INPUT_DAYS  # ← PASTIKAN RETURN INI

async def show_days_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan tabel pemilihan hari"""
    if 'selected_numbers' not in context.user_data:
        context.user_data['selected_numbers'] = []
    
    selected = context.user_data['selected_numbers']
    protocol = context.user_data.get('selected_protocol')
    username = context.user_data.get('username')
    
    print(f"🔍 [show_days_table] protocol={protocol}, username={username}, selected={selected}")  # DEBUG
    
    price = PRICES.get(protocol, 500)
    
    total_days = 0
    total_price = 0
    if selected:
        days_str = ''.join(map(str, selected))
        total_days = int(days_str)
        total_price = price * total_days
    
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data='num_1'),
            InlineKeyboardButton("2️⃣", callback_data='num_2'),
            InlineKeyboardButton("3️⃣", callback_data='num_3'),
            InlineKeyboardButton("4️⃣", callback_data='num_4'),
            InlineKeyboardButton("5️⃣", callback_data='num_5'),
        ],
        [
            InlineKeyboardButton("6️⃣", callback_data='num_6'),
            InlineKeyboardButton("7️⃣", callback_data='num_7'),
            InlineKeyboardButton("8️⃣", callback_data='num_8'),
            InlineKeyboardButton("9️⃣", callback_data='num_9'),
            InlineKeyboardButton("0️⃣", callback_data='num_0'),
        ],
        [
            InlineKeyboardButton("✅ Konfirmasi", callback_data='days_confirm'),
            InlineKeyboardButton("🔄 Reset", callback_data='days_reset'),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data='proto_batal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    selected_text = "• Belum ada" if not selected else ' '.join(map(str, selected))
    step = "Langkah 3/3" if protocol == 'ssh' else "Langkah 2/2"
    
    # KIRIM PESAN DENGAN REPLY MARKUP
    await update.message.reply_text(
        f"📝 <b>{step}: Pilih Masa Aktif</b>\n\n"
        f"👤 Username  : <code>{username}</code>\n"
        f"📌 Angka     : {selected_text}\n"
        f"📊 Total     : <b>{total_days} hari</b>\n"
        f"💰 Harga     : <b>Rp {total_price:,}</b>\n\n"
        f"Tekan angka untuk memilih durasi (maks 3 digit).",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def days_number_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    num = int(query.data.replace('num_', ''))
    
    if 'selected_numbers' not in context.user_data:
        context.user_data['selected_numbers'] = []
    
    if len(context.user_data['selected_numbers']) < 3:
        context.user_data['selected_numbers'].append(num)
    else:
        await query.answer("Maksimal 3 digit!", show_alert=True)
        return
    
    selected = context.user_data['selected_numbers']
    protocol = context.user_data.get('selected_protocol')
    username = context.user_data.get('username')
    selected_text = "• Belum ada" if not selected else ' '.join(map(str, selected))
    step = "Langkah 3/3" if protocol == 'ssh' else "Langkah 2/2"
    price = PRICES.get(protocol, 500)
    
    days_str = ''.join(map(str, selected))
    total_days = int(days_str)
    total_price = price * total_days
    
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data='num_1'),
            InlineKeyboardButton("2️⃣", callback_data='num_2'),
            InlineKeyboardButton("3️⃣", callback_data='num_3'),
            InlineKeyboardButton("4️⃣", callback_data='num_4'),
            InlineKeyboardButton("5️⃣", callback_data='num_5'),
        ],
        [
            InlineKeyboardButton("6️⃣", callback_data='num_6'),
            InlineKeyboardButton("7️⃣", callback_data='num_7'),
            InlineKeyboardButton("8️⃣", callback_data='num_8'),
            InlineKeyboardButton("9️⃣", callback_data='num_9'),
            InlineKeyboardButton("0️⃣", callback_data='num_0'),
        ],
        [
            InlineKeyboardButton("✅ Konfirmasi", callback_data='days_confirm'),
        ],
        [
            InlineKeyboardButton("🔄 Reset", callback_data='days_reset'),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data='proto_batal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 <b>{step}: Pilih Masa Aktif</b>\n\n"
        f"👤 Username  : <code>{username}</code>\n"
        f"📌 Angka     : {selected_text}\n"
        f"📊 Total     : <b>{total_days} hari</b>\n"
        f"💰 Harga     : <b>Rp {total_price:,}</b>\n\n"
        f"Tekan angka untuk memilih durasi (maks 3 digit).",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def days_reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['selected_numbers'] = []
    
    protocol = context.user_data.get('selected_protocol')
    
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data='num_1'),
            InlineKeyboardButton("2️⃣", callback_data='num_2'),
            InlineKeyboardButton("3️⃣", callback_data='num_3'),
            InlineKeyboardButton("4️⃣", callback_data='num_4'),
            InlineKeyboardButton("5️⃣", callback_data='num_5'),
        ],
        [
            InlineKeyboardButton("6️⃣", callback_data='num_6'),
            InlineKeyboardButton("7️⃣", callback_data='num_7'),
            InlineKeyboardButton("8️⃣", callback_data='num_8'),
            InlineKeyboardButton("9️⃣", callback_data='num_9'),
            InlineKeyboardButton("0️⃣", callback_data='num_0'),
        ],
        [
            InlineKeyboardButton("✅ Konfirmasi", callback_data='days_confirm'),
        ],
        [
            InlineKeyboardButton("🔄 Reset", callback_data='days_reset'),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data='proto_batal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    protocol = context.user_data.get('selected_protocol')
    username = context.user_data.get('username')
    step = "Langkah 3/3" if protocol == 'ssh' else "Langkah 2/2"

    await query.edit_message_text(
        f"📝 <b>Pilih Masa Aktif</b>\n\n"
        f"👤 Username  : <code>{username}</code>\n"
        f"📌 Angka     : • Belum ada\n"
        f"📊 Total     : <b>0 hari</b>\n"
        f"💰 Harga     : <b>Rp 0</b>\n\n"
        f"Tekan angka untuk memilih durasi (maks 3 digit).",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def days_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    selected = context.user_data.get('selected_numbers', [])
    
    if not selected:
        await query.answer("Pilih angka dulu!", show_alert=True)
        return
    
    days_str = ''.join(map(str, selected))
    days = int(days_str)
    
    if days < 1 or days > 365:
        await query.answer("Maksimal 365 hari!", show_alert=True)
        return
    
    context.user_data['days'] = days
    print(f"✅ [days_confirm] days={days}, selected={selected}")  # DEBUG
    
    await process_create_account(update, context, skip_balance=False)
    return ConversationHandler.END  # ← PASTIKAN RETURN INI

# ==========================================
# COMMAND HANDLER
# ==========================================
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status_text = "<b>📊 STATUS BOT</b>\n\n"
    for proto, script in SCRIPTS.items():
        if os.path.exists(script):
            status_text += f"✅ {proto.upper()}: OK\n"
        else:
            status_text += f"❌ {proto.upper()}: TIDAK DITEMUKAN\n"
    await update.message.reply_text(status_text, parse_mode='HTML')

async def saldo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = get_balance(user_id)
    await update.message.reply_text(f"💰 <b>SALDO ANDA</b>\n\nUser ID: <code>{user_id}</code>\nSaldo: <b>Rp {balance:,}</b>", parse_mode='HTML')

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /broadcast - kirim pesan ke semua user"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Hanya owner yang bisa menggunakan command ini!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 <b>CARA BROADCAST</b>\n\n"
            "Kirim pesan ke semua user:\n"
            "• <code>/broadcast pesan anda</code>\n\n"
            "Atau gunakan menu Broadcast di Voucher Menu.",
            parse_mode='HTML'
        )
        return
    
    message_text = ' '.join(context.args)
    users = get_all_users()
    
    if not users:
        await update.message.reply_text("❌ Belum ada user yang terdaftar!")
        return
    
    progress_msg = await update.message.reply_text(f"⏱️ Memulai broadcast ke {len(users)} user...")
    
    success_count = 0
    fail_count = 0
    
    for user_id, username, first_name in users:
        try:
            personalized_msg = message_text.replace("{name}", first_name or "User")
            personalized_msg = personalized_msg.replace("{username}", username or "User")
            
            await context.bot.send_message(
                chat_id=user_id,
                text=personalized_msg,
                parse_mode='HTML'
            )
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            fail_count += 1
            print(f"❌ Gagal kirim ke {user_id}: {e}")
    
    await progress_msg.edit_text(
        f"✅ <b>BROADCAST SELESAI!</b>\n\n"
        f"📊 Total user: {len(users)}\n"
        f"✅ Berhasil: {success_count}\n"
        f"❌ Gagal: {fail_count}",
        parse_mode='HTML'
    )

async def batal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Dibatalkan.")
    context.user_data.clear()
    return ConversationHandler.END

async def voucher_generate_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return PROTOKOL

async def voucher_generate_min_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return PROTOKOL

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # === TOPUP HANDLER - URUTAN HARUS! ===
    if data == 'topup_saldo':
        return await topup_saldo(update, context)
    
    if data.startswith('cek_status_'):
        return await cek_status_topup(update, context)
    
    if data.startswith('batal_topup_'):
        return await batal_topup(update, context)
    
    if data == 'batal_topup_custom':
        await query.edit_message_text("❌ Topup dibatalkan.")
        await start(update, context)
        return PROTOKOL
    
    # === HANDLER LAINNYA ===
    if data == 'proto_batal':
        return await batal_callback(update, context)
    
    if data == 'cek_saldo':
        return await cek_saldo(update, context)
    
    if data == 'kembali_ke_menu':
        return await kembali_ke_menu(update, context)
    
    if data == 'voucher_menu':
        return await voucher_menu(update, context)
    
    if data == 'voucher_redeem':
        return await voucher_redeem(update, context)
    
    if data == 'voucher_generate':
        return await voucher_generate(update, context)
    
    if data == 'voucher_list':
        return await voucher_list(update, context)
    
    if data == 'reset_saldo_menu':
        return await reset_saldo_menu(update, context)
    
    if data == 'reset_saldo_input':
        return await reset_saldo_input(update, context)
    
    if data == 'reset_saldo_list':
        return await reset_saldo_list(update, context)
    
    if data == 'reset_saldo_all_confirm':
        return await reset_saldo_all_confirm(update, context)
    
    if data == 'reset_saldo_all_yes':
        return await reset_saldo_all_yes(update, context)
    
    if data == 'renew_menu':
        return await renew_account_menu(update, context)
    
    if data.startswith('renew_proto_'):
        return await renew_select_protocol(update, context)
    
    if data == 'renew_confirm':
        return await renew_confirm_callback(update, context)
    
    if data.startswith('rnum_'):
        if data == 'rnum_reset':
            return await renew_reset_callback(update, context)
        else:
            return await renew_number_callback(update, context)
    
    if data.startswith('gen_'):
        return await voucher_generate_type(update, context)
    
    if data.startswith('ulimit_'):
        if data == 'ulimit_confirm':
            return await user_limit_confirm_callback(update, context)
        elif data == 'ulimit_reset':
            return await user_limit_reset_callback(update, context)
        else:
            return await user_limit_number_callback(update, context)
    
    if data.startswith('expire_'):
        return await voucher_generate_expire(update, context)
    
    if data == 'finish_voucher':
        return await voucher_generate_finish(update, context)
    
    if data.startswith('auto_trial_'):
        return await auto_trial(update, context)
    
    if data.startswith('auto_proto_'):
        return await auto_renew_proto(update, context)
    
    if data == 'auto_renew_menu':
        return await auto_renew_menu(update, context)
    
    if data == 'auto_renew_on':
        return await auto_renew_on(update, context)
    
    if data == 'auto_renew_off':
        return await auto_renew_off(update, context)
    
    if data == 'trial_menu':
        return await trial_menu(update, context)
    
    if data == 'buat_lagi':
        return await buat_lagi(update, context)
    
    if data == 'broadcast_menu':
        return await broadcast_menu(update, context)
    
    if data == 'broadcast_text':
        return await broadcast_text_start(update, context)
    
    if data == 'broadcast_photo':
        return await broadcast_photo_start(update, context)
    
    if data == 'broadcast_list':
        return await broadcast_list_users(update, context)
    
    if data == 'edit_harga_menu':
        return await edit_harga_menu(update, context)
    
    if data == 'sub_menu_lainnya':
        return await sub_menu_lainnya(update, context)
    
    if data == 'stock_menu':
        return await stock_menu(update, context)
    
    if data == 'stock_add':
        return await stock_add(update, context)
    
    if data == 'stock_remove':
        return await stock_remove(update, context)
    
    if data == 'stock_set':
        return await stock_set(update, context)
    
    if data == 'stock_refresh':
        return await stock_refresh(update, context)
    if data == 'vpn_menu':
        return await vpn_menu(update, context)
    
    if data.startswith('edit_harga_'):
        return await edit_harga_pilih_protokol(update, context)
    
    if data.startswith('proto_'):
        protocol = data.replace('proto_', '')
        context.user_data['selected_protocol'] = protocol
        
        proto_names = {
            'ssh': '🚀 SSH',
            'vmess': '📡 VMess',
            'vless': '📡 VLess',
            'trojan': '🛡️ Trojan'
        }
        
        keyboard = [[InlineKeyboardButton("❌ Batal", callback_data='proto_batal')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        step_text = "Langkah 1/3" if protocol == 'ssh' else "Langkah 1/2"
        detail = "• Password isi bebas nanti" if protocol == 'ssh' else "• Password otomatis"
        
        await query.edit_message_text(
            f"✅ <b>{proto_names[protocol]}</b>\n"
            f"💰 Harga: Rp {PRICES[protocol]:,}/hari\n\n"
            f"📝 {step_text}: Masukkan <b>Username</b>\n"
            f"• Hanya huruf, angka, underscore\n"
            f"• Contoh: <code>myname_90</code>\n"
            f"{detail}",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
        return INPUT_USERNAME
    
    return PROTOKOL

# ==========================================
# MAIN FUNCTION
# ==========================================
def main():
    print("=" * 60)
    print("🚀 BOT TUNNELING - COMPLETE VERSION")
    print("📦 Fitur: Create, Renew, Trial, Voucher, Auto Renew,")
    print("         Topup QRIS Otomatis (Pakasir), Log Channel,")
    print("         Broadcast, Region, Stock Management")
    print("=" * 60)
    
    # CEK KONFIGURASI
    print(f"📋 Token Bot: {TOKEN[:10]}...{TOKEN[-5:]}")
    print(f"👤 Owner ID: {OWNER_ID}")
    print(f"📢 Channel ID: {CHANNEL_ID}")
    print(f"💰 Harga SSH: Rp {PRICES['ssh']:,}/hari")
    print(f"💰 Harga VMess: Rp {PRICES['vmess']:,}/hari")
    print(f"💰 Harga VLess: Rp {PRICES['vless']:,}/hari")
    print(f"💰 Harga Trojan: Rp {PRICES['trojan']:,}/hari")
    print("=" * 60)
    
    # INISIALISASI DATABASE
    try:
        init_db()
        print("✅ Database saldo initialized")
    except Exception as e:
        print(f"❌ Gagal init database saldo: {e}")
    
    try:
        init_voucher_db()
        print("✅ Database voucher initialized")
    except Exception as e:
        print(f"❌ Gagal init database voucher: {e}")
    
    try:
        init_trial_db()
        print("✅ Database trial initialized")
    except Exception as e:
        print(f"❌ Gagal init database trial: {e}")
    
    try:
        init_auto_renew_db()
        print("✅ Database auto renew initialized")
    except Exception as e:
        print(f"❌ Gagal init database auto renew: {e}")
    
    try:
        init_user_db()
        print("✅ Database user initialized")
    except Exception as e:
        print(f"❌ Gagal init database user: {e}")
    
    try:
        init_stock_db()
        print("✅ Database stok initialized")
    except Exception as e:
        print(f"❌ Gagal init database stok: {e}")
    
    try:
        init_log_file()
        print("✅ Log file initialized")
    except Exception as e:
        print(f"❌ Gagal init log file: {e}")
    
    # BUAT DIREKTORI
    try:
        os.makedirs("/etc/conf/topup_requests", exist_ok=True)
        print("✅ Direktori topup requests siap")
    except Exception as e:
        print(f"⚠️ Gagal buat direktori topup: {e}")
    
    # BUAT FILE VISITOR
    try:
        visitor_file = "/etc/conf/visitors.txt"
        if not os.path.exists(visitor_file):
            with open(visitor_file, 'w') as f:
                f.write("0")
            print("✅ File visitor dibuat")
    except Exception as e:
        print(f"⚠️ Gagal buat file visitor: {e}")
    
    # CEK QRIS IMAGE
    if os.path.exists(QRIS_IMAGE_PATH):
        print(f"✅ QRIS Image ditemukan: {QRIS_IMAGE_PATH}")
    else:
        print(f"⚠️ QRIS Image tidak ditemukan (tidak dipakai untuk Pakasir)")
    
    print("=" * 60)
    
    # BUILD APP
    try:
        app = Application.builder().token(TOKEN).build()
        print("✅ Application built")
    except Exception as e:
        print(f"❌ Gagal build application: {e}")
        return
    
    # INIT PAKASIR
    try:
        pakasir = init_pakasir(app.bot)
        if pakasir:
            print("✅ Pakasir Payment Gateway initialized")
            print(f"   - Merchant ID: {pakasir.client.merchant_id}")
            print(f"   - Base URL: {pakasir.client.base_url}")
            print(f"   - Polling Interval: {pakasir.client.polling_interval}s")
            print(f"   - Timeout: {pakasir.client.timeout_minutes} menit")
        else:
            print("⚠️ Pakasir Payment Gateway gagal diinisialisasi")
    except Exception as e:
        print(f"❌ Gagal init Pakasir: {e}")
        print("⚠️ Fitur topup otomatis mungkin tidak berjalan")
    
    # ERROR HANDLER
    app.add_error_handler(error_handler)
    print("✅ Error handler added")
    
    # COMMAND HANDLER
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("saldo", saldo_command))
    app.add_handler(CommandHandler("batal", batal))
    print("✅ Command handlers added")
    
    # SUB MENU
	
    app.add_handler(CallbackQueryHandler(cek_status_topup, pattern='^cek_status_'))
    app.add_handler(CallbackQueryHandler(batal_topup, pattern='^batal_topup_'))
	
    app.add_handler(CallbackQueryHandler(sub_menu_lainnya, pattern='^sub_menu_lainnya$'))
    print("✅ Sub menu handler added")
    
    # CONVERSATION HANDLER
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
			CallbackQueryHandler(button_handler, pattern='^proto_'),
            CallbackQueryHandler(topup_saldo, pattern='^topup_saldo$'),
            CallbackQueryHandler(trial_menu, pattern='^trial_menu$'),
            CallbackQueryHandler(vpn_menu, pattern='^vpn_menu$'),
            CallbackQueryHandler(sub_menu_lainnya, pattern='^sub_menu_lainnya$'),
            CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
            CallbackQueryHandler(voucher_menu, pattern='^voucher_menu$'),
            CallbackQueryHandler(renew_account_menu, pattern='^renew_menu$'),
            CallbackQueryHandler(auto_renew_menu, pattern='^auto_renew_menu$'),
            CallbackQueryHandler(cek_saldo, pattern='^cek_saldo$'),
            CallbackQueryHandler(buat_lagi, pattern='^buat_lagi$'),
       ],
        states={
            PROTOKOL: [
                CallbackQueryHandler(button_handler, pattern='^proto_'),
                CallbackQueryHandler(button_handler, pattern='^cek_saldo$'),
                CallbackQueryHandler(button_handler, pattern='^topup_saldo$'),
                CallbackQueryHandler(button_handler, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(button_handler, pattern='^voucher_menu$'),
                CallbackQueryHandler(button_handler, pattern='^voucher_generate$'),
                CallbackQueryHandler(button_handler, pattern='^voucher_redeem$'),
                CallbackQueryHandler(button_handler, pattern='^voucher_list$'),
                CallbackQueryHandler(button_handler, pattern='^reset_saldo_menu$'),
                CallbackQueryHandler(button_handler, pattern='^reset_saldo_input$'),
                CallbackQueryHandler(button_handler, pattern='^reset_saldo_list$'),
                CallbackQueryHandler(button_handler, pattern='^reset_saldo_all_confirm$'),
                CallbackQueryHandler(button_handler, pattern='^reset_saldo_all_yes$'),
                CallbackQueryHandler(button_handler, pattern='^renew_menu$'),
                CallbackQueryHandler(button_handler, pattern='^renew_proto_'),
                CallbackQueryHandler(button_handler, pattern='^renew_'),
                CallbackQueryHandler(button_handler, pattern='^rnum_'),
                CallbackQueryHandler(button_handler, pattern='^gen_'),
                CallbackQueryHandler(button_handler, pattern='^ulimit_'),
                CallbackQueryHandler(button_handler, pattern='^expire_'),
                CallbackQueryHandler(button_handler, pattern='^finish_voucher$'),
                CallbackQueryHandler(button_handler, pattern='^auto_renew_menu$'),
                CallbackQueryHandler(button_handler, pattern='^auto_renew_on$'),
                CallbackQueryHandler(button_handler, pattern='^auto_renew_off$'),
                CallbackQueryHandler(button_handler, pattern='^trial_menu$'),
                CallbackQueryHandler(button_handler, pattern='^auto_trial_'),
                CallbackQueryHandler(button_handler, pattern='^broadcast_menu$'),
                CallbackQueryHandler(button_handler, pattern='^broadcast_text$'),
                CallbackQueryHandler(button_handler, pattern='^broadcast_photo$'),
                CallbackQueryHandler(button_handler, pattern='^broadcast_list$'),
                CallbackQueryHandler(button_handler, pattern='^edit_harga_menu$'),
                CallbackQueryHandler(button_handler, pattern='^edit_harga_'),
                CallbackQueryHandler(button_handler, pattern='^stock_menu$'),
                CallbackQueryHandler(button_handler, pattern='^stock_'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            INPUT_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_username),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
            ],
            
            INPUT_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_password),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
            ],
            
            INPUT_DAYS: [
                CallbackQueryHandler(days_number_callback, pattern='^num_'),
                CallbackQueryHandler(days_reset_callback, pattern='^days_reset$'),
                CallbackQueryHandler(days_confirm_callback, pattern='^days_confirm$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
            ],
            
            TOPUP_NOMINAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_nominal_topup),
                CallbackQueryHandler(batal_topup_custom, pattern='^batal_topup_custom$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
            ],
            
            TOPUP_BUKTI: [
                # Kosong - tidak dipakai lagi
            ],
            
            VOUCHER_MENU: [
                CallbackQueryHandler(button_handler, pattern='^voucher_generate$'),
                CallbackQueryHandler(button_handler, pattern='^voucher_redeem$'),
                CallbackQueryHandler(button_handler, pattern='^voucher_list$'),
                CallbackQueryHandler(button_handler, pattern='^reset_saldo_menu$'),
                CallbackQueryHandler(button_handler, pattern='^broadcast_menu$'),
                CallbackQueryHandler(button_handler, pattern='^edit_harga_menu$'),
                CallbackQueryHandler(button_handler, pattern='^stock_menu$'),
                CallbackQueryHandler(button_handler, pattern='^voucher_menu$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            VOUCHER_GENERATE: [
                CallbackQueryHandler(button_handler, pattern='^gen_'),
                CallbackQueryHandler(button_handler, pattern='^voucher_menu$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            VOUCHER_GENERATE_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, voucher_generate_value),
                CallbackQueryHandler(button_handler, pattern='^voucher_menu$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            VOUCHER_GENERATE_LIMIT: [
                CallbackQueryHandler(button_handler, pattern='^ulimit_'),
                CallbackQueryHandler(button_handler, pattern='^voucher_menu$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            VOUCHER_GENERATE_EXPIRE: [
                CallbackQueryHandler(button_handler, pattern='^expire_'),
                CallbackQueryHandler(button_handler, pattern='^finish_voucher$'),
                CallbackQueryHandler(button_handler, pattern='^voucher_generate$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            VOUCHER_GENERATE_MIN_BALANCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, voucher_generate_min_balance),
                CallbackQueryHandler(button_handler, pattern='^finish_voucher$'),
                CallbackQueryHandler(button_handler, pattern='^voucher_generate$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            RESET_SALDO_MENU: [
                CallbackQueryHandler(button_handler, pattern='^reset_saldo_input$'),
                CallbackQueryHandler(button_handler, pattern='^reset_saldo_list$'),
                CallbackQueryHandler(button_handler, pattern='^reset_saldo_all_confirm$'),
                CallbackQueryHandler(button_handler, pattern='^reset_saldo_all_yes$'),
                CallbackQueryHandler(button_handler, pattern='^voucher_menu$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            RESET_SALDO_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reset_saldo_process),
                CallbackQueryHandler(button_handler, pattern='^reset_saldo_menu$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            VOUCHER_REDEEM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, voucher_redeem_process),
                CallbackQueryHandler(button_handler, pattern='^voucher_menu$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            RENEW_MENU: [
                CallbackQueryHandler(button_handler, pattern='^renew_proto_'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            RENEW_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, renew_input_username),
                CallbackQueryHandler(renew_account_menu, pattern='^renew_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            RENEW_DAYS: [
                CallbackQueryHandler(button_handler, pattern='^rnum_'),
                CallbackQueryHandler(button_handler, pattern='^renew_confirm$'),
                CallbackQueryHandler(renew_account_menu, pattern='^renew_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            TRIAL_MENU: [
                CallbackQueryHandler(button_handler, pattern='^auto_trial_'),
                CallbackQueryHandler(button_handler, pattern='^trial_menu$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            AUTO_RENEW_MENU: [
                CallbackQueryHandler(button_handler, pattern='^auto_proto_'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            AUTO_RENEW_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, auto_renew_process),
                CallbackQueryHandler(auto_renew_menu, pattern='^auto_renew_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            AUTO_RENEW_SETTING: [
                CallbackQueryHandler(button_handler, pattern='^auto_renew_on$'),
                CallbackQueryHandler(button_handler, pattern='^auto_renew_off$'),
                CallbackQueryHandler(auto_renew_menu, pattern='^auto_renew_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            EDIT_HARGA_MENU: [
                CallbackQueryHandler(button_handler, pattern='^edit_harga_'),
                CallbackQueryHandler(button_handler, pattern='^voucher_menu$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
            ],
            
            EDIT_HARGA_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_harga_proses),
                CallbackQueryHandler(edit_harga_menu, pattern='^edit_harga_menu$'),
            ],
            
            BROADCAST_MENU: [
                CallbackQueryHandler(button_handler, pattern='^broadcast_text$'),
                CallbackQueryHandler(button_handler, pattern='^broadcast_photo$'),
                CallbackQueryHandler(button_handler, pattern='^broadcast_list$'),
                CallbackQueryHandler(button_handler, pattern='^voucher_menu$'),
                CallbackQueryHandler(kembali_ke_menu, pattern='^kembali_ke_menu$'),
            ],
            
            BROADCAST_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_process_text),
                MessageHandler(filters.PHOTO, broadcast_process_photo),
                CallbackQueryHandler(broadcast_menu, pattern='^broadcast_menu$'),
                CallbackQueryHandler(batal_callback, pattern='^proto_batal$'),
            ],
            
            STOCK_MENU: [
                CallbackQueryHandler(button_handler, pattern='^stock_'),
                CallbackQueryHandler(voucher_menu, pattern='^voucher_menu$'),
            ],
            
            STOCK_INPUT_ADD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stock_process_add),
                CallbackQueryHandler(stock_menu, pattern='^stock_menu$'),
            ],
            
            STOCK_INPUT_REMOVE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stock_process_remove),
                CallbackQueryHandler(stock_menu, pattern='^stock_menu$'),
            ],
            
            STOCK_INPUT_SET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stock_process_set),
                CallbackQueryHandler(stock_menu, pattern='^stock_menu$'),
            ],
        },
        fallbacks=[
            CommandHandler('batal', batal),
            CallbackQueryHandler(buat_lagi, pattern='^buat_lagi$'),
        ],
        allow_reentry=True,
        name="main_conversation",
        persistent=False,
    )
	
    app.add_handler(conv_handler)
    print("✅ Conversation handler added")
    
    # ===== FALLBACK HANDLER UNTUK TOPUP =====
    async def handle_angka_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle input angka untuk topup jika terlewat dari ConversationHandler"""
        text = update.message.text.strip()
        
        if text.isdigit():
            amount = int(text)
            if 1000 <= amount <= 1000000:
                # Proses sebagai topup
                context.user_data['topup_amount'] = amount
                context.user_data['topup_user'] = update.effective_user.id
                
                loading_msg = await update.message.reply_text(
                    "⏳ <b>MEMPROSES...</b>\n\nMohon tunggu sebentar.",
                    parse_mode='HTML'
                )
                
                await proses_topup_qris_from_message(update, context, amount, loading_msg)
                return
        
        await update.message.reply_text(
            "❌ Perintah tidak dikenali.\n"
            "Gunakan /start untuk memulai.",
            parse_mode='HTML'
        )
    
    app.add_handler(MessageHandler(
        filters.Regex(r'^\d+$') & ~filters.COMMAND,
        handle_angka_topup
    ))
    print("✅ Fallback topup handler added")
    
    # START BOT
    print("=" * 60)
    print("✅ BOT SIAP DAN BERJALAN!")
    print("📌 Klik /start untuk memulai")
    print("💰 Fitur Topup QRIS Otomatis AKTIF (Pakasir)")
    print("📢 Fitur Broadcast: /broadcast [pesan]")
    print("🌍 Fitur Region & Stok Aktif")
    print("📦 Manajemen Stok: Voucher Menu -> Manajemen Stok")
    print("=" * 60)
    
    try:
        app.run_polling(
            timeout=30,
            read_timeout=30,
            write_timeout=30,
            connect_timeout=30,
            pool_timeout=30,
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        print("\n⏹️ Bot dihentikan oleh user")
    except Exception as e:
        print(f"❌ Error saat menjalankan bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
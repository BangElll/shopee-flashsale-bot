import telebot
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json
from datetime import datetime
import threading
import logging
from typing import List, Dict
import sys
import os

# FIX: Konfigurasi UTF-8 untuk Windows
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Konfigurasi - GANTI INI!
TELEGRAM_TOKEN = "8629967467:AAEvjnx4Pyv5im8caTMJQzYU9FM72L8qaOc"
ADMIN_CHAT_ID = "8464029301"
SHOPEE_USERNAME = "qu220813@gmail.com"
SHOPEE_PASSWORD = "Letsmak3money"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# FIX: Logging dengan UTF-8 support
def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # File handler dengan UTF-8
    file_handler = logging.FileHandler('shopee_bot.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Console handler dengan UTF-8
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Clear existing handlers
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()

class ShopeeFlashSaleMonitor:
    def __init__(self):
        self.driver = None
        self.last_products = set()
        self.is_logged_in = False

    def setup_driver(self, headless=True):
        """Setup Chrome driver dengan fix"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("✅ Chrome driver berhasil dibuat")
            return True
        except Exception as e:
            logger.error(f"❌ Gagal buat driver: {str(e)}")
            return False

    def safe_login(self):
        """Login Shopee dengan error handling"""
        try:
            logger.info("🔐 Mencoba login Shopee...")
            self.driver.get("https://shopee.co.id/buyer/login")
            time.sleep(5)
            
            # Coba berbagai selector login
            selectors = [
                (By.NAME, "loginKey"),
                (By.XPATH, "//input[@placeholder*='No. telepon']"),
                (By.XPATH, "//input[@placeholder*='Email']")
            ]
            
            phone_input = None
            for by, selector in selectors:
                try:
                    phone_input = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    break
                except:
                    continue
            
            if not phone_input:
                logger.error("❌ Tidak menemukan input login")
                return False
                
            phone_input.clear()
            phone_input.send_keys(SHOPEE_USERNAME)
            time.sleep(1)
            
            # Password
            password_selectors = [
                (By.NAME, "password"),
                (By.XPATH, "//input[@type='password']")
            ]
            
            password_input = None
            for by, selector in password_selectors:
                try:
                    password_input = self.driver.find_element(by, selector)
                    break
                except:
                    continue
            
            if password_input:
                password_input.send_keys(SHOPEE_PASSWORD)
                time.sleep(1)
                
                # Login button
                login_selectors = [
                    (By.XPATH, "//button[@type='submit']"),
                    (By.XPATH, "//button[contains(text(), 'Masuk')]"),
                    (By.XPATH, "//div[contains(text(), 'Masuk')]//parent::button")
                ]
                
                login_btn = None
                for by, selector in login_selectors:
                    try:
                        login_btn = self.driver.find_element(by, selector)
                        login_btn.click()
                        break
                    except:
                        continue
            
            time.sleep(8)
            self.is_logged_in = True
            logger.info("✅ Login Shopee berhasil!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Login gagal: {str(e)}")
            return False

    def is_tanggal_kembar(self) -> bool:
        """Cek tanggal kembar"""
        now = datetime.now()
        return now.day == now.month

    def get_flashsale_products(self) -> List[Dict]:
        """Ambil produk flashsale - SIMPLIFIED"""
        products = []
        
        try:
            # Langsung ke flashsale
            flashsale_url = "https://shopee.co.id/m/flashsale"
            if self.is_tanggal_kembar():
                day = datetime.now().day
                flashsale_url = f"https://shopee.co.id/m/flashsale?date={day:02d}{day:02d}"
            
            self.driver.get(flashsale_url)
            time.sleep(5)
            
            # Scroll
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Ambil semua link produk
            product_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/product/')]")
            
            for link in product_links[:15]:
                try:
                    href = link.get_attribute('href')
                    if href and 'product' in href:
                        # Ambil nama dari title atau text
                        name_elem = link.find_elements(By.XPATH, ".//div[contains(@class, 'name')]")
                        name = name_elem[0].text[:40] if name_elem else "Produk Flashsale"
                        
                        price_elem = link.find_elements(By.XPATH, ".//*[contains(@class, 'price')]")
                        price = price_elem[0].text if price_elem else "Cek harga"
                        
                        products.append({
                            'name': name,
                            'price': price,
                            'url': href,
                            'is_kembar': self.is_tanggal_kembar()
                        })
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error get products: {str(e)}")
        
        return products

    def check_new_flashsale(self) -> List[Dict]:
        """Cek flashsale baru"""
        products = self.get_flashsale_products()
        new_products = []
        
        current_ids = {p['url'] for p in products}
        new_ids = current_ids - self.last_products
        
        for product in products:
            if product['url'] in new_ids:
                new_products.append(product)
        
        self.last_products.update(current_ids)
        return new_products

# Global monitor
monitor = ShopeeFlashSaleMonitor()
monitoring_active = False

def start_monitoring():
    """Start monitoring dalam thread terpisah"""
    global monitoring_active
    
    def monitor_loop():
        global monitoring_active
        
        if monitor.setup_driver(headless=True):
            if monitor.safe_login():
                logger.info("🚀 Monitoring flashsale DIMULAI")
                
                while monitoring_active:
                    try:
                        new_products = monitor.check_new_flashsale()
                        
                        if new_products:
                            kembar_emoji = "🎉 TANGGAL KEMBAR! 🎉" if monitor.is_tanggal_kembar() else ""
                            message = f"🚨 FLASH SALE BARU!\n{kembar_emoji}\n\n"
                            
                            for product in new_products[:5]:
                                message += f"• {product['name']}\n"
                                message += f"  💰 {product['price']}\n"
                                message += f"  {product['url']}\n\n"
                            
                            try:
                                bot.send_message(ADMIN_CHAT_ID, message)
                            except:
                                logger.error("Gagal kirim notifikasi")
                        
                        time.sleep(60)  # 1 menit
                        
                    except Exception as e:
                        logger.error(f"Monitor error: {str(e)}")
                        time.sleep(30)
        
        logger.info("⏹️ Monitoring berhenti")
    
    monitoring_active = True
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()

# ========== TELEGRAM HANDLERS (FIXED Markdown) ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    welcome_text = """Shopee Flashsale Bot Tanggal Kembar

Fitur:
- Monitor flashsale 24/7
- Notifikasi TANGGAL KEMBAR (11.11, 12.12, dll)
- Auto detect produk baru

Commands:
/check - Cek flashsale sekarang
/start_monitor - Mulai monitoring
/stop_monitor - Stop monitoring
/status - Status bot
/tanggal_kembar - Info tanggal kembar berikutnya

Siap berburu flashsale!"""
    
    try:
        bot.reply_to(message, welcome_text)
    except Exception as e:
        # Fallback plain text
        bot.reply_to(message, "Bot siap! Ketik /check untuk cek flashsale")

@bot.message_handler(commands=['check'])
def check_flashsale(message):
    bot.reply_to(message, "Sedang cek flashsale...")
    
    try:
        if not monitor.driver or not monitor.is_logged_in:
            if monitor.setup_driver(headless=False):
                monitor.safe_login()
        
        products = monitor.get_flashsale_products()
        
        if products:
            message_text = f"Flashsale ditemukan ({len(products)} produk):\n\n"
            for i, product in enumerate(products[:8], 1):
                message_text += f"{i}. {product['name']}\n"
                message_text += f"   {product['price']}\n"
                message_text += f"   {product['url']}\n\n"
            
            # Split jika terlalu panjang
            if len(message_text) > 4000:
                bot.reply_to(message, message_text[:4000])
            else:
                bot.reply_to(message, message_text, disable_web_page_preview=True)
        else:
            bot.reply_to(message, "Tidak ada flashsale saat ini")
            
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['start_monitor'])
def start_monitor_cmd(message):
    global monitoring_active
    if not monitoring_active:
        start_monitoring()
        bot.reply_to(message, "Monitoring DIMULAI! Notifikasi akan dikirim ke admin")
    else:
        bot.reply_to(message, "Monitoring sudah aktif")

@bot.message_handler(commands=['stop_monitor'])
def stop_monitor_cmd(message):
    global monitoring_active
    monitoring_active = False
    bot.reply_to(message, "Monitoring DIHENTIKAN")

@bot.message_handler(commands=['status'])
def status(message):
    now = datetime.now()
    is_kembar = "YA!" if monitor.is_tanggal_kembar() else "Tidak"
    
    status_text = f"""Status Bot:
Tanggal: {now.strftime('%d/%m/%Y %H:%M')}
Tanggal Kembar: {is_kembar}
Monitoring: {'AKTIF' if monitoring_active else 'OFF'}
Login Shopee: {'OK' if monitor.is_logged_in else 'Belum'}"""
    
    bot.reply_to(message, status_text)

@bot.message_handler(commands=['tanggal_kembar'])
def tanggal_kembar(message):
    now = datetime.now()
    next_kembar = None
    
    for day in range(1, 13):
        kembar_date = datetime(now.year, day, day)
        if kembar_date > now:
            next_kembar = kembar_date
            break
    
    if next_kembar:
        days_left = (next_kembar - now).days
        text = f"Tanggal kembar berikutnya: {next_kembar.strftime('%d.%m.%Y')}\nSisa: {days_left} hari"
    else:
        text = "Tanggal kembar bulan ini sudah lewat!"
    
    bot.reply_to(message, text)

@bot.message_handler(func=lambda message: True)
def unknown(message):
    bot.reply_to(message, "Command tidak dikenal. Ketik /start")

# Tambahkan di akhir file (sebelum if __name__):
if __name__ == "__main__":
    logger.info("Telegram Shopee Flashsale Bot Started!")
    logger.info(f"Hari ini tanggal kembar: {monitor.is_tanggal_kembar()}")
    
    # AUTO START MONITORING (opsional)
    start_monitoring()
    
    try:
        bot.infinity_polling(none_stop=True)
    except Exception as e:
        logger.error(f"Bot error: {str(e)}")
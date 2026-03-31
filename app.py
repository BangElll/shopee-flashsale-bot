# app.py - Versi Render ready
import os
import telebot
from telegram_shopee_bot_fixed import ShopeeFlashSaleMonitor, start_monitoring, logger
from flask import Flask

# Flask app untuk Render health check
app = Flask(__name__)

# Telegram config dari Environment Variables
TELEGRAM_TOKEN = os.getenv('8629967467:AAEvjnx4Pyv5im8caTMJQzYU9FM72L8qaOc')
ADMIN_CHAT_ID = os.getenv('8464029301')
SHOPEE_USERNAME = os.getenv('qu220813@gmail.com')
SHOPEE_PASSWORD = os.getenv('Letsmak3money')

bot = telebot.TeleBot(TELEGRAM_TOKEN)
monitor = ShopeeFlashSaleMonitor()

@app.route('/')
def health_check():
    return "🤖 Shopee Flashsale Bot OK!"

@app.route('/status')
def status():
    return f"""
    Status: OK
    Tanggal Kembar: {monitor.is_tanggal_kembar()}
    Monitoring: {'Active' if 'monitoring_active' in globals() and monitoring_active else 'Stopped'}
    """

# Copy semua handler dari telegram_shopee_bot_fixed.py ke sini
# ... (paste semua @bot.message_handler dari file sebelumnya)

# Background task untuk monitoring
def run_monitoring():
    global monitoring_active
    monitoring_active = True
    start_monitoring()

if __name__ == "__main__":
    # Start monitoring di background
    import threading
    monitor_thread = threading.Thread(target=run_monitoring, daemon=True)
    monitor_thread.start()
    
    logger.info("🚀 Render Bot Started!")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
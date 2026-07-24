import asyncio
import sqlite3
import re
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetHistoryRequest
import requests
import os

# ========== КОНФИГ ==========
BOT_TOKEN = "8879746943:AAEkKGyga7ooDSu5YbofrlPWjY49z8dTu3A"
CHAT_ID = 7847983646

# Берем из переменных окружения (безопасно)
API_ID = int(os.getenv('API_ID', 12345))
API_HASH = os.getenv('API_HASH', 'your_api_hash')
CHANNEL_NAME = os.getenv('CHANNEL_NAME', 'Gift Market')

# ========== БАЗА ДАННЫХ ==========
conn = sqlite3.connect('gifts.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS gifts (
        id TEXT PRIMARY KEY,
        model TEXT,
        pattern TEXT,
        background TEXT,
        price TEXT,
        unlock_time TEXT,
        status TEXT,
        first_seen TEXT
    )
''')
conn.commit()

# ========== ОТПРАВКА УВЕДОМЛЕНИЙ ==========
def send_notification(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def parse_gift_message(text):
    gift_data = {}
    price_match = re.search(r'[★⭐]\s*(\d+)\+?', text)
    if price_match:
        gift_data['price'] = price_match.group(1)
    
    date_match = re.search(r'(\d{1,2}\s+(?:янв|фев|мар|апр|мая|июн|июл|авг|сен|окт|ноя|дек)\s+\d{4}\s+в\s+\d{2}:\d{2})', text)
    if date_match:
        gift_data['unlock_time'] = date_match.group(1)
    
    if 'Модель' in text:
        model_match = re.search(r'Модель\s+([^\n]+)', text)
        if model_match:
            gift_data['model'] = model_match.group(1).strip()
    
    if 'Узор' in text:
        pattern_match = re.search(r'Узор\s+([^\n]+)', text)
        if pattern_match:
            gift_data['pattern'] = pattern_match.group(1).strip()
    
    if 'Фон' in text:
        bg_match = re.search(r'Фон\s+([^\n]+)', text)
        if bg_match:
            gift_data['background'] = bg_match.group(1).strip()
    
    return gift_data

async def main():
    client = TelegramClient('session', API_ID, API_HASH)
    await client.start()
    
    print("✅ Бот запущен!")
    send_notification("🚀 Бот запущен на Railway! Отслеживаю подарки.")
    
    try:
        entity = await client.get_entity(CHANNEL_NAME)
    except Exception as e:
        print(f"❌ Чат '{CHANNEL_NAME}' не найден! Ошибка: {e}")
        send_notification(f"❌ Чат '{CHANNEL_NAME}' не найден! Проверь название.")
        return
    
    last_message_id = 0
    
    while True:
        try:
            history = await client(GetHistoryRequest(
                peer=entity,
                limit=10,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=last_message_id,
                add_offset=0,
                hash=0
            ))
            
            for msg in history.messages:
                if msg.id <= last_message_id:
                    continue
                
                if msg.text and any(keyword in msg.text for keyword in ['★', '⭐', 'Модель', 'размороз', 'маркет']):
                    gift_data = parse_gift_message(msg.text)
                    
                    if gift_data.get('price') or gift_data.get('model'):
                        notif_text = f"🆕 <b>Новый подарок!</b>\n"
                        if gift_data.get('model'):
                            notif_text += f"📦 Модель: {gift_data['model']}\n"
                        if gift_data.get('price'):
                            notif_text += f"💰 Цена: ★ {gift_data['price']}+\n"
                        if gift_data.get('unlock_time'):
                            notif_text += f"⏳ Разморозка: {gift_data['unlock_time']}\n"
                        
                        notif_text += f"\n🔗 <a href='https://t.me/c/{entity.id}/{msg.id}'>Открыть подарок</a>"
                        
                        send_notification(notif_text)
                        print(f"📨 Отправлено: {gift_data}")
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO gifts 
                            (id, model, pattern, background, price, unlock_time, status, first_seen)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            f"{entity.id}_{msg.id}",
                            gift_data.get('model', ''),
                            gift_data.get('pattern', ''),
                            gift_data.get('background', ''),
                            gift_data.get('price', ''),
                            gift_data.get('unlock_time', ''),
                            'new',
                            datetime.now().isoformat()
                        ))
                        conn.commit()
                
                last_message_id = max(last_message_id, msg.id)
            
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    print("Запуск парсера...")
    asyncio.run(main())

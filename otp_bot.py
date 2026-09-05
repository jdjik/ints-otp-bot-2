import requests
import time
import re
import threading
import os
import sys
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "INTS Panel API-Based OTP Bot is Running 24/7!"

# ==================== আপনার কনফিগারেশন ====================
TELEGRAM_BOT_TOKEN = "8884098961:AAE1UxFAH60LQaUdnB6q3MKN2VHJ8mw84Q0"
TELEGRAM_CHAT_ID = "-1004358010030"

# আপনার দেওয়া API Token
PANEL_API_TOKEN = "coCDhoNwgHl6i0pGRlVP"
# ==========================================================

latest_stamp = None

def log_print(message):
    print(message)
    sys.stdout.flush()

def mask_phone_number(phone):
    if not phone:
        return ""
    phone_str = str(phone).strip().replace("+", "")
    if len(phone_str) <= 7:
        return f"+{phone_str}"
    
    start = phone_str[:4]      
    end = phone_str[-3:]       
    masked = "*" * (len(phone_str) - 7) 
    return f"+{start}{masked}{end}"

def get_global_country(phone):
    phone_str = str(phone).strip().replace("+", "")
    country_map = {
        "236": ("Central African Republic", "🇨🇫"),
        "241": ("Gabon", "🇬🇦"),
        "994": ("Azerbaijan", "🇦🇿"),
        "880": ("Bangladesh", "🇧🇩"),
        "91": ("India", "🇮🇳"),
        "92": ("Pakistan", "🇵🇰"),
        "1": ("USA/Canada", "🇺🇸"),
        "44": ("United Kingdom", "🇬🇧")
    }
    for length in [3, 2, 1]:
        prefix = phone_str[:length]
        if prefix in country_map:
            return country_map[prefix]
    return "International", "🌍"

def extract_otp(message):
    match = re.search(r'\b\d{4,8}\b', message)
    return match.group(0) if match else ""

def send_telegram_message(text):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(telegram_url, json=payload, timeout=10)
    except Exception as e:
        log_print(f"[-] Telegram Error: {e}")

def fetch_new_sms():
    global latest_stamp
    
    now_ms = int(time.time() * 1000)
    
    # URL ও Header দুটোতেই API Token পাঠানো হচ্ছে
    full_api_url = (
        f"http://145.239.130.45/ints/agent/res/data_smscdr.php?"
        f"token={PANEL_API_TOKEN}&api_key={PANEL_API_TOKEN}"
        f"&sEcho=1&iColumns=8&sColumns=&iDisplayStart=0&iDisplayLength=10"
        f"&fdate1=2026-09-03%2000:00:00&fdate2=2026-09-03%2023:59:59"
        f"&frange=&fclient=&fnum=&fcli=&fgdata=&_={now_ms}"
    )
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Authorization": f"Bearer {PANEL_API_TOKEN}",
        "X-API-KEY": PANEL_API_TOKEN,
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }
    
    try:
        response = requests.get(full_api_url, headers=headers, timeout=15)
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                log_print("[!] Response Error: Output is not JSON. API Key placement issue?")
                return

            sms_list = data.get('aaData') or data.get('data') or []
            if not isinstance(sms_list, list) or not sms_list:
                log_print("[*] API Connected! No new SMS found.")
                return

            first_item = sms_list[0]
            first_stamp = first_item[0] if isinstance(first_item, list) else first_item.get('start_stamp')

            if latest_stamp is None:
                latest_stamp = first_stamp
                log_print(f"[*] INTS API Connected via Token! Initial stamp: {latest_stamp}")
                return

            for sms in reversed(sms_list):
                if isinstance(sms, list):
                    current_stamp = sms[0]
                    source = sms[2] if len(sms) > 2 else "TELEGRAM"
                    receiver = sms[3] if len(sms) > 3 else ""
                    message = sms[4] if len(sms) > 4 else ""
                else:
                    current_stamp = sms.get('start_stamp')
                    message = sms.get('short_message') or ""
                    receiver = sms.get('destination_addr') or ""
                    source = sms.get('source_addr') or "TELEGRAM"

                if current_stamp and current_stamp > latest_stamp:
                    otp_code = extract_otp(message)
                    country_name, country_flag = get_global_country(receiver)
                    masked_number = mask_phone_number(receiver)
                    service_name = str(source).upper() if "Unknown" not in str(source) else "TELEGRAM"
                    
                    alert_text = (
                        f"🚨 **NEW OTP RECEIVED** 🚨\n\n"
                        f"◁ **NUMBER:** `{masked_number}`\n"
                        f"◁ **OTP:** `{otp_code}`\n"
                        f"◁ **SERVICE:** {service_name}\n"
                        f"◁ **LOCATION:** {country_name} {country_flag}\n\n"
                        f"💬 **SMS Text:**\n`{message}`"
                    )
                    send_telegram_message(alert_text)
                    log_print(f"[+] OTP Forwarded to Telegram! (Time: {current_stamp})")
                    latest_stamp = current_stamp
        elif response.status_code == 503:
            log_print("[!] Error 503: Rate limited by panel.")
        else:
            log_print(f"[!] API Response Code: {response.status_code}")
    except Exception as e:
        log_print(f"[-] Connection Exception: {e}")

def main_loop():
    while True:
        fetch_new_sms()
        time.sleep(60)

if __name__ == "__main__":
    t = threading.Thread(target=main_loop, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

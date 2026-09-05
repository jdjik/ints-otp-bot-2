import requests
import time
import re
import threading
import os
import sys
from datetime import datetime
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "INTS Panel Auto-Session OTP Bot is Running 24/7!"

# ==================== আপনার কনফিগারেশন ====================
TELEGRAM_BOT_TOKEN = "8884098961:AAE1UxFAH60LQaUdnB6q3MKN2VHJ8mw84Q0"
TELEGRAM_CHAT_ID = "-1004358010030"

PANEL_BASE_URL = "http://145.239.130.45/ints"
PANEL_USERNAME = "abdurRahim"  # আপনার প্যানেল ইউজারনেম
PANEL_PASSWORD = "Rahim@1424@"  # আপনার প্যানেল পাসওয়ার্ড
# ==========================================================

session = requests.Session()
latest_stamp = None

def log_print(message):
    print(message)
    sys.stdout.flush()

def login_to_panel():
    global session
    session = requests.Session()  # নতুন সেশন তৈরি করা
    login_url = f"{PANEL_BASE_URL}/login"
    login_action_url = f"{PANEL_BASE_URL}/agent/login_check"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Origin": "http://145.239.130.45",
        "Referer": login_url
    }
    
    payload = {
        "_username": PANEL_USERNAME,
        "username": PANEL_USERNAME,
        "_password": PANEL_PASSWORD,
        "password": PANEL_PASSWORD,
        "login": "Login"
    }
    
    try:
        log_print("[*] Attempting HTTP Session Auto-Login...")
        session.get(login_url, headers=headers, timeout=15)
        res = session.post(login_action_url, data=payload, headers=headers, timeout=15)
        log_print("[+] Session Auto-Login Completed.")
        return True
    except Exception as e:
        log_print(f"[-] Login Exception: {e}")
        return False

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
        res = requests.post(telegram_url, json=payload, timeout=10)
        log_print(f"[*] Telegram Send Status: {res.status_code}")
    except Exception as e:
        log_print(f"[-] Telegram Error: {e}")

def fetch_new_sms():
    global latest_stamp, session
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_ms = int(time.time() * 1000)
    
    full_api_url = (
        f"http://145.239.130.45/ints/agent/res/data_smscdr.php?"
        f"sEcho=1&iColumns=8&sColumns=&iDisplayStart=0&iDisplayLength=10"
        f"&fdate1={today_str}%2000:00:00&fdate2={today_str}%2023:59:59"
        f"&frange=&fclient=&fnum=&fcli=&fgdata=&_={now_ms}"
    )
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "http://145.239.130.45/ints/agent/SMSCDRReports",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }
    
    try:
        response = session.get(full_api_url, headers=headers, timeout=15)
        
        # যদি রেসপন্স JSON না হয় বা রিডাইরেক্ট করে লগইন পেজে পাঠায়
        if "<html" in response.text.lower() or "login" in response.url.lower():
            log_print("[!] Session Expired or Redirected. Re-authenticating...")
            login_to_panel()
            return

        try:
            data = response.json()
        except Exception as e:
            log_print(f"[!] JSON Parsing Failed: {e}")
            return

        sms_list = data.get('aaData') or data.get('data') or []
        if not isinstance(sms_list, list) or not sms_list:
            log_print("[*] Checking for new SMS... (No new SMS found)")
            return

        first_item = sms_list[0]
        first_stamp = first_item[0] if isinstance(first_item, list) else first_item.get('start_stamp')

        if latest_stamp is None:
            latest_stamp = first_stamp
            log_print(f"[*] Connected successfully! Current stamp: {latest_stamp}")
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
                log_print(f"[+] OTP Sent to Telegram! Stamp: {current_stamp}")
                latest_stamp = current_stamp

    except Exception as e:
        log_print(f"[-] Connection Exception: {e}")

def main_loop():
    login_to_panel()
    while True:
        fetch_new_sms()
        time.sleep(20)

if __name__ == "__main__":
    t = threading.Thread(target=main_loop, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

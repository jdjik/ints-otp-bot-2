import requests
import time
import re
import threading
import os
import sys
from flask import Flask
from python_anticaptcha import AnticaptchaClient, NoCaptchaTaskProxylessTask

# Flask App Initialization
app = Flask(__name__)

@app.route('/')
def home():
    return "INTS Panel Auto-Login & OTP Bot is Running 24/7!"

# ==================== আপনার কনফিগারেশন ====================
TELEGRAM_BOT_TOKEN = "8884098961:AAE1UxFAH60LQaUdnB6q3MKN2VHJ8mw84Q0"
TELEGRAM_CHAT_ID = "-1004358010030"

# INTS Panel Login Details
PANEL_LOGIN_URL = "http://145.239.130.45/ints/login"  # প্যানেলের আসল লগইন URL দিন
PANEL_USERNAME = "abdurRahim"                      # আপনার প্যানেল ইউজারনেম
PANEL_PASSWORD = "Rahim@1424@"                      # আপনার প্যানেল পাসওয়ার্ড
PANEL_SITEKEY = "6Lcfa1sUAAAAAKVPye-X6cftDCzFiF3BSHljWqNR"             # প্যানেল লগইন পেজের google sitekey

# Anti-Captcha API Key
ANTICAPTCHA_KEY = 377fb1c778cf04f2fb607024cae95ef9"
# ==========================================================

PANEL_COOKIE = ""
latest_stamp = None

def log_print(message):
    print(message)
    sys.stdout.flush()

def solve_recaptcha():
    """Anti-Captcha API ব্যবহার করে ক্যাপচা সলভ করে g-recaptcha-response প্রদান করে"""
    log_print("[*] Captcha Solving Started via Anti-Captcha...")
    try:
        client = AnticaptchaClient(ANTICAPTCHA_KEY)
        task = NoCaptchaTaskProxylessTask(PANEL_LOGIN_URL, PANEL_SITEKEY)
        job = client.create_task(task)
        job.wait_for_result()
        g_response = job.get_solution_response()
        log_print("[+] Captcha Solved Successfully!")
        return g_response
    except Exception as e:
        log_print(f"[-] Captcha Solving Failed: {e}")
        return None

def auto_login():
    """স্বয়ংক্রিয়ভাবে প্যানেলে লগইন করে নতুন PHPSESSID সংগ্রহ করে"""
    global PANEL_COOKIE
    log_print("[*] Attempting Automatic Panel Login...")
    
    g_recaptcha_response = solve_recaptcha()
    if not g_recaptcha_response:
        log_print("[-] Login Aborted: Captcha not solved.")
        return False

    session = requests.Session()
    login_payload = {
        "username": PANEL_USERNAME,
        "password": PANEL_PASSWORD,
        "g-recaptcha-response": g_recaptcha_response
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": PANEL_LOGIN_URL
    }

    try:
        res = session.post(PANEL_LOGIN_URL, data=login_payload, headers=headers, timeout=20)
        cookies = session.cookies.get_dict()
        if "PHPSESSID" in cookies:
            PANEL_COOKIE = f"PHPSESSID={cookies['PHPSESSID']}"
            log_print(f"[+] Auto-Login Successful! New Cookie: {PANEL_COOKIE}")
            return True
        else:
            log_print("[-] Login failed or PHPSESSID not found in response.")
            return False
    except Exception as e:
        log_print(f"[-] Login Error: {e}")
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
        requests.post(telegram_url, json=payload, timeout=10)
    except Exception as e:
        log_print(f"[-] Telegram Error: {e}")

def fetch_new_sms():
    global latest_stamp, PANEL_COOKIE
    
    if not PANEL_COOKIE:
        if not auto_login():
            return

    now_ms = int(time.time() * 1000)
    full_api_url = (
        f"http://145.239.130.45/ints/agent/res/data_smscdr.php?"
        f"sEcho=1&iColumns=8&sColumns=&iDisplayStart=0&iDisplayLength=10"
        f"&fdate1=2026-09-03%2000:00:00&fdate2=2026-09-03%2023:59:59"
        f"&frange=&fclient=&fnum=&fcli=&fgdata=&_={now_ms}"
    )
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "http://145.239.130.45/ints/agent/SMSCDRReports",
        "Cookie": PANEL_COOKIE,
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }
    
    try:
        response = requests.get(full_api_url, headers=headers, timeout=15)
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                log_print("[!] JSON Parse Error. Cookie Expired! Re-logging...")
                PANEL_COOKIE = ""
                auto_login()
                return

            sms_list = data.get('aaData') or data.get('data') or []
            if not isinstance(sms_list, list) or not sms_list:
                log_print("[*] Connected. No new SMS.")
                return

            first_item = sms_list[0]
            first_stamp = first_item[0] if isinstance(first_item, list) else first_item.get('start_stamp')

            if latest_stamp is None:
                latest_stamp = first_stamp
                log_print(f"[*] INTS API Connected! Initial stamp: {latest_stamp}")
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
            log_print("[!] Error 503: Rate limited.")
        else:
            log_print(f"[!] API Error Code: {response.status_code}")
    except Exception as e:
        log_print(f"[-] API Connection Error: {e}")

def main_loop():
    while True:
        fetch_new_sms()
        time.sleep(30)

if __name__ == "__main__":
    t = threading.Thread(target=main_loop, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

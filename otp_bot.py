import requests
import time
import re
import threading
import os
import sys
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "INTS Panel Voice/SMS OTP Bot 2 is Running Live 24/7!"

# ==================== আপনার কনফিগারেশন ====================
TELEGRAM_BOT_TOKEN = "8884098961:AAE1UxFAH60LQaUdnB6q3MKN2VHJ8mw84Q0"
TELEGRAM_CHAT_ID = "-1004358010030"

# আপনার কুকি
PANEL_COOKIE = "PHPSESSID=ms355fnuahbptbtlt7ntncbbd9"
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
        "213": ("Algeria", "🇩🇿"),
        "961": ("Lebanon", "🇱🇧"),
        "880": ("Bangladesh", "🇧🇩"),
        "91": ("India", "🇮🇳"),
        "92": ("Pakistan", "🇵🇰"),
        "7": ("Russia/Kazakhstan", "🇷🇺"),
        "33": ("France", "🇫🇷"),
        "49": ("Germany", "🇩🇪"),
        "966": ("Saudi Arabia", "🇸🇦"),
        "971": ("UAE", "🇦🇪"),
        "60": ("Malaysia", "🇲🇾"),
        "65": ("Singapore", "🇸🇬"),
        "44": ("United Kingdom", "🇬🇧"),
        "1": ("USA/Canada", "🇺🇸"),
        "974": ("Qatar", "🇶🇦"),
        "965": ("Kuwait", "🇰🇼"),
        "968": ("Oman", "🇴🇲"),
        "973": ("Bahrain", "🇧🇭"),
        "962": ("Jordan", "🇯🇴"),
        "20": ("Egypt", "🇪🇬"),
        "90": ("Turkey", "🇹🇷"),
        "27": ("South Africa", "🇿🇦"),
        "234": ("Nigeria", "🇳🇬"),
        "254": ("Kenya", "🇰🇪"),
        "212": ("Morocco", "🇲🇦"),
        "216": ("Tunisia", "🇹🇳"),
        "964": ("Iraq", "🇮🇶"),
        "39": ("Italy", "🇮🇹"),
        "34": ("Spain", "🇪🇸"),
        "41": ("Switzerland", "🇨🇭"),
        "31": ("Netherlands", "🇳🇱"),
        "32": ("Belgium", "🇧🇪"),
        "46": ("Sweden", "🇸🇪"),
        "47": ("Norway", "🇳🇴"),
        "61": ("Australia", "🇦🇺"),
        "64": ("New Zealand", "🇳ℤ"),
        "81": ("Japan", "🇯🇵"),
        "82": ("South Korea", "🇰🇷"),
        "86": ("China", "🇨🇳"),
        "62": ("Indonesia", "🇮🇩"),
        "66": ("Thailand", "🇹🇭"),
        "63": ("Philippines", "🇵🇭"),
        "84": ("Vietnam", "🇻🇳"),
        "94": ("Sri Lanka", "🇱🇰"),
        "977": ("Nepal", "🇳🇵"),
        "960": ("Maldives", "🇲🇻"),
        "55": ("Brazil", "🇧🇷"),
        "52": ("Mexico", "🇲🇽"),
        "54": ("Argentina", "🇦🇷")
    }
    
    for length in [3, 2, 1]:
        prefix = phone_str[:length]
        if prefix in country_map:
            return country_map[prefix]
            
    return "International", "🌍"

def extract_otp(message):
    match = re.search(r'\b\d{4,8}\b', message)
    if match:
        return match.group(0)
    return ""

def send_telegram_message(text):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(telegram_url, json=payload, timeout=10)
    except Exception as e:
        log_print(f"[-] Telegram Error: {e}")

def fetch_new_sms():
    global latest_stamp
    
    # ডায়নামিক টাইমস্ট্যাম্প তৈরি
    now_ms = int(time.time() * 1000)
    
    #DataTable এর আসল প্যারামিটার সহ URL
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
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }
    
    try:
        response = requests.get(full_api_url, headers=headers, timeout=15)
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                log_print("[!] JSON পার্স করা যায়নি। কুকি সেশন হয়তো এক্সপায়ার হয়ে গেছে।")
                return

            sms_list = data.get('aaData') or data.get('data') or []
            
            if not isinstance(sms_list, list) or not sms_list:
                log_print("[*] ডাটা পাওয়া গেছে কিন্তু কোনো নতুন এসএমএস নেই।")
                return

            first_item = sms_list[0]
            first_stamp = first_item[0] if isinstance(first_item, list) else first_item.get('start_stamp')

            if latest_stamp is None:
                latest_stamp = first_stamp
                log_print(f"[*] INTS API কানেক্টেড! প্রথম টাইমস্ট্যাম্প: {latest_stamp}")
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
                    log_print(f"[+] ওটিপি Telegram-এ ফরোয়ার্ড করা হয়েছে! (Time: {current_stamp})")
                    
                    latest_stamp = current_stamp
        elif response.status_code == 503:
            log_print("[!] Error 503: প্যানেলে ১৫ সেকেন্ডের কম সময়ে রিকোয়েস্ট পাঠানো হয়েছে অথবা সেশন ফ্রোজ হয়ে গেছে।")
        else:
            log_print(f"[!] API Response Error Code: {response.status_code}")
    except Exception as e:
        log_print(f"[-] API Connection Error: {e}")

def main_loop():
    while True:
        fetch_new_sms()
        time.sleep(30)  # প্যানেলের রেট-লিমিটিং এড়াতে বিরতি ৩০ সেকেন্ডে উন্নীত করা হলো

if __name__ == "__main__":
    t = threading.Thread(target=main_loop, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

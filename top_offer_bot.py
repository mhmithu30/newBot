import requests
from bs4 import BeautifulSoup
import time
import json
import os
import re
from collections import defaultdict
from datetime import datetime

# ========== এনভায়রনমেন্ট ভেরিয়েবল (Railway এ সেট করবেন) ==========
BOT_TOKEN = os.environ.get("8644605311:AAEX4ZdRk46ZoehgE3_5pUz6sM5Pp_2y10Y")
CHAT_ID = os.environ.get("6881373105")

# ========== সাইট লিংক ==========
HUNTSKIN_URL = "https://huntskin.com/Liveoffersfinal/Live.php"
APUCASH_URL = "https://apucash.com"
PAIDCASH_URL = "https://paidcash.co"

OFFER_COUNT_FILE = "top_offer_counts.json"
REPORT_INTERVAL = 7200  # ২ ঘণ্টা

# Survey Walls ব্লকলিস্ট
SURVEY_WALLS_BLOCKLIST = ["theoremreach", "cpx research", "pollfish", "survey", "surveys"]

def load_counts():
    if os.path.exists(OFFER_COUNT_FILE):
        with open(OFFER_COUNT_FILE, "r") as f:
            return json.load(f)
    return {"huntskin": {}, "apucash": {}, "paidcash": {}}

def save_counts(counts):
    with open(OFFER_COUNT_FILE, "w") as f:
        json.dump(counts, f)

def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ BOT_TOKEN or CHAT_ID missing!")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def scrape_huntskin():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(HUNTSKIN_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        offers = []
        rows = soup.find_all("tr")
        for row in rows:
            type_td = row.find("td", attrs={"data-label": "type"})
            if type_td:
                offer_name = type_td.get_text(strip=True)
                if offer_name:
                    offers.append(offer_name)
        return offers
    except Exception as e:
        print(f"Huntskin error: {e}")
        return []

def scrape_apucash():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(APUCASH_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        offers = []
        public_cards = soup.find_all("div", class_=re.compile(r"activity-item|offer-item"))
        for card in public_cards:
            try:
                offer_name_elem = card.find("span", class_=re.compile(r"offer-title|title"))
                if offer_name_elem:
                    offer_name = offer_name_elem.get_text(strip=True)
                    if offer_name:
                        offers.append(offer_name)
            except:
                continue
        return offers
    except Exception as e:
        print(f"Apucash error: {e}")
        return []

def scrape_paidcash():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(PAIDCASH_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        offers = []
        items = soup.find_all("div", class_="earning-feed-item")
        for item in items:
            try:
                title_elem = item.find("p", class_="earning-feed-item-content-title")
                offerwall = title_elem.get_text(strip=True).lower() if title_elem else ""
                is_survey = any(k in offerwall for k in SURVEY_WALLS_BLOCKLIST)
                if is_survey:
                    continue
                points_elem = item.find("p", class_="earning-feed-item-reward-amount")
                points_str = points_elem.get_text(strip=True) if points_elem else "0"
                points_val = float(re.sub(r'[^\d.]', '', points_str)) if points_str else 0
                if points_val < 200:
                    continue
                offer_name = title_elem.get_text(strip=True) if title_elem else "Offer"
                offers.append(offer_name)
            except:
                continue
        return offers
    except Exception as e:
        print(f"Paidcash error: {e}")
        return []

def update_counts():
    counts = load_counts()
    
    for offer in scrape_huntskin():
        counts["huntskin"][offer] = counts["huntskin"].get(offer, 0) + 1
    
    for offer in scrape_apucash():
        counts["apucash"][offer] = counts["apucash"].get(offer, 0) + 1
    
    for offer in scrape_paidcash():
        counts["paidcash"][offer] = counts["paidcash"].get(offer, 0) + 1
    
    save_counts(counts)
    return counts

def get_top_3(counts_dict):
    sorted_items = sorted(counts_dict.items(), key=lambda x: x[1], reverse=True)
    return sorted_items[:3]

def send_report():
    counts = update_counts()
    
    message = "<b>📊 টপ অফার রিপোর্ট (গত ২ ঘণ্টা)</b>\n\n"
    
    top_hunt = get_top_3(counts["huntskin"])
    if top_hunt:
        message += "🔴 <b>Huntskin</b>\n"
        for i, (name, count) in enumerate(top_hunt, 1):
            message += f"{i}️⃣ {name} - {count} বার\n"
        message += "\n"
    
    top_apu = get_top_3(counts["apucash"])
    if top_apu:
        message += "🟢 <b>ApuCash</b>\n"
        for i, (name, count) in enumerate(top_apu, 1):
            message += f"{i}️⃣ {name} - {count} বার\n"
        message += "\n"
    
    top_paid = get_top_3(counts["paidcash"])
    if top_paid:
        message += "🪙 <b>PaidCash</b>\n"
        for i, (name, count) in enumerate(top_paid, 1):
            message += f"{i}️⃣ {name} - {count} বার\n"
    
    if not (top_hunt or top_apu or top_paid):
        message += "❌ গত ২ ঘণ্টায় কোনো অফার পাওয়া যায়নি।"
    
    send_telegram(message)
    
    # কাউন্ট রিসেট
    save_counts({"huntskin": {}, "apucash": {}, "paidcash": {}})

def main():
    print("✅ টপ অফার রিপোর্ট বট চালু হয়েছে")
    send_telegram("✅ <b>টপ অফার রিপোর্ট বট চালু হয়েছে!</b>\n\nপ্রতি ২ ঘণ্টা পর টপ ৩ অফারের রিপোর্ট পাঠানো হবে।")
    
    last_report = time.time()
    
    while True:
        current_time = time.time()
        if current_time - last_report >= REPORT_INTERVAL:
            send_report()
            last_report = current_time
        time.sleep(60)

if __name__ == "__main__":
    main()

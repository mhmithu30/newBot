import requests
from bs4 import BeautifulSoup
import time
import json
import os
import re

# ========== আপনার টোকেন ও চ্যাট আইডি (সেট করা আছে) ==========
BOT_TOKEN = "8644605311:AAEX4ZdRk46ZoehgE3_5pUz6sM5Pp_2y10Y"
CHAT_ID = "6881373105"

# ========== সাইট লিংক ==========
HUNTSKIN_URL = "https://huntskin.com/Liveoffersfinal/Live.php"
APUCASH_URL = "https://apucash.com"
PAIDCASH_URL = "https://paidcash.co"

OFFER_COUNT_FILE = "top_offer_counts.json"
REPORT_INTERVAL = 7200  # ২ ঘণ্টা

# Survey Walls ব্লকলিস্ট (PaidCash-এর জন্য)
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
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        print(f"Telegram send: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def scrape_huntskin():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(HUNTSKIN_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        offers = []
        rows = soup.find_all("tr")
        for row in rows:
            type_td = row.find("td", attrs={"data-label": "type"})
            if type_td:
                offer_name = type_td.get_text(strip=True)
                if offer_name and offer_name != "?":
                    offers.append(offer_name)
        print(f"Huntskin offers found: {len(offers)}")
        return offers
    except Exception as e:
        print(f"Huntskin error: {e}")
        return []

def scrape_apucash():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(APUCASH_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        offers = []
        
        # পাবলিক প্রোফাইল
        public_cards = soup.find_all("div", class_=re.compile(r"activity-item|offer-item"))
        for card in public_cards:
            try:
                offer_name_elem = card.find("span", class_=re.compile(r"offer-title|title"))
                if offer_name_elem:
                    offer_name = offer_name_elem.get_text(strip=True)
                    if offer_name and offer_name != "?":
                        offers.append(offer_name)
            except:
                continue
        
        # প্রাইভেট প্রোফাইল
        private_blocks = soup.find_all("div", attrs={"wire:key": re.compile(r"^offer-\d+$")})
        for block in private_blocks:
            try:
                h6 = block.find("h6")
                if h6:
                    activity = h6.get_text(strip=True)
                    if activity and activity != "?":
                        offers.append(activity)
            except:
                continue
        
        print(f"ApuCash offers found: {len(offers)}")
        return offers
    except Exception as e:
        print(f"ApuCash error: {e}")
        return []

def scrape_paidcash():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(PAIDCASH_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        offers = []
        
        items = soup.find_all("div", class_="earning-feed-item")
        
        for item in items:
            try:
                title_elem = item.find("p", class_="earning-feed-item-content-title")
                offerwall = title_elem.get_text(strip=True).lower() if title_elem else ""
                
                # Survey Walls বাদ দেওয়া
                is_survey = any(keyword in offerwall for keyword in SURVEY_WALLS_BLOCKLIST)
                if is_survey:
                    continue
                
                # পয়েন্টস চেক (২০০ বা তার বেশি)
                points_elem = item.find("p", class_="earning-feed-item-reward-amount")
                points_str = points_elem.get_text(strip=True) if points_elem else "0"
                points_val = float(re.sub(r'[^\d.]', '', points_str)) if points_str else 0
                
                if points_val < 200:
                    continue
                
                # অফারের নাম
                offer_name = title_elem.get_text(strip=True) if title_elem else "Offer"
                if offer_name and offer_name != "?":
                    offers.append(offer_name)
            except:
                continue
        
        print(f"PaidCash offers found (200+ pts): {len(offers)}")
        return offers
    except Exception as e:
        print(f"PaidCash error: {e}")
        return []

def update_counts():
    counts = load_counts()
    
    # Huntskin কাউন্ট
    for offer in scrape_huntskin():
        counts["huntskin"][offer] = counts["huntskin"].get(offer, 0) + 1
    
    # ApuCash কাউন্ট
    for offer in scrape_apucash():
        counts["apucash"][offer] = counts["apucash"].get(offer, 0) + 1
    
    # PaidCash কাউন্ট
    for offer in scrape_paidcash():
        counts["paidcash"][offer] = counts["paidcash"].get(offer, 0) + 1
    
    save_counts(counts)
    return counts

def get_top_3(counts_dict):
    sorted_items = sorted(counts_dict.items(), key=lambda x: x[1], reverse=True)
    return sorted_items[:3]

def send_report():
    print("Generating top offers report...")
    counts = update_counts()
    
    message = "<b>📊 টপ অফার রিপোর্ট (গত ২ ঘণ্টা)</b>\n\n"
    has_any = False
    
    # Huntskin
    top_hunt = get_top_3(counts["huntskin"])
    if top_hunt:
        has_any = True
        message += "🔴 <b>Huntskin</b>\n"
        for i, (name, count) in enumerate(top_hunt, 1):
            message += f"{i}️⃣ {name} - {count} বার\n"
        message += "\n"
    
    # ApuCash
    top_apu = get_top_3(counts["apucash"])
    if top_apu:
        has_any = True
        message += "🟢 <b>ApuCash</b>\n"
        for i, (name, count) in enumerate(top_apu, 1):
            message += f"{i}️⃣ {name} - {count} বার\n"
        message += "\n"
    
    # PaidCash
    top_paid = get_top_3(counts["paidcash"])
    if top_paid:
        has_any = True
        message += "🪙 <b>PaidCash</b>\n"
        for i, (name, count) in enumerate(top_paid, 1):
            message += f"{i}️⃣ {name} - {count} বার\n"
    
    if not has_any:
        message += "❌ গত ২ ঘণ্টায় কোনো অফার পাওয়া যায়নি।"
    
    send_telegram(message)
    
    # কাউন্ট রিসেট (নতুন ২ ঘণ্টার জন্য)
    save_counts({"huntskin": {}, "apucash": {}, "paidcash": {}})
    print("Report sent and counts reset.")

def main():
    print("✅ টপ অফার রিপোর্ট বট চালু হয়েছে")
    send_telegram("✅ <b>টপ অফার রিপোর্ট বট চালু হয়েছে!</b>\n\nপ্রতি ২ ঘণ্টা পর টপ ৩ অফারের রিপোর্ট পাঠানো হবে।")
    
    last_report = time.time()
    
    while True:
        current_time = time.time()
        if current_time - last_report >= REPORT_INTERVAL:
            send_report()
            last_report = current_time
        time.sleep(60)  # প্রতি ১ মিনিটে চেক করবে

if __name__ == "__main__":
    main()

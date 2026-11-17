import asyncio
import time
import random
from curl_cffi.requests import AsyncSession  # הספרייה המשודרגת ל-JA3 Spoofing

payloads_list = []
TARGET_URL = "https://httpbin.org/post"

class Soldier:
    def __init__(self, soldier_id, payload, token):
        self.soldier_id = soldier_id
        self.payload = payload
        self.token = token 

    async def play(self):
        url = TARGET_URL
        custom_headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://ChatGPT.com",
            "Referer": "https://ChatGPT.com/",
            "X-Authorization": self.token
        }
        
        # --- יצירת AsyncSession עם JA3 Spoofing מובנה לכל חייל ---
        async with AsyncSession(impersonate="chrome120") as session:
            for shot_id in range(1, 11):
                # מרווח מותאם ל-Jitter (מניעת חניקה של ה-IP המקומי)
                await asyncio.sleep(random.uniform(0.3, 1.2))
                
                # לולאת ניסיונות חוזרים (Retries) עבור כדור בודד
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        print(f"[Soldier {self.soldier_id}] Aiming (Shot {shot_id}/10, Attempt {attempt+1}/{max_retries})...")
                        
                        response = await session.post(
                            url, 
                            json={"message": f"{self.payload} | shot_{shot_id}"}, 
                            headers=custom_headers,
                            timeout=4.0  # אופטימיזציה ל-4 שניות לשרידת Tarpitting
                        )
                        
                        status = response.status_code
                        if status == 200:
                            print(f"[+] [Soldier {self.soldier_id}] Fired Shot {shot_id}! Status: {status}")
                            break  # הצלחנו, יוצאים מלולאת ה-Retries ועוברים לכדור הבא
                        
                        # אם נתקלנו בחסימה זמנית או עומס
                        if status in [429, 403, 503, 502]:
                            print(f"[!] [Soldier {self.soldier_id}] Hit wall (Status {status}). Retrying in 1s...")
                            await asyncio.sleep(1.0)
                            
                    except (asyncio.TimeoutError, Exception) as e:
                        # אם הגענו לניסיון האחרון ועדיין נכשלנו
                        if attempt == max_retries - 1:
                            error_msg = str(e).split('\n')[0]
                            print(f"[-] [Soldier {self.soldier_id}] Shot {shot_id} failed completely: {error_msg}")
                        else:
                            # השהיה קצרה לפני הניסיון הבא באותו כדור
                            await asyncio.sleep(0.5)

def readrop(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                collect(line.strip())
    except FileNotFoundError:
        print("[-] File not found. Creating dummy data.")
        for i in range(10):
            collect(f"Dummy payload {i}")

def collect(line: str):
    if line:
        payloads_list.append(line)

# הכנת כיתת היורים (טעינת Payloads וטוקנים לכל חייל)
def start_sockets(num: int):
    kitat_yorim = []
    MY_AUTH_TOKEN = "Bearer eyJhbGciOi..." 
    
    for n in range(num):
        payload = payloads_list[n % len(payloads_list)] if payloads_list else "Empty"
        soldier = Soldier(n, payload, MY_AUTH_TOKEN)
        kitat_yorim.append(soldier)
    return kitat_yorim

async def send_requests(kitat_yorim):
    tasks = []
    for soldier in kitat_yorim:
        tasks.append(soldier.play())
    await asyncio.gather(*tasks)

async def main():
    print("[+] Step 1 & 2: Reading payloads...")
    readrop("my_payloads.txt")
    
    print("[+] Step 3: Positioning 100 soldiers (With Resilient JA3 Engine)...")
    kitat_yorim = start_sockets(100)
    
    print("[+] Step 4: FIRE!")
    
    start_time = time.time()
    await send_requests(kitat_yorim)
    end_time = time.time()
    
    total_duration = end_time - start_time
    total_requests = len(kitat_yorim) * 10 
    requests_per_second = total_requests / total_duration
    
    print("\n" + "="*40)
    print(f"[📊 TELEMETRY REPORT - PRODUCTION READY]")
    print(f"[*] Total Requests Sent (Max base): {total_requests}")
    print(f"[*] Total Time Elapsed: {total_duration:.2f} seconds")
    print(f"[*] Execution Speed: {requests_per_second:.2f} Requests/Second (RPS)")
    print("="*40 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
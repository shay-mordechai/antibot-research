import asyncio
import json
import uuid
import os
import time
import random
from playwright.async_api import async_playwright, Route

NUM = 5
ITERATIONS = 8 # הופחת ל-5 כדי למנוע קריסת DOM עקב אורך השיחה
RESULTS_LOG_FILE = "results_log.csv"

os.makedirs("success", exist_ok=True) # החזרנו את תיקיית ההצלחות
os.makedirs("fails", exist_ok=True)
os.makedirs("traces", exist_ok=True)
os.makedirs("chats", exist_ok=True)

if not os.path.exists(RESULTS_LOG_FILE):
    with open(RESULTS_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("Timestamp,WorkerID,TraceID,Status,Details\n")

def write_trace(worker_id, message):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] [*] Worker {worker_id}: {message}"
    print(log_line)
    trace_path = os.path.join("traces", f"worker_{worker_id}_trace.txt")
    with open(trace_path, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

def record_result(worker_id, trace_id, status, details=""):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    clean_details = details.replace(",", " ").replace("\n", " ") 
    log_line = f"{timestamp},{worker_id},{trace_id},{status},{clean_details}\n"
    
    with open(RESULTS_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)

async def run_worker(worker_id, browser, parser_data):
    api_headers = parser_data.get("headers", {})
    cookies = parser_data.get("cookies", {})
    sentinel_token = parser_data.get("finalize_payload", {}).get("token")

    chat_file = os.path.join("chats", f"worker_{worker_id}.txt")
    payloads_list = []
    if os.path.exists(chat_file):
        with open(chat_file, "r", encoding="utf-8") as f:
            payloads_list = [line.strip() for line in f if line.strip()]
            
    if not payloads_list:
        payloads_list = [f"Collision test message from worker {worker_id}"]

    desktop_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    context = await browser.new_context(
        user_agent=desktop_user_agent,
        viewport={"width": 1920, "height": 1080},
        is_mobile=False,
        has_touch=False
    )
    
    cookie_list = [{"name": str(k), "value": str(v), "url": "https://ChatGPT.com/"} 
                   for k, v in cookies.items() if k and v]
    await context.add_cookies(cookie_list)
    
    page = await context.new_page()
    
    # Listeners
    page.on("response", lambda response: 
            write_trace(worker_id, f"HTTP {response.status} from {response.url}") 
            if "backend-api/conversation" in response.url else None)
    page.on("console", lambda msg: 
            write_trace(worker_id, f"CONSOLE [{msg.type}]: {msg.text}") 
            if msg.type in ["error", "warning"] else None)

    async def intercept_api(route: Route):
        headers = dict(route.request.headers)
        if sentinel_token:
            headers["OpenAI-sentinel-proof-token"] = sentinel_token
            headers["OpenAI-sentinel-turnstile-token"] = sentinel_token
        await route.continue_(headers=headers)
    await page.route("**/backend-api/**", intercept_api)

    write_trace(worker_id, "Navigating to start a NEW conversation...")
    trace_id = "INIT"
    
    try:
        await page.goto("https://ChatGPT.com/", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_selector('nav', timeout=30000)
        
        input_box = page.locator('#prompt-textarea')
        await input_box.wait_for(state="visible", timeout=30000)
        
        write_trace(worker_id, "Waiting for initial SPA hydration...")
        await asyncio.sleep(5) 
        
        for iteration in range(1, ITERATIONS + 1):
            write_trace(worker_id, f"--- Starting Iteration {iteration}/{ITERATIONS} ---")
            
            trace_id = uuid.uuid4().hex[:6].upper()
            payload_line = payloads_list[(iteration - 1) % len(payloads_list)]
            msg_text = f"{payload_line} | Trace ID: [{trace_id}]"
            
            user_messages = page.locator('[data-message-author-role="user"]')
            assistant_messages = page.locator('[data-message-author-role="assistant"]')

            before_user = await user_messages.count()
            before_assistant = await assistant_messages.count()

            write_trace(worker_id, f"Sending message Trace ID: {trace_id}")
            
            await input_box.click()
            await input_box.fill(msg_text)
            await asyncio.sleep(1) 
            
            send_button = page.locator('button[data-testid="send-button"]')
            await send_button.wait_for(state="visible", timeout=15000)
            
            if not await send_button.is_enabled():
                write_trace(worker_id, "Send button disabled, waiting 2s...")
                await asyncio.sleep(2)
                
            await send_button.click()
            write_trace(worker_id, "Verifying User message injection...")

            user_confirmed = False
            for _ in range(30):
                if await user_messages.count() > before_user:
                    user_confirmed = True
                    break
                await asyncio.sleep(1)

            if not user_confirmed:
                raise Exception("User message never appeared in DOM. Possible 429 Rate Limit hit.")
            
            write_trace(worker_id, "User message confirmed. Waiting for Assistant response to start...")

            assistant_confirmed = False
            for _ in range(90):
                if await assistant_messages.count() > before_assistant:
                    assistant_confirmed = True
                    break
                await asyncio.sleep(1)

            if not assistant_confirmed:
                raise Exception("No new assistant response generated after 90 seconds.")

            write_trace(worker_id, "Response started. Waiting for text generation to finish...")
            stop_button = page.locator('button[data-testid="stop-button"]')
            try:
                await stop_button.wait_for(state="hidden", timeout=120000)
                write_trace(worker_id, "Text generation finished successfully.")
            except Exception:
                write_trace(worker_id, "Warning: Stop button didn't hide within 120s, UI might be stuck.")

            await asyncio.sleep(3)

            write_trace(worker_id, f"TRUE SUCCESS. Iteration {iteration} complete.")
            record_result(worker_id, trace_id, "SUCCESS", f"Completed Iteration {iteration}")
            
            # צילום מסך רק באיטרציה האחרונה, כדי לחסוך עומס I/O
            if iteration == ITERATIONS:
                try:
                    screenshot_filename = f"worker_{worker_id}_final_trace_{trace_id}.png"
                    await page.screenshot(path=os.path.join("success", screenshot_filename), timeout=5000)
                except Exception as e:
                    write_trace(worker_id, f"Screenshot saving failed: {e}")

            cooldown = random.uniform(8.0, 15.0)
            write_trace(worker_id, f"Cooling down for {cooldown:.1f} seconds...")
            await asyncio.sleep(cooldown)

    except Exception as e:
        error_msg = str(e)[:100]
        write_trace(worker_id, f"FAILED: {error_msg}")
        record_result(worker_id, trace_id, "FAILED", error_msg)
        try:
            fail_filename = f"fail_worker_{worker_id}_trace_{trace_id}.png"
            await page.screenshot(path=os.path.join("fails", fail_filename), timeout=5000) 
        except Exception:
            pass
    finally:
        write_trace(worker_id, "Closing context.")
        await context.close()

async def main():
    try:
        with open("session_ready.json", "r") as f:
            parser_data = json.load(f)
    except FileNotFoundError:
        print("[-] session_ready.json not found.")
        return

    print("[*] Verifying chat context files...")
    for i in range(NUM):
        chat_path = os.path.join("chats", f"worker_{i}.txt")
        if not os.path.exists(chat_path):
            with open(chat_path, "w", encoding="utf-8") as f:
                f.write(f"Initiating security analysis protocol for Worker {i}.\n")
                f.write(f"Checking trust boundaries for Iteration 2 context on Worker {i}.\n")
                f.write(f"Analyzing execution flow for Iteration 3 on Worker {i}.\n")

    print(f"[*] Starting {NUM} independent parallel conversations.")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        tasks = []
        for i in range(NUM):
            await asyncio.sleep(i * 3.5) 
            tasks.append(run_worker(i, browser, parser_data))
        
        await asyncio.gather(*tasks)
        
        await browser.close()
        print(f"[*] All workers finished their conversation cycles. Review {RESULTS_LOG_FILE} and the success/fails folders.")

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import json
import uuid
import os
import time
import random
import math
from playwright.async_api import async_playwright, Error as PlaywrightError

# Start with 5 to verify stability, then scale up to 100 for maximum stress
NUM_WORKERS = 5
ITERATIONS = 10 
RESULTS_LOG_FILE = "throughput_results.csv"

# Create directories for logs and telemetry
os.makedirs("traces", exist_ok=True)
os.makedirs("success", exist_ok=True)
os.makedirs("fails", exist_ok=True)
os.makedirs("chats", exist_ok=True)

if not os.path.exists(RESULTS_LOG_FILE):
    with open(RESULTS_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("Timestamp,WorkerID,TraceID,Status,Details\n")

def get_gaussian_delay(mean=25, std_dev=10):
    """
    Returns a human-like delay following a Gaussian distribution (התפלגות נורמלית).
    This mimics real human typing speed variations better than flat random ranges.
    """
    delay = random.gauss(mean, std_dev)
    return max(5, int(delay)) # Ensure delay is never non-positive

def write_trace(worker_id, message):
    """Silently logs execution traces to disk."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] [*] Worker {worker_id}: {message}"
    trace_path = os.path.join("traces", f"worker_{worker_id}_trace.txt")
    with open(trace_path, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

def record_result(worker_id, trace_id, status, details=""):
    """Records final iteration status to the central CSV for analysis."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    clean_details = details.replace(",", " ").replace("\n", " ")
    log_line = f"{timestamp},{worker_id},{trace_id},{status},{clean_details}\n"
    with open(RESULTS_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)

async def run_worker(worker_id, browser, parser_data):
    """
    Executes a worker in an isolated BrowserContext.
    Each worker targets the ROOT url to create a NEW conversation.
    This tests Account-Level Throughput instead of Thread-Level Locks.
    """
    cookies = parser_data.get("cookies", {})
    trace_id = "INIT"

    # Match worker to the respective chat file (using modulo if NUM_WORKERS > 5)
    file_index = worker_id % 5
    chat_file = os.path.join("chats", f"worker_{file_index}.txt")
    payloads_list = []
    if os.path.exists(chat_file):
        with open(chat_file, "r", encoding="utf-8") as f:
            payloads_list = [line.strip() for line in f if line.strip()]
            
    if not payloads_list:
        payloads_list = [f"Fallback payload from worker {worker_id}"]

    # Isolated context ensures unique cryptographic token generation per worker
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080}
    )
    
    # Inject authentication cookies
    await context.add_cookies([{"name": str(k), "value": str(v), "url": "https://ChatGPT.com/"}
                               for k, v in cookies.items() if k and v])

    page = await context.new_page()

    try:
        # Changed to root URL to force a new chat for every worker
        write_trace(worker_id, f"Navigating to NEW conversation...")
        await page.goto("https://ChatGPT.com/", wait_until="domcontentloaded", timeout=60000)
        
        # Wait for SPA hydration
        await asyncio.sleep(5)
        
        for iteration in range(1, min(ITERATIONS, len(payloads_list)) + 1):
            trace_id = uuid.uuid4().hex[:6].upper()
            write_trace(worker_id, f"--- Starting Iteration {iteration} ---")
            
            stop_button = page.locator('button[data-testid="stop-button"]').first
            
            # Ensure the UI is ready to accept input
            try:
                await stop_button.wait_for(state="hidden", timeout=30000)
            except:
                pass # Ignore if it doesn't hide cleanly, attempt to type anyway
                
            msg_text = f"{payloads_list[iteration - 1]} | Trace ID: [{trace_id}]"
            
            write_trace(worker_id, "Typing payload...")
            
            # Use a retry loop to handle React DOM updates during typing
            typed_successfully = False
            for attempt in range(3):
                try:
                    # Dynamically locate the input box
                    input_box = page.locator('#prompt-textarea').first
                    await input_box.wait_for(state="visible", timeout=15000)
                    
                    # Click to focus the element with increased timeout for high CPU load
                    await input_box.click(timeout=15000)
                    await input_box.fill("", timeout=15000)
                    await asyncio.sleep(0.2)
                    
                    # Use global keyboard typing with GAUSSIAN delays 
                    # This is significantly more realistic than uniform random ranges
                    for char in msg_text:
                        await page.keyboard.type(char, delay=get_gaussian_delay(mean=25, std_dev=12))
                    
                    typed_successfully = True
                    break # Exit retry loop on success
                except PlaywrightError as e:
                    write_trace(worker_id, f"Typing attempt {attempt + 1} interrupted by UI shift or timeout. Retrying...")
                    await asyncio.sleep(1)
            
            if not typed_successfully:
                raise Exception("Failed to type payload after multiple attempts.")
                
            await asyncio.sleep(0.5)
            
            write_trace(worker_id, "Attempting to send...")
            send_button = page.locator('button[data-testid="send-button"]').first
            
            if await send_button.is_visible() and await send_button.is_enabled():
                # Increased timeout for the click action
                await send_button.click(timeout=15000)
            else:
                # Press Enter while focus is still in the input box
                await page.keyboard.press("Enter")
                
            write_trace(worker_id, "Waiting for backend processing...")
            
            # Check completion by waiting for the stop button to disappear
            try:
                await stop_button.wait_for(state="hidden", timeout=15000)
                write_trace(worker_id, f"Iteration {iteration} processed.")
                record_result(worker_id, trace_id, "SUCCESS", f"Iteration {iteration} processed")
            except Exception:
                write_trace(worker_id, f"Iteration {iteration} timed out (Throttled).")
                record_result(worker_id, trace_id, "TIMEOUT", f"Iteration {iteration} backend throttle")
            
            # Random cooldown to prevent local resource spikes
            await asyncio.sleep(random.uniform(5, 10))

    except Exception as e:
        record_result(worker_id, trace_id, "FAILED", str(e)[:50])
        write_trace(worker_id, f"CRITICAL ERROR: {str(e)[:50]}")
    finally:
        await context.close()

async def main():
    try:
        with open("session_ready.json", "r", encoding="utf-8") as f:
            parser_data = json.load(f)
    except FileNotFoundError:
        print("[-] session_ready.json not found.")
        return

    print(f"[*] Commencing Account-Level Throughput Test (בדיקת תפוקה כללית).")
    print(f"[*] Launching 1 Core Browser with {NUM_WORKERS} Isolated Contexts...")
    print(f"[*] Each worker will start a NEW conversation to bypass thread locks.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        tasks = []
        for i in range(NUM_WORKERS):
            # Small stagger to prevent local CPU bottlenecking during context creation
            await asyncio.sleep(0.5)
            # We no longer pass conv_id, as we are creating new ones
            tasks.append(run_worker(i, browser, parser_data))
            
        print(f"[*] Firing all {NUM_WORKERS} workers concurrently!")
        await asyncio.gather(*tasks)
        
        await browser.close()
        print(f"[*] Throughput test complete. Review {RESULTS_LOG_FILE}.")

if __name__ == "__main__":
    asyncio.run(main())
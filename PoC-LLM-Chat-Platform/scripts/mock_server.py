import asyncio
import json
import uuid
import os
import time
from curl_cffi.requests import AsyncSession
from playwright.async_api import async_playwright

NUM_WORKERS = 100 # Scaled up to 100 concurrent workers
RESULTS_LOG_FILE = "hybrid_results_log.csv"

# Create necessary directories for traces and logs
os.makedirs("traces", exist_ok=True)

# Initialize the CSV log file with appropriate headers
if not os.path.exists(RESULTS_LOG_FILE):
    with open(RESULTS_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("Timestamp,WorkerID,TraceID,Status,Details\n")

def record_result(worker_id, trace_id, status, details=""):
    """
    Records the execution result into the CSV file for analysis.
    Logs are appended securely.
    """
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    clean_details = details.replace(",", " ").replace("\n", " ") 
    log_line = f"{timestamp},{worker_id},{trace_id},{status},{clean_details}\n"
    
    with open(RESULTS_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)

async def harvest_fresh_tokens(parser_data, conv_id):
    """
    Phase 1: Opens a single headless browser to generate and intercept 
    perfectly fresh Sentinel tokens and cookies.
    """
    print("[*] Phase 1: Launching Browser Sitter to harvest fresh Sentinel tokens...")
    cookies = parser_data.get("cookies", {})
    captured_headers = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        # Inject known session cookies into the browser context
        await context.add_cookies([{"name": str(k), "value": str(v), "url": "https://ChatGPT.com/"} 
                                   for k, v in cookies.items() if k and v])
        
        page = await context.new_page()

        # Route interceptor to steal headers when the UI sends the message
        async def intercept_request(route, request):
            nonlocal captured_headers
            # Broadened the URL check to catch both standard and /f/ conversation endpoints
            if "backend-api" in request.url and "conversation" in request.url and request.method == "POST":
                captured_headers = await request.all_headers()
                print("[+] Successfully captured fresh network headers (including Sentinel tokens)!")
            await route.continue_()

        # Intercept all backend-api traffic to ensure we do not miss the POST request
        await page.route("**/backend-api/**", intercept_request)

        print(f"[*] Navigating to conversation {conv_id}...")
        await page.goto(f"https://ChatGPT.com/c/{conv_id}", wait_until="domcontentloaded", timeout=60000)
        
        input_box = page.locator('#prompt-textarea').first
        await input_box.wait_for(state="visible", timeout=30000)
        
        # Type a primer message to trigger the backend request using robust typing simulation
        print("[*] Triggering primer message to force token generation...")
        await input_box.click()
        await input_box.fill("")
        await asyncio.sleep(0.5)
        
        # Use type() instead of fill() to ensure React state registers the input
        await input_box.type("Initializing high-volume network test...", delay=20)
        await asyncio.sleep(1)
        
        send_button = page.locator('button[data-testid="send-button"]').first
        
        # Check if the send button is enabled, otherwise use the Enter key fallback
        if not await send_button.is_enabled():
            print("[*] Send button disabled, pressing 'Enter' key as fallback...")
            await input_box.press("Enter")
        else:
            await send_button.click()

        # Wait until our interceptor catches the headers (increased timeout to 20s)
        for _ in range(20):
            if captured_headers:
                break
            await asyncio.sleep(1)

        await browser.close()
        
    if not captured_headers:
        raise Exception("Failed to harvest headers from the browser.")
        
    return captured_headers

async def fire_api_request(worker_id, session, headers, base_payload):
    """
    Phase 2: Fires a raw API request mimicking a Chrome TLS fingerprint.
    """
    trace_id = uuid.uuid4().hex[:6].upper()
    
    # Deep copy payload so workers do not overwrite each other's data
    payload = json.loads(json.dumps(base_payload))
    payload["messages"][0]["id"] = str(uuid.uuid4())
    payload["messages"][0]["content"]["parts"] = [f"Hybrid API Injection | Worker {worker_id} | Trace ID: [{trace_id}]"]
    
    # Copy headers and inject a fresh turn-trace-id for the Web Application Firewall (WAF)
    req_headers = headers.copy()
    req_headers["x-oai-turn-trace-id"] = str(uuid.uuid4())
    
    start_time = time.time()
    try:
        response = await session.post(
            "https://ChatGPT.com/backend-api/f/conversation",
            headers=req_headers,
            json=payload,
            timeout=30 # Prevent hanging on network drops
        )
        
        elapsed = time.time() - start_time
        status = response.status_code
        print(f"[*] Worker {worker_id:<3} | HTTP {status} | Time: {elapsed:.2f}s | Trace: {trace_id}")
        record_result(worker_id, trace_id, f"HTTP {status}", f"Time: {elapsed:.2f}s")
        
    except Exception as e:
        print(f"[-] Worker {worker_id:<3} | ERROR | {str(e)[:50]}")
        record_result(worker_id, trace_id, "ERROR", str(e)[:50])

async def main():
    try:
        with open("session_ready.json", "r", encoding="utf-8") as f:
            parser_data = json.load(f)
    except FileNotFoundError:
        print("[-] session_ready.json not found.")
        return

    base_payload = parser_data.get("conversation_payload", {})
    conv_id = base_payload.get("conversation_id")
    
    if not conv_id:
        print("[-] Error: 'conversation_id' missing from JSON.")
        return

    try:
        # Step 1: Harvest the fresh tokens using a single browser
        fresh_headers = await harvest_fresh_tokens(parser_data, conv_id)
        
        print("\n[*] Phase 2: Commencing high-speed API Fuzzing...")
        print(f"[*] Firing {NUM_WORKERS} concurrent requests (בקשות מקבילות)...")
        
        # Step 2: Blast the API using curl_cffi to mimic Chrome TLS
        async with AsyncSession(impersonate="chrome120") as session:
            tasks = [fire_api_request(i, session, fresh_headers, base_payload) for i in range(NUM_WORKERS)]
            
            # Execute all tasks concurrently (בו זמנית)
            await asyncio.gather(*tasks)
            
        print(f"\n[*] Execution finished. Results written to {RESULTS_LOG_FILE}.")
        
    except Exception as e:
        print(f"[-] Critical Error during execution: {e}")

if __name__ == "__main__":
    asyncio.run(main())
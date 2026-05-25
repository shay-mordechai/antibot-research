import asyncio
import time
import json
import os
from playwright.async_api import async_playwright
from curl_cffi import requests

TARGET_URL = "https://thehackernews.com/"
OUTPUT_FILE = "../outputs/exp_001_results.json"

async def test_v8_dom_environment():
    """Tier 1: Testing standard Browser Automation (V8/Renderer detection)"""
    print("[*] Running Tier 1: V8/DOM Environment (Playwright)...")
    start_time = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )

        try:
            response = await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=15000)
            status = response.status
            content = await page.content()

            # WAFs usually throw 403 or inject a JS challenge page (which lacks normal content)
            is_blocked = status == 403 or "cf-challenge" in content.lower()
        except Exception as e:
            status, is_blocked = 0, True

        await browser.close()

    elapsed = round(time.time() - start_time, 2)
    print(f"    -> Playwright Result | Status: {status} | Blocked: {is_blocked} | Time: {elapsed}s\n")

    return {
        "method": "Playwright_Headless",
        "engine": "V8_Renderer",
        "status": status,
        "blocked": is_blocked,
        "time_elapsed": elapsed
    }

def test_network_tls_impersonation():
    """Tier 3: Testing Network-Level Impersonation (Bypassing V8 execution)"""
    print("[*] Running Tier 3: Network TLS/HTTP2 Impersonation (curl_cffi)...")
    start_time = time.time()

    session = requests.Session(impersonate="chrome120")

    try:
        response = session.get(TARGET_URL, timeout=15)
        status = response.status_code
        content = response.text
        is_blocked = status == 403 or "cf-challenge" in content.lower()
    except Exception as e:
        status, is_blocked = 0, True

    elapsed = round(time.time() - start_time, 2)
    print(f"    -> Curl_CFFI Result | Status: {status} | Blocked: {is_blocked} | Time: {elapsed}s\n")

    return {
        "method": "Curl_CFFI_Impersonation",
        "engine": "Network_JA3",
        "status": status,
        "blocked": is_blocked,
        "time_elapsed": elapsed
    }

async def main():
    os.makedirs("../outputs", exist_ok=True)

    print("=== Anti-Bot Detection: Exp 001 ===")

    # Run the tests
    tier_1_result = await test_v8_dom_environment()
    time.sleep(2) # Cool down
    tier_3_result = test_network_tls_impersonation()

    results = [tier_1_result, tier_3_result]

    # Save output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    print(f"[V] Experiment 001 Complete. Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json
import os
import re
import logging
from typing import List
from playwright.async_api import async_playwright, Page, Response, ConsoleMessage
import google.generativeai as genai

from dotenv import load_dotenv
load_dotenv(dotenv_path="config/.env", override=True)

# ==============================================================================
# ⚙️ CONFIGURATION & LOGGING
# ==============================================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [DAST-AGENT] %(message)s")
BENIGN_PAYLOAD = "test_diag_reflection_123"

# --- THE SET-OF-MARK (SoM) JAVASCRIPT PAYLOAD ---
SOM_JS_SNIPPET = """
() => {
    const containerId = 'qa-diagnostic-som-overlays';
    const existingContainer = document.getElementById(containerId);
    if (existingContainer) existingContainer.remove();

    const overlayContainer = document.createElement('div');
    overlayContainer.id = containerId;
    overlayContainer.style.position = 'absolute';
    overlayContainer.style.top = '0';
    overlayContainer.style.left = '0';
    overlayContainer.style.width = '100%';
    overlayContainer.style.height = '100%';
    overlayContainer.style.pointerEvents = 'none'; 
    overlayContainer.style.zIndex = '2147483647'; 
    document.body.appendChild(overlayContainer);

    const selectors = ['input:not([type="hidden"])', 'textarea', 'button', 'select', '[role="button"]'].join(', ');
    const elements = document.querySelectorAll(selectors);
    let idCounter = 1;

    elements.forEach((el) => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);

        if (rect.width === 0 || rect.height === 0 || style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
            return;
        }

        el.setAttribute('data-diagnostic-id', idCounter);

        const box = document.createElement('div');
        box.style.position = 'absolute';
        box.style.left = `${rect.left + window.scrollX}px`;
        box.style.top = `${rect.top + window.scrollY}px`;
        box.style.width = `${rect.width}px`;
        box.style.height = `${rect.height}px`;
        box.style.border = '3px solid #FF00FF'; 
        box.style.boxSizing = 'border-box';

        const label = document.createElement('div');
        label.textContent = `[${idCounter}]`;
        label.style.position = 'absolute';
        label.style.top = '-15px'; 
        label.style.left = '-3px';
        label.style.backgroundColor = '#FF00FF';
        label.style.color = '#FFFFFF';
        label.style.fontSize = '14px';
        label.style.fontWeight = '900';
        label.style.padding = '2px 6px';
        label.style.lineHeight = '1';
        label.style.fontFamily = 'monospace'; 
        
        box.appendChild(label);
        overlayContainer.appendChild(box);
        idCounter++;
    });
    return idCounter - 1; 
}
"""

class UIUXDiagnosticAgent:
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.screenshot_path = "data/screenshots/state_capture.png"
        
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY environment variable is missing.")
        
        genai.configure(api_key=self.api_key)
        # Using Gemini 1.5 Pro for accurate OCR and reasoning
        self.vlm = genai.GenerativeModel('gemini-2.5-flash')

    def _setup_observability(self, page: Page):
        async def handle_response(response: Response):
            if response.request.resource_type in ["fetch", "xhr", "document"]:
                logging.info(f"Network [HTTP {response.status}] {response.request.method} {response.url}")
                
        async def handle_console(msg: ConsoleMessage):
            if BENIGN_PAYLOAD in msg.text:
                logging.warning(f"🚨 Reflection Detected in Console: {msg.text}")
            else:
                logging.debug(f"Console [{msg.type}]: {msg.text}")

        page.on("response", handle_response)
        page.on("console", handle_console)

    async def _map_ui_visually(self, page: Page) -> List[int]:
        logging.info("[*] Injecting Set-of-Mark (SoM) overlays into the DOM...")
        
        marked_count = await page.evaluate(SOM_JS_SNIPPET)
        logging.info(f"[*] SoM injection complete. Marked {marked_count} interactive elements.")

        await page.screenshot(path=self.screenshot_path, full_page=True)
        logging.info("[*] Screenshot captured. Uploading to Vision API...")

        prompt = """
        You are an expert QA Automation Engineer. I have applied a Set-of-Mark (SoM) overlay to this UI.
        Interactive elements are wrapped in magenta boxes with an ID tag (e.g., [1], [2]).
        
        Identify the IDs of the TEXT INPUT fields or SEARCH BARS only. Do not include buttons.
        Return ONLY a valid JSON list of integers representing the IDs. Do not include markdown or explanations.
        Example: [1, 4, 7]
        """
        
        try:
            sample_file = genai.upload_file(path=self.screenshot_path)
            response = self.vlm.generate_content([sample_file, prompt])
            
            clean_json = re.sub(r"^```json\s*|\s*```$", "", response.text.strip())
            target_ids = json.loads(clean_json)
            
            logging.info(f"[*] Vision API identified input fields with IDs: {target_ids}")
            return target_ids
            
        except Exception as e:
            logging.error(f"[-] Vision API error: {e}")
            return []

    async def _execute_diagnostics(self, page: Page, target_ids: List[int]):
        for diagnostic_id in target_ids:
            selector = f'[data-diagnostic-id="{diagnostic_id}"]'
            locator = page.locator(selector)
            
            if await locator.count() > 0:
                logging.info(f"[*] Targeting Input ID [{diagnostic_id}]")
                await locator.scroll_into_view_if_needed()
                
                # Human telemetry: click and type sequentially
                await locator.click(delay=200)
                await locator.fill("") 
                await locator.press_sequentially(BENIGN_PAYLOAD, delay=120)
                
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)
            else:
                logging.warning(f"[-] Could not find element in DOM with ID [{diagnostic_id}]")

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=50)
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()

            self._setup_observability(page)

            try:
                logging.info(f"[*] Navigating to {self.target_url}")
                await page.goto(self.target_url, wait_until="networkidle")
                
                target_ids = await self._map_ui_visually(page)

                if target_ids:
                    await self._execute_diagnostics(page, target_ids)
                else:
                    logging.warning("[-] No input fields mapped. Aborting.")

                logging.info("[*] Diagnostic routine complete. Waiting for final network logs...")
                await asyncio.sleep(3)

            except Exception as e:
                logging.error(f"[-] Execution halted: {e}")
            finally:
                if os.path.exists(self.screenshot_path):
                    os.remove(self.screenshot_path)
                await browser.close()
                logging.info("[*] Session terminated cleanly.")

if __name__ == "__main__":
    # Fetch the target from the .env file, fallback to example.com if missing
    TARGET = os.getenv("TARGET_URL", "https://example.com")
    agent = UIUXDiagnosticAgent(target_url=TARGET)
    asyncio.run(agent.run())

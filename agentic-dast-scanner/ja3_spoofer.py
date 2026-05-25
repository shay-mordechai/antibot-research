from curl_cffi import requests
from bs4 import BeautifulSoup
import time
import random

TARGET_URLS = [
    # --- Category 1: Browser Research & Anti-Bot ---
    "https://thehackernews.com/2026/03/aitm-phishing-targets-tiktok-business.html",
    "https://thehackernews.com/2026/03/apple-fixes-webkit-vulnerability.html",
    "https://thehackernews.com/2026/03/google-fixes-two-chrome-zero-days.html",
    "https://thehackernews.com/2026/03/new-chrome-vulnerability-let-malicious.html",

    # --- Category 2: Infostealers & Credential Harvesting ---
    "https://thehackernews.com/2026/03/deepload-malware-uses-clickfix-and-wmi.html",
    "https://thehackernews.com/2026/03/glassworm-malware-uses-solana-dead.html",
    "https://thehackernews.com/2026/03/malicious-npm-package-posing-as.html",
    "https://thehackernews.com/2026/03/starkiller-phishing-suite-uses-aitm.html",

    # --- Category 3: AI Agents & AI Security ---
    "https://thehackernews.com/2026/03/claude-extension-flaw-enabled-zero.html",
    "https://thehackernews.com/2026/03/researchers-trick-perplexitys-comet-ai.html",
    "https://thehackernews.com/2026/03/how-ceros-gives-security-teams.html",

    # --- Category 4: Web Security & Supply Chain ---
    "https://thehackernews.com/2026/03/webrtc-skimmer-bypasses-csp-to-steal.html",
    "https://thehackernews.com/2026/03/claude-code-security-and-magecart.html"
]

def fetch_full_text(session, url):
    print(f"[*] Sending spoofed request to: {url}")
    try:
        # We use the session to make the request.
        # The library handles all the complex TLS and HTTP/2 spoofing automatically.
        response = session.get(url, timeout=30)

        # If Cloudflare blocks us, the status code will usually be 403 (Forbidden)
        if response.status_code == 403:
             return url, "[!] Blocked by Cloudflare (403 Forbidden)."

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract the Title
        title_element = soup.select_one(".story-title a")
        title = title_element.get_text(strip=True) if title_element else "Unknown Title"

        # Extract the Full Article Body
        article_body = soup.select_one(".articlebody")

        if article_body:
            text = article_body.get_text(separator='\n\n', strip=True)
            return title, text
        else:
            return url, "[!] Connected successfully, but could not find the article body."

    except Exception as e:
        return url, f"Error: {str(e)}"

def main():
    print("[*] Initializing advanced JA3/HTTP2 spoofing session...")

    # --- THIS IS THE MAGIC (זה הקסם) ---
    # 1. Advanced Session Management: requests.Session() keeps cookies intact between requests.
    # 2. JA3 Spoofing: impersonate="chrome120" perfectly copies the TLS/HTTP2 fingerprint of Chrome 120.
    session = requests.Session(impersonate="chrome120")

    filename = "Spoofed_Articles_Report.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write("=== ADVANCED JA3 SPOOFING EXTRACTION ===\n\n")

        for url in TARGET_URLS:
            title, full_text = fetch_full_text(session, url)

            f.write(f"Title: {title}\n")
            f.write(f"URL: {url}\n")
            f.write("-" * 80 + "\n")
            f.write(f"{full_text}\n\n")
            f.write("=" * 80 + "\n\n")

            print(f"[+] Successfully extracted: {title}")

            # Human-like delay
            sleep_time = random.uniform(4.0, 7.0)
            print(f"[*] Sleeping for {sleep_time:.2f} seconds...\n")
            time.sleep(sleep_time)

    print(f"[V] Mission Complete! Full articles saved to {filename}")

if __name__ == "__main__":
    main()

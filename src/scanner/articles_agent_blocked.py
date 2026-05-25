import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# The exact URLs of the 13 articles you want to extract
# IMPORTANT: Replace the "https://..." placeholders with the real links from your data!
TARGET_URLS = [
    # --- Category 1: Browser Research & Anti-Bot ---
    "https://thehackernews.com/2026/03/aitm-phishing-targets-tiktok-business.html", # AitM Phishing Targets TikTok Business Accounts Using Cloudflare Turnstile Evasion
    "https://thehackernews.com/2026/03/apple-fixes-webkit-vulnerability.html",      # Apple Fixes WebKit Vulnerability Enabling Same-Origin Policy Bypass
    "https://thehackernews.com/2026/03/google-fixes-two-chrome-zero-days.html",     # Google Fixes Two Chrome Zero-Days Exploited in the Wild Affecting Skia and V8
    "https://thehackernews.com/2026/03/new-chrome-vulnerability-extensions.html",   # New Chrome Vulnerability Let Malicious Extensions Escalate Privileges

    # --- Category 2: Infostealers & Credential Harvesting ---
    "https://thehackernews.com/placeholder-deepload",  # DeepLoad Malware Uses ClickFix
    "https://thehackernews.com/placeholder-glassworm", # GlassWorm Malware Uses Solana Dead Drops
    "https://thehackernews.com/placeholder-openclaw",  # Malicious npm Package Posing as OpenClaw
    "https://thehackernews.com/placeholder-starkiller",# Starkiller Phishing Suite Uses AitM Reverse Proxy

    # --- Category 3: AI Agents & AI Security ---
    "https://thehackernews.com/placeholder-claude-ext",# Claude Extension Flaw Enabled Zero-Click XSS
    "https://thehackernews.com/placeholder-perplexity",# Researchers Trick Perplexity's Comet AI Browser
    "https://thehackernews.com/placeholder-ceros",     # How Ceros Gives Security Teams Visibility in Claude Code

    # --- Category 4: Web Security & Supply Chain ---
    "https://thehackernews.com/placeholder-webrtc",    # WebRTC Skimmer Bypasses CSP
    "https://thehackernews.com/placeholder-magecart"   # Claude Code Security and Magecart
]

async def fetch_full_text(page, url):
    print(f"[*] Navigating to: {url}")
    try:
        # Go to the article URL
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Get the HTML content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        # Extract the Title
        title_element = soup.select_one(".story-title a")
        title = title_element.get_text(strip=True) if title_element else "Unknown Title"

        # Extract the Full Article Body
        article_body = soup.select_one(".articlebody")

        if article_body:
            # Clean up the text, preserving paragraphs
            text = article_body.get_text(separator='\n\n', strip=True)
            return title, text
        else:
            return url, "[!] Could not find the article body. Playwright might be blocked by Cloudflare/Anti-Bot!"

    except Exception as e:
        print(f"[!] Error fetching {url}: {e}")
        return url, f"Error: {str(e)}"

async def main():
    async with async_playwright() as p:
        # Using headless=True. If you get blocked, change to headless=False to debug visually!
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        filename = "My_13_Browser_Research_Articles.txt"

        with open(filename, "w", encoding="utf-8") as f:
            f.write("=== MY 13 TARGETED BROWSER SECURITY ARTICLES ===\n\n")

            for url in TARGET_URLS:
                # Skip the placeholders if you haven't replaced them yet
                if "placeholder" in url:
                    print(f"[-] Skipping placeholder URL: {url}")
                    continue

                title, full_text = await fetch_full_text(page, url)

                # Write the article to our text file
                f.write(f"Title: {title}\n")
                f.write(f"URL: {url}\n")
                f.write("-" * 80 + "\n")
                f.write(f"{full_text}\n\n")
                f.write("=" * 80 + "\n\n")

                print(f"[+] Successfully extracted: {title}")

                # Important: Sleep for a few seconds to avoid triggering Rate Limits
                await asyncio.sleep(3)

        print(f"\n[V] Mission Complete! Full articles saved to {filename}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

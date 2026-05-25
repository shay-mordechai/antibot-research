import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from config/.env
load_dotenv("config/.env")

# Configure your API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("[!] Error: GEMINI_API_KEY not found in config/.env")
    exit(1)

genai.configure(api_key=api_key)

# Using Gemini 2.5 Flash as requested (Fast and cost-effective)
model = genai.GenerativeModel('gemini-2.5-flash')

def generate_intel(article_content):
    prompt = f"""
    You are a Senior Cyber Threat Intelligence (CTI) Analyst.
    Analyze the following technical article and provide a structured report in English.

    1. **Executive Summary**: A 2-sentence non-technical overview.
    2. **Technical Deep-Dive**: 3 bullet points explaining the 'How it works' (focus on exploit logic).
    3. **Indicators of Compromise (IoCs)**: List any IPs, Domains, or CVEs found.
    4. **Mitigation Strategy**: How should a defender block this specific attack?

    Article Content:
    {article_content}
    """

    response = model.generate_content(prompt)
    return response.text

def main():
    input_file = "Spoofed_Articles_Report.txt"
    output_file = "Final_Threat_Intel_Report.md"

    if not os.path.exists(input_file):
        print(f"[!] Error: {input_file} not found. Run the spoofer first!")
        return

    print("[*] Reading raw research data...")
    with open(input_file, "r", encoding="utf-8") as f:
        raw_data = f.read()

    # Split the file by the separator used in the spoofer
    articles = [a.strip() for a in raw_data.split("=" * 80) if len(a.strip()) > 100]

    print(f"[*] Found {len(articles)} articles. Starting Intelligence Generation...")

    with open(output_file, "w", encoding="utf-8") as out:
        out.write("# 🛡️ Automated Threat Intelligence Report\n\n")

        for i, article in enumerate(articles):
            print(f"[+] Processing Article {i+1}/{len(articles)}...")

            try:
                intel = generate_intel(article)
                out.write(f"## Research Item {i+1}\n")
                out.write(intel + "\n\n")
                out.write("---\n\n")

                # Rate Limiting: Wait 15 seconds to stay under 5 RPM (Requests Per Minute)
                if i < len(articles) - 1:
                    print("[*] Rate Limiting: Sleeping for 15s...")
                    time.sleep(15)

            except Exception as e:
                print(f"[!] Error processing article {i+1}: {e}")
                if "429" in str(e):
                    print("[!] Quota Exceeded. Sleeping for 60s before retry...")
                    time.sleep(60)
                continue

    print(f"\n[V] Mission Complete! Final report saved to {output_file}")

if __name__ == "__main__":
    main()

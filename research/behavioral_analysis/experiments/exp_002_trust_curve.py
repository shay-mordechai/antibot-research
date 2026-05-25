import time
import random
import json
import os
import matplotlib.pyplot as plt
from curl_cffi import requests

TARGET_URL = "https://thehackernews.com/"
MAX_REQUESTS = 25
OUTPUT_DIR = "../outputs"

def classify_block(status, text):
    """
    Classifies the severity of the WAF intervention.
    Returns: (severity_level, string_label)
    """
    if status in [403, 401]:
        return 2, "hard_block"
    if status == 429:
        return 2, "rate_limit"

    text_lower = text.lower()
    if "cf-challenge" in text_lower or "attention required" in text_lower:
        return 1, "js_challenge"

    return 0, "ok"

def run_degradation_test(profile_name, max_reqs=MAX_REQUESTS, use_delay=False):
    print(f"\n[*] Starting Test Profile: {profile_name}")

    session = requests.Session(impersonate="chrome120")
    telemetry_data = []
    global_start = time.time()

    for i in range(1, max_reqs + 1):
        req_start = time.time()

        try:
            response = session.get(f"{TARGET_URL}?req_id={i}", timeout=15)
            status = response.status_code
            text = response.text
            cookies_count = len(session.cookies.get_dict())

            # Extract headers for research snapshot
            req_headers = dict(response.request.headers)
            headers_sample = {
                "user-agent": req_headers.get("User-Agent", "Missing"),
                "accept": req_headers.get("Accept", "Missing")
            }
        except Exception as e:
            print(f"[-] Request {i} Failed: {e}")
            status, text, cookies_count, headers_sample = 0, "", 0, {}

        elapsed_req = round(time.time() - req_start, 2)
        elapsed_total = round(time.time() - global_start, 2)

        severity, label = classify_block(status, text)

        print(f"   -> Req {i:02d} | Status: {status} | Block: {label.upper()} | Cookies: {cookies_count} | Total: {elapsed_total}s")

        telemetry_data.append({
            "request_id": i,
            "status": status,
            "severity": severity,
            "block_type": label,
            "cookies_count": cookies_count,
            "elapsed_req": elapsed_req,
            "elapsed_total": elapsed_total,
            "headers_sample": headers_sample
        })

        if severity == 2:
            print(f"[!] Hard Block Threshold Reached at Request {i}.")
            break

        if use_delay and i < max_reqs:
            time.sleep(random.uniform(2.0, 5.0))

    return telemetry_data

def generate_graph(results, filepath):
    """Generates a visual representation of session degradation."""
    plt.figure(figsize=(10, 5))

    colors = ['blue', 'red', 'green']

    for profile_id, (profile_key, data) in enumerate(results["profiles"].items()):
        x = [d["request_id"] for d in data]
        y = [d["severity"] for d in data]

        plt.plot(x, y, marker='o', linestyle='-', color=colors[profile_id], label=profile_key.replace("_", " ").title())

    plt.yticks([0, 1, 2], ['200 OK', 'JS Challenge', 'Hard Block (403/429)'])
    plt.xlabel('Request ID Number')
    plt.ylabel('WAF Mitigation Level')
    plt.title('WAF Block Thresholds: Velocity vs. Trust Decay')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)

    plt.savefig(filepath)
    print(f"\n[+] Graph saved to {filepath}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    json_path = os.path.join(OUTPUT_DIR, "exp_002_trust_curve.json")
    graph_path = os.path.join(OUTPUT_DIR, "exp_002_graph.png")

    results = {
        "experiment": "002_session_degradation",
        "target": TARGET_URL,
        "profiles": {}
    }

    # 1. Baseline Control
    results["profiles"]["control"] = run_degradation_test("Control Baseline", max_reqs=1, use_delay=False)
    print("\n[*] Cooling down IP for 10 seconds...")
    time.sleep(10)

    # 2. Aggressive Profile
    results["profiles"]["aggressive"] = run_degradation_test("Aggressive Bot (0s delay)", max_reqs=MAX_REQUESTS, use_delay=False)
    print("\n[*] Cooling down IP for 10 seconds...")
    time.sleep(10)

    # 3. Human Mimicry Profile
    results["profiles"]["human_mimicry"] = run_degradation_test("Human Mimicry (2-5s delay)", max_reqs=MAX_REQUESTS, use_delay=True)

    # Save Data
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print(f"\n[+] Telemetry saved to {json_path}")

    # Generate Visualization
    generate_graph(results, graph_path)

if __name__ == "__main__":
    main()

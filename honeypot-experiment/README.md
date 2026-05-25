# 🔬 Anti-Bot Detection & Evasion Research Framework

![Status](https://img.shields.io/badge/status-research--in--progress-yellow)

> **Authored by Shay Mordechai**
> This experimental framework builds upon my theoretical research into OS Internals, V8 Architecture, and Browser Privilege Boundaries. You can read the foundational theory behind why browser engines fail at isolation in my [Security Research Journal](https://github.com/shay-mordechai/security-research-journal).

## 📖 Overview
This repository explores how modern anti-bot systems (e.g., Cloudflare Turnstile, Akamai) detect automated traffic. Rather than focusing solely on "bypassing" Web Application Firewalls (WAF), this framework aims to analyze, measure, and understand the specific triggers that cause trust degradation in automated sessions.

## 🧪 Active Experiments

### [Experiment 001: DOM/V8 Fingerprinting vs. TLS Impersonation](docs/experiment_001_dom_vs_tls.md)
Comparing the block rates of standard browser automation (Playwright/V8) vs. native network impersonation (curl_cffi/JA3). Proves that perfectly aligning the network fingerprint forces the WAF to bypass aggressive V8 JavaScript challenges.

### [Experiment 002: Session Degradation & Block Thresholds](docs/experiment_002_trust_curve.md)
Mapping the exact thresholds where a WAF drops Session Trust. By comparing an "Aggressive Bot" (0s delay) with "Human Mimicry" (randomized jitter), we mapped progressive mitigation behaviors (e.g., silently dropping `cf_clearance` cookies before issuing a hard 403).

## 🏗️ Getting Started
To run these experiments locally and generate your own telemetry graphs:

```bash
# 1. Clone the repository
git clone https://github.com/shay-mordechai/antibot-research.git
cd antibot-research

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Run the degradation test (generates a graph in /outputs)
python experiments/exp_002_trust_curve.py
```
Disclaimer: This repository is intended for educational purposes, security research, and defensive development. Always ensure you have authorization before testing against third-party infrastructure.

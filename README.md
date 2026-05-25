# Agentic Bot Research Lab

This repository serves as a research laboratory for studying **Agentic Bots** and their evasion techniques against modern anti-bot systems. The goal is to bridge the gap between static network fingerprinting and advanced behavioral telemetry.

## 🔬 Threat Model: Behavioral vs. Static Defenses
Modern anti-bot systems are shifting from static identification to progressive behavioral mitigation. Below is the synthesis of my findings regarding the evolution of bot architectures.

### Executive Summary
Traditional defenses rely on static identifiers (IPs, TLS fingerprints). However, modern **Agentic Bots** (using Visual Language Models) have commoditized static spoofing. The battlefield has shifted from *Identity* ("What the client is") to *Behavioral Telemetry* ("How the client behaves").

### Key Research Findings
1. **Network Layer Bypass:** Perfectly spoofed JA3/TLS fingerprints grant immediate trust, rendering User-Agent checks obsolete.
2. **Visual Over DOM:** Agentic bots use computer vision (Set-of-Mark) to interact with the UI, effectively ignoring hidden DOM-based honeypots.
3. **Latency as a Feature:** The processing time required by VLMs (Gemini/GPT) acts as organic "jitter," naturally mimicking human interaction speed and defeating behavioral rate-limiters.

*(Full synthesis available in `/docs/Final_Threat_Intel_Report.md`)*

## Repository Structure
- `docs/` – Threat Intelligence reports and high-level findings.
- `research/` – Empirical data, PCAPs, and experimental telemetry (Static & Dynamic analysis).
- `src/scanner/` – An agentic DAST scanner implementation using vision-based navigation.

## Goals
- Develop adversarial UI countermeasures.
- Validate behavioral biometric signatures.
- Understand the logic of autonomous navigation in LLM-driven agents.

---
*Research conducted in a controlled environment for security verification purposes.*

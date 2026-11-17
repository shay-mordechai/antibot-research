import json
import re
import os

INPUT_FILE_PREPARE = "prepare.curl"
INPUT_FILE_FINALIZE = "finalize.curl"
INPUT_FILE_CONVERSATION = "conversation.curl"
OUTPUT_FILE = "session_ready.json"

def extract_headers(content):
    """Extracts headers from a cURL command string."""
    headers = {}
    matches = re.findall(r"-H\s+(['\"])(.*?)\1", content)
    for _, header_str in matches:
        if ':' in header_str:
            k, v = header_str.split(':', 1)
            headers[k.strip()] = v.strip()
    return headers

def extract_cookies(content, headers):
    """Extracts and cleans cookies from the cURL string or headers."""
    cookies = {}
    cookie_str = ""
    
    m = re.search(r"-b\s+(['\"])(.*?)\1", content, re.S)
    if m:
        cookie_str = m.group(2)
    else:
        for k, v in headers.items():
            if k.lower() == "cookie":
                cookie_str = v
                break

    if cookie_str:
        for pair in cookie_str.split(";"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                cookies[k.strip()] = v.strip().strip('"').strip("'")
                
    return cookies

def extract_payload(content):
    """Extracts the JSON payload from a cURL command string."""
    data_start = re.search(r"--data(?:-raw)?\s+", content)
    if not data_start:
        return {} # Return empty if no payload
        
    raw_tail = content[data_start.end():].strip()
    
    is_bash_escaped = False
    if raw_tail.startswith("$'"):
        is_bash_escaped = True
        quote_char = "'"
        raw_tail = raw_tail[2:]
    elif raw_tail.startswith("'"):
        quote_char = "'"
        raw_tail = raw_tail[1:]
    elif raw_tail.startswith('"'):
        quote_char = '"'
        raw_tail = raw_tail[1:]
    else:
        raise ValueError("Payload doesn't start with recognized quotes.")

    escaped = False
    end_idx = -1
    for i, c in enumerate(raw_tail):
        if escaped:
            escaped = False
            continue
        if c == '\\':
            escaped = True
            continue
        if c == quote_char:
            end_idx = i
            break
            
    if end_idx == -1:
        raise ValueError("Could not find closing quote for payload.")
        
    raw_payload = raw_tail[:end_idx]

    if is_bash_escaped:
        clean = raw_payload.replace('\\"', '"').replace("\\'", "'").replace('\\n', '\n').replace('\\t', '\t')
        clean = clean.replace('\\\\', '\\')
    else:
        clean = raw_payload

    start = clean.find('{')
    end = clean.rfind('}')
    if start == -1 or end == -1:
        return {}

    json_str = clean[start:end+1]

    try:
        return json.loads(json_str, strict=False)
    except json.JSONDecodeError:
        try:
            fixed = json_str.replace('\n', '\\n').replace('\r', '')
            return json.loads(fixed, strict=False)
        except Exception:
            return {}

def parse_curl_file(file_path):
    """Parses a single cURL file into a structured dictionary."""
    if not os.path.exists(file_path):
        print(f"[-] File {file_path} not found.")
        return None
        
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        
    headers = extract_headers(content)
    return {
        "headers": headers,
        "cookies": extract_cookies(content, headers),
        "payload": extract_payload(content)
    }

if __name__ == "__main__":
    try:
        print("[*] Parsing cURL files (Prepare, Finalize, Conversation)...")
        prep = parse_curl_file(INPUT_FILE_PREPARE)
        final = parse_curl_file(INPUT_FILE_FINALIZE)
        conv = parse_curl_file(INPUT_FILE_CONVERSATION)
        
        if prep and final and conv:
            # We use the conversation headers/cookies as the primary identity
            final_data = {
                "headers": conv["headers"],
                "cookies": conv["cookies"],
                "prepare_payload": prep["payload"],
                "finalize_payload": final["payload"],
                "conversation_payload": conv["payload"]
            }
            
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2)
            print(f"[+] {OUTPUT_FILE} generated successfully with finalize data!")
            
            # Validation checks
            conv_id = final_data.get('conversation_payload', {}).get('conversation_id')
            if not conv_id:
                print("[!] Warning: conversation_id missing.")
            else:
                print(f"[*] Success: Processed conversation {conv_id}")
                
        else:
            print("[-] Could not parse all files. Check if prepare/finalize/conversation exist.")
            
    except Exception as e:
        print(f"[-] Failed to parse: {e}")
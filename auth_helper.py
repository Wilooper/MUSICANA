import json
import time
import hashlib
import re
from ytmusicapi import YTMusic

ORIGIN = "https://music.youtube.com"

# -----------------------------
# 1. OAUTH AUTHENTICATION
# -----------------------------
def get_oauth():
    """Try loading OAuth credentials."""
    try:
        return YTMusic("oauth.json")
    except Exception as e:
        print("⚠ OAuth failed:", e)
        return None


# -----------------------------
# 2. HEADER.JSON LOADING
# -----------------------------
def load_header():
    try:
        with open("header.json", "r") as f:
            return json.load(f)
    except:
        return None


# -----------------------------
# 3. SAPISID EXTRACTOR
# -----------------------------
def extract_sapisid(cookie_string):
    """Extract SAPISID from cookies."""
    match = re.search(r"SAPISID=([^;]+)", cookie_string)
    if not match:
        raise Exception("❌ SAPISID not found in cookie string!")
    return match.group(1)


# -----------------------------
# 4. AUTO SAPISIDHASH GENERATOR
# -----------------------------
def build_dynamic_auth():
    """Builds a fresh SAPISIDHASH using header.json."""
    header = load_header()
    if not header:
        return None

    cookie = header.get("cookie", "")
    if not cookie:
        print("❌ Missing cookie string in header.json")
        return None

    try:
        sapisid = extract_sapisid(cookie)
    except Exception as e:
        print(e)
        return None

    timestamp = int(time.time())
    message = f"{timestamp} {sapisid} {ORIGIN}"
    digest = hashlib.sha1(message.encode()).hexdigest()

    # Insert dynamic Authorization header
    header["authorization"] = f"SAPISIDHASH {timestamp}_{digest}"
    header["origin"] = ORIGIN
    header["referer"] = ORIGIN
    header["x-goog-authuser"] = "0"
    header["user-agent"] = header.get("user-agent",
        "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/119 Safari")

    return header


# -----------------------------
# 5. YTMUSIC INSTANCE USING HEADER
# -----------------------------
def get_header_auth():
    auth = build_dynamic_auth()
    if not auth:
        return None

    try:
        return YTMusic(auth)
    except Exception as e:
        print("⚠ Header authentication failed:", e)
        return None


# -----------------------------
# 6. MAIN AUTH SELECTOR
# -----------------------------
def initialize_auth():
    """
    MAIN FUNCTION:
      1. Try OAuth
      2. Try Header.json
      3. Use guest mode
    """

    print("\n🔍 Checking authentication methods...\n")

    # 1️⃣ Try OAuth first
    ytm = get_oauth()
    if ytm:
        print("✅ Logged in using OAuth")
        return ytm

    # 2️⃣ Try header auth
    ytm = get_header_auth()
    if ytm:
        print("✅ Logged in using header.json (SAPISIDHASH)")
        return ytm

    # 3️⃣ Guest mode
    print("⚠ No valid authentication found — running in guest mode")
    return YTMusic()  # unauthenticated instance

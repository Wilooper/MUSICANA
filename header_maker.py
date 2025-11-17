import json
import re
import sys

REQUIRED_COOKIES = [
    "SID", "__Secure-1PSID", "__Secure-3PSID",
    "SAPISID", "__Secure-1PAPISID", "__Secure-3PAPISID",
    "APISID", "SSID", "HSID", "LOGIN_INFO"
]

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 10; Mobile) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)

def load_cookie_file(path):
    """Load Firefox/Chrome cookie JSON file."""
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print("❌ Failed to load cookie file:", e)
        sys.exit(1)


def extract_cookie_value(data, name):
    """Extract a cookie value by name."""
    for obj in data:
        if obj.get("Name raw") == name:
            return obj.get("Content raw")
    return None


def build_cookie_string(data):
    """Build a valid cookie string for YTM."""
    cookie_parts = []
    missing = []

    for name in REQUIRED_COOKIES:
        value = extract_cookie_value(data, name)
        if value:
            cookie_parts.append(f"{name}={value}")
        else:
            missing.append(name)

    print("\n🔍 Cookies found:")
    for c in cookie_parts:
        print("  ✔", c)

    if missing:
        print("\n⚠ Missing cookies:", missing)
        print("   (Some premium/My Library actions may fail)\n")

    return "; ".join(cookie_parts)


def build_header(cookie_string):
    """Constructs final header.json structure."""
    return {
        "cookie": cookie_string,
        "user-agent": USER_AGENT,
        "accept-language": "en-IN,en-US;q=0.9,en;q=0.8",
        "authority": "music.youtube.com",
        "origin": "https://music.youtube.com",
        "referer": "https://music.youtube.com"
    }


def save_header_json(header):
    """Write header.json to disk."""
    with open("header.json", "w") as f:
        json.dump(header, f, indent=4)
    print("\n✅ Saved as header.json\n")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 make_header.py <cookies.json>")
        sys.exit(1)

    cookie_path = sys.argv[1]
    cookie_data = load_cookie_file(cookie_path)

    cookie_string = build_cookie_string(cookie_data)
    header = build_header(cookie_string)
    save_header_json(header)

    print("🎉 Your header.json is ready!")
    print("👉 Use it with the dynamic SAPISIDHASH generator.")


if __name__ == "__main__":
    main()

import urllib.request
import urllib.parse
import json
import webbrowser
import time

# ============ HIER IHRE DATEN EINTRAGEN ============
APP_KEY = ""        # z.B. "abc123def456"
APP_SECRET = ""  # z.B. "xyz789..."
# ==================================================

print("=" * 50)
print("Dropbox Refresh Token Generator")
print("=" * 50)
print()

# 1. Link zum Autorisieren öffnen
auth_url = f"https://www.dropbox.com/oauth2/authorize?client_id={APP_KEY}&token_access_type=offline&response_type=code"
print("1. Öffne Browser für Autorisierung...")
print(f"Falls der Browser nicht automatisch öffnet, kopieren Sie diesen Link:")
print(auth_url)
print()
webbrowser.open(auth_url)

# 2. Code abfragen
print("2. Nach der Autorisierung erhalten Sie einen Code.")
print("   Kopieren Sie diesen Code und fügen Sie ihn hier ein.")
print()
code = input("Code: ").strip()

# 3. Code gegen Refresh Token tauschen
print()
print("3. Tausche Code gegen Refresh Token...")

url = "https://api.dropboxapi.com/oauth2/token"
data = urllib.parse.urlencode({
    'code': code,
    'grant_type': 'authorization_code',
    'client_id': APP_KEY,
    'client_secret': APP_SECRET
}).encode('utf-8')

req = urllib.request.Request(url, data=data, method='POST')
req.add_header('Content-Type', 'application/x-www-form-urlencoded')

try:
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode('utf-8'))
        
        print()
        print("=" * 50)
        print("ERFOLG! Hier sind Ihre Tokens:")
        print("=" * 50)
        print()
        print("📌 ACCESS TOKEN (kurzlebig, 4 Stunden):")
        print(result.get('access_token'))
        print()
        print("📌 REFRESH TOKEN (dauerhaft, für Addon):")
        print(result.get('refresh_token'))
        print()
        print("=" * 50)
        print("Diese Werte müssen Sie in Kodi eintragen:")
        print("=" * 50)
        print()
        print("App Key:     ", APP_KEY)
        print("App Secret:  ", APP_SECRET)
        print("Refresh Token:", result.get('refresh_token'))
        print()
        
        # Speichern in Datei
        with open('dropbox_tokens.txt', 'w') as f:
            f.write(f"App Key: {APP_KEY}\n")
            f.write(f"App Secret: {APP_SECRET}\n")
            f.write(f"Refresh Token: {result.get('refresh_token')}\n")
            f.write(f"Access Token: {result.get('access_token')}\n")
        print("✅ Tokens wurden in 'dropbox_tokens.txt' gespeichert!")
        
except Exception as e:
    print()
    print("❌ FEHLER:", e)
    
input("\nDrücken Sie Enter zum Beenden...")
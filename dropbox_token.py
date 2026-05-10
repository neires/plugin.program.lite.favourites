import urllib.request
import urllib.parse
import json
import webbrowser
import time
import os

# ============ HIER IHRE DATEN EINTRAGEN ============
APP_KEY = ""        # z.B. "abc123def456"
APP_SECRET = ""        # z.B. "xyz789..."
# ==================================================

print("=" * 50)
print("Dropbox Refresh Token Generator")
print("=" * 50)
print()

# 1. Link zum Autorisieren öffnen
auth_url = f"https://www.dropbox.com/oauth2/authorize?client_id={APP_KEY}&token_access_type=offline&response_type=code"
print("1. Öffne Browser für Autorisierung...")
webbrowser.open(auth_url)

# 2. Code abfragen
print("2. Nach der Autorisierung erhalten Sie einen Code.")
code = input("Code: ").strip()

# 3. Code gegen Refresh Token tauschen
print("\n3. Tausche Code gegen Refresh Token...")

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
        
        refresh_token = result.get('refresh_token')
        access_token = result.get('access_token')

        print("\n" + "=" * 50)
        print("ERFOLG!")
        print("=" * 50)
        print(f"Refresh Token: {refresh_token}")
        
        # Pfad zum Downloads-Ordner festlegen
        download_path = os.path.join(os.environ['USERPROFILE'], 'Downloads', 'dropbox_tokens.txt')
        
        # Speichern in Datei
        with open(download_path, 'w', encoding='utf-8') as f:
            f.write(f"App Key:      {APP_KEY}\n")
            f.write(f"App Secret:   {APP_SECRET}\n")
            f.write(f"Refresh Token: {refresh_token}\n")
            f.write(f"Access Token:  {access_token}\n")
        
        print(f"\n✅ Datei gespeichert unter:\n   {download_path}")
        
        print("\n" + "=" * 50)
        input("Drücken Sie Enter zum Beenden und öffnen der Datei dropbox_tokens.txt...")
        
        # Datei mit dem Standard-Texteditor öffnen
        os.startfile(download_path)
        
except Exception as e:
    print("\n❌ FEHLER:", e)
    input("\nDrücken Sie Enter zum Beenden...")

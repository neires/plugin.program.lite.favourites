#Dropbox Refresh Token Generator 01.05.2026 by neires
import urllib.request
import urllib.parse
import json
import webbrowser
import time
import os

# ============ HIER IHRE DATEN EINTRAGEN ============
APP_KEY    = ""        # z.B. "abc123def456"
APP_SECRET = ""        # z.B. "xyz789..."
# ==================================================

print("=" * 50)
print("Dropbox Refresh Token Generator")
print("=" * 50)
print()

auth_url = (
    f"https://www.dropbox.com/oauth2/authorize"
    f"?client_id={APP_KEY}&token_access_type=offline&response_type=code"
)

# 1. Anweisungen anzeigen, Browser erst nach Enter öffnen
print("1. Lesen Sie zuerst die Anweisungen für Schritt 2 und drücken Sie dann Eingabe,")
print("   um den Browser zu öffnen.")
print()
print("2. Im Browser sehen Sie gleich die Autorisierungsseite.")
print("   Dort wird nach dem Klick auf Weiter der App Folder Name, hinter Apps › , angezeigt.")
print("   - kopieren Sie ihn und hier in der Konsole einfügen + Eingabe.")
print("   Alternativ: dropbox.com/developers → Ihre App → Settings → 'App folder name'")
print()
print("   Falls der Browser sich nicht öffnet, kopieren Sie diesen Link manuell:")
print(f"   {auth_url}")
print()
input("   Eingabe drücken um den Browser zu öffnen...")

# Prüfung ob APP_KEY und APP_SECRET eingetragen sind
if not APP_KEY or not APP_SECRET:
    print()
    print("=" * 50)
    print("⚠️  HINWEIS: APP_KEY und/oder APP_SECRET sind nicht eingetragen!")
    print("   Die Datei wird jetzt im Texteditor geöffnet.")
    print("   Tragen Sie Ihre Daten bei APP_KEY und APP_SECRET ein,")
    print("   speichern Sie die Datei und starten Sie das Programm erneut.")
    print("=" * 50)
    input("\n   Eingabe drücken zum öffnen und korrigieren der nötigen Daten in der Datei.")
    os.startfile(__file__)
    exit()

webbrowser.open(auth_url)
print()
app_folder_name = input("   App Folder Name eingeben: ").strip()

# 3. Zugangscode abfragen
print()
print("3. Autorisieren Sie die App im Browser mit Zulassen.")
print("    - Sie erhalten einen Zugangscode – kopieren Sie ihn und hier in der Konsole einfügen + Eingabe.")
code = input("   Zugangscode eingeben: ").strip()

# 4. Code gegen Refresh Token tauschen
print()
print("4. Tausche Zugangscode gegen Refresh Token...")
url  = "https://api.dropboxapi.com/oauth2/token"
data = urllib.parse.urlencode({
    'code':          code,
    'grant_type':    'authorization_code',
    'client_id':     APP_KEY,
    'client_secret': APP_SECRET,
}).encode('utf-8')
req = urllib.request.Request(url, data=data, method='POST')
req.add_header('Content-Type', 'application/x-www-form-urlencoded')

try:
    with urllib.request.urlopen(req, timeout=30) as response:
        result        = json.loads(response.read().decode('utf-8'))
        refresh_token = result.get('refresh_token')

    print()
    print("=" * 50)
    print("ERFOLG!")
    print("=" * 50)
    print(f"Refresh Token:   {refresh_token}")
    print(f"App Folder Name: {app_folder_name}")

    download_path = os.path.join(
        os.environ['USERPROFILE'], 'Downloads', 'dropbox_tokens.txt'
    )
    with open(download_path, 'w', encoding='utf-8') as f:
        f.write("## Trage die 4 Werte in den Einstellungen von Lite.Favourites unter Dropbox Sync ein. ##\n")
        f.write(f"App Key:         {APP_KEY}\n")
        f.write(f"App Secret:      {APP_SECRET}\n")
        f.write(f"Refresh Token:   {refresh_token}\n")
        f.write(f"App Folder Name: {app_folder_name}\n")

    print(f"\n✅ Datei gespeichert unter:\n   {download_path}")
    print()
    print("=" * 50)
    input("Drücken Sie Eingabe zum Beenden und Öffnen der Datei...")
    os.startfile(download_path)

except Exception as e:
    print("\n❌ FEHLER:", e)
    input("\nDrücken Sie Eingabe zum Beenden...")
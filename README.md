# Lite Favourites (plugin.program.lite.favourites)

Mein eigener Ersatz (komplett neuer Code ohne Altlasten) für das alte Plugin *Super Favourites*. 
Ein schlankes, aber leistungsstarkes Kodi-Addon zur Verwaltung personalisierter Favoriten mit automatischer Metadaten-Anreicherung und Cloud-Synchronisation via Dropbox.

---

## 🚀 Hauptfunktionen

### 📂 Intelligente Organisation
* **Hierarchische Ordnerstruktur:** Erstelle beliebig tiefe Unterordner, um Filme, Serien und Addon-Links sauber zu trennen.
* **Verschiebe-Logik:** Items können nachträglich zwischen Ordnern verschoben werden. Das Addon prüft dabei logisch die Zielpfade (z. B. "Serien gehören in den Serien-Zweig").
* **Duplikat-Check:** Beim Hinzufügen erkennt das Addon, ob ein Medium bereits existiert und bietet an, direkt zum vorhandenen Speicherort zu springen. 
* **Präziser Fokus:** Der Sprung zum Duplikat erfolgt direkt mit Scroll-Fokus auf das Item. Funktioniert am besten mit der Sortierung nach Namen.
* **Speicherpfad der Favoriten:** `userdata/addon_data/plugin.program.lite.favourites/favourites.json`

### 🎭 Metadaten & Scraping
* **TMDb-Integration:** Das Addon extrahiert TMDb-IDs aus URLs und reichert Einträge automatisch mit Postern, Fanarts, Plots und Genres an.
* **IMDb-Bewertungen:** Durch die OMDb-Schnittstelle werden echte IMDb-Ratings abgerufen und als `imdbnumber` gespeichert.
* **TMDbHelper-Anbindung:** Nutzt (falls vorhanden) die lokale Datenbank des *TMDbHelper* Addons für blitzschnelle Informationen.
* **Lokales Caching:** Wenn alle Poster einmal geladen sind, werden sie nicht mehr erneut aus dem Internet geladen, sondern rasant direkt aus `userdata/Thumbnails` bezogen.

### 🛠 Bedienkomfort (UX)
* **Kontextmenü-Integration:** Füge Inhalte direkt aus anderen Addons während des Browsens zu deinen Lite Favourites hinzu.
* **Turbo-Focus-Scroll:** Eine spezielle Threading-Logik sorgt dafür, dass nach dem Wechsel in einen Ordner das zuletzt gewählte Item automatisch fokussiert und "angescrollt" wird (optimiert für Grid-Ansichten, z. B. 9 Spalten).
* **Dynamische Ansicht:** Das Addon erkennt den Inhaltstyp (Movies vs. TV Shows), damit Kodi automatisch das passende Layout wählt.

---

## 🎬 Erste Schritte (Quickstart-Guide)

### 1. Den ersten Ordner anlegen
1. Öffne das **Lite Favourites** Addon in Kodi.
2. Da die Liste beim ersten Start noch leer ist, klicke auf den Button **[+] Ersten Ordner erstellen**.
3. Gib über die Bildschirmtastatur den gewünschten Namen ein (z. B. `Serien`) und bestätige. Der Ordner ist nun angelegt!

### 2. Eine Serie finden & hinzufügen
1. Verlasse *Lite Favourites* und öffne dein Quell-Addon, zum Beispiel den **TMDbHelper**.
2. Navigiere dort zu einer Serie oder einem Film.
3. Öffne auf der Serie das Kodi-Kontextmenü (Rechtsklick, Taste `C` oder langes Drücken der OK-Taste).
4. Wähle den Eintrag **Zu Lite Favourites hinzufügen**.
5. Wähle im Auswahlfenster deinen zuvor erstellten Ordner **Serien** aus.
6. **Fertig!** Das Addon lädt nun automatisch hochauflösende Poster, Fanarts und Beschreibungen inklusive IMDb-Rating herunter.

### 3. Tipps zur Struktur
* Verlinke dir die Ordner `Serien` / `Filme` direkt in dein Home-Menü (Skin-abhängig).
* Mein Ordner `Serien` beinhaltet Serien, die ich gerade schaue. Zusätzlich nutze ich Unterordner wie *Eingestellt, Merkliste, Komplett, Staffelpause* – dorthin schiebe ich die Items nach Lust und Laune per Kontextmenü-Verschiebe-Logik.

---

## 🌟 IMDb-Bewertungen & OMDb-Key

Um echte IMDb-Bewertungen anstelle der TMDb-Userwertung anzuzeigen, wird ein OMDb-Key benötigt.

### 1. OMDb-API-Key erstellen
1. Gehe auf [omdbapi.com/apikey.aspx](http://www.omdbapi.com/apikey.aspx).
2. Wähle die Option **"FREE"** (bis zu 1.000 Abfragen pro Tag).
3. Gib deine E-Mail-Adresse und deinen Namen ein.
4. **WICHTIG:** Du musst den Bestätigungslink in der E-Mail von OMDb klicken, um den Key zu aktivieren!

### 2. Einrichtung in Kodi
Lite Favourites übernimmt den Key automatisch aus dem **TMDbHelper**:
1. Öffne die Einstellungen von **TMDbHelper**.
2. Navigiere zum Reiter **"API-Konten"** ➡️ **"OMDb API Key"**.
3. Trage deinen Key dort ein. Lite Favourites erkennt diesen nun automatisch und nutzt ihn für alle zukünftigen Favoriten.

---
## ☁️ Optionale Einrichtung: Cloud-Synchronisation per Dropbox-Sync

Der Sync ermöglicht es, deine Favoriten-Liste auf allen Kodi-Geräten identisch zu halten.

### 1. Dropbox App erstellen
1. Logge dich bei [Dropbox Developers](https://www.dropbox.com/developers/apps) ein und klicke auf **"Create app"**.
2. Wähle: **"Scoped access"**, **"Full Dropbox"** und gib der App einen Namen.
3. Reiter **"Permissions"**: Aktiviere unter "Files and folders" folgende Punkte:
   - `files.metadata.read`
   - `files.metadata.write`
   - `files.content.read`
   - `files.content.write`
4. Klicke auf **"Submit"**, um die Berechtigungen zu speichern.
5. Kopiere im Reiter **"Settings"** den **App Key** und das **App Secret**.

### 2. Tokens generieren (am Computer)
Nutze das im Repository beiliegende Skript `dropbox_token.py`:
1. Öffne `dropbox_token.py` in einem Texteditor und trage oben deinen `APP_KEY` und dein `APP_SECRET` ein.
2. Starte das Skript (Python erforderlich): `python dropbox_token.py`.
3. Folge den Anweisungen: Kopiere den App Folder Name (Schritt 2) und den erhaltenen Browser-Code (Schritt 3) in die Konsole.
4. Das Skript zeigt danach den **Refresh Token** an und speichert ihn in der Datei `dropbox_tokens.txt` im Downloads-Verzeichnis.

### 3. Addon in Kodi konfigurieren
App Key, App Secret, Refresh Token, App Folder Name
Trage die Daten in den Addon-Einstellungen ein oder editiere direkt die `settings.xml`. 

> **Info:** Der **Refresh Token** ist dein dauerhafter "Generalschlüssel".
> Er verfällt nicht und erlaubt dem Addon, selbstständig kurzlebige Access Tokens zu generieren.
> Du musst nur diese 4 Werte hinterlegen – den Rest erledigt das Addon beim ersten Sync automatisch.

**Pfad:** `userdata/addon_data/plugin.program.lite.favourites/settings.xml`

```xml
<settings version="2">
    <setting id="dropbox_app_key">DEIN_APP_KEY</setting>
    <setting id="dropbox_app_secret">DEIN_APP_SECRET</setting>
    <setting id="dropbox_refresh_token">DEIN_REFRESH_TOKEN</setting>
    <setting id="dropbox_folder">DEIN_ORDNERNAME</setting>
    <setting id="sync_interval">60</setting>
</settings>
```

### 4. Multi-Geräte Setup (Copy & Paste)
Sobald ein Gerät läuft, kannst du die Einstellungen/Dropboxtoken einfach übertragen:
1. Kopiere den Ordner `userdata/addon_data/plugin.program.lite.favourites` deines fertig konfigurierten Gerätes.
2. Füge ihn auf allen anderen Geräten (Android, Windows, CoreELEC etc.) im entsprechenden Verzeichnis ein.
3. **Fertig:** Alle Geräte nutzen nun denselben Dropbox-Sync-Kanal und sind sofort einsatzbereit, ohne dass du erneut Tokens generieren musst.
4. Im laufenden Betrieb kann direkt per Kontextmenü auf ein Item **"Sync mit Dropbox"** aufgerufen werden. 
Je nachdem was älter oder neuer ist, löst dies den Upload oder Download aus (oder nichts, falls der Inhalt gleich ist). 
Der Inhalt wird dann automatisch adhoc refresht.

---

## Vorschau
So sieht das auf meinem Kodi 22 Piers mit dem skin.arctic.zephyr.martian und Ansicht Posterwand klein aus.

https://github.com/martian89/skin.arctic.zephyr.martian

<img width="960" height="540" alt="lite favourites" src="https://github.com/user-attachments/assets/e0603f69-cfd9-425f-a0f2-521260f953f1" />

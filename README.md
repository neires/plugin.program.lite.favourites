# Lite Favourites (plugin.program.lite.favourites)

Ein schlankes, aber leistungsstarkes Kodi-Addon zur Verwaltung personalisierter Favoriten mit automatischer Metadaten-Anreicherung und Cloud-Synchronisation via Dropbox.
---
## 🚀 Hauptfunktionen

### 📂 Intelligente Organisation
* **Hierarchische Ordnerstruktur:** Erstelle beliebig tiefe Unterordner, um Filme, Serien und Addon-Links sauber zu trennen.
* **Verschiebe-Logik:** Items können nachträglich zwischen Ordnern verschoben werden. Das Addon prüft dabei logisch die Zielpfade (z. B. "Serien gehören in den Serien-Zweig").
* **Duplikat-Check:** Beim Hinzufügen erkennt das Addon, ob ein Medium bereits existiert und bietet an, direkt zum vorhandenen Speicherort zu springen.
  Der Sprung erfolgt dann auch direkt mit scoll-Fokus auf das Item. Funktioniert am besten mit Sortierung nach Name.
* *Speicherpfad der Favouriten** `userdata/addon_data/plugin.program.lite.favourites/favourites.json`

### 🎭 Metadaten & Scraping
* **TMDb-Integration:** Das Addon extrahiert TMDb-IDs aus URLs und reichert Einträge automatisch mit Postern, Fanarts, Plots und Genres an.
* **TMDbHelper-Anbindung:** Nutzt (falls vorhanden) die lokale Datenbank des *TMDbHelper* Addons für blitzschnelle Informationen.
* **Manuelle Korrektur:** Bietet die Möglichkeit, fehlerhafte TMDb-IDs über eine integrierte Suche oder manuelle Eingabe zu korrigieren.

### 🛠 Bedienkomfort (UX)
* **Kontextmenü-Integration:** Füge Inhalte direkt aus anderen Addons während des Browsens zu deinen Lite Favourites hinzu.
* **Turbo-Focus-Scroll:** Eine spezielle Threading-Logik sorgt dafür, dass nach dem Wechsel in einen Ordner das zuletzt gewählte Item automatisch fokussiert und "angescrollt" wird (optimiert für Grid-Ansichten).
* **Dynamische Ansicht:** Das Addon erkennt den Inhaltstyp (Movies vs. TV Shows), damit Kodi automatisch das passende Layout wählt.

---
## 🎬 Erste Schritte (Quickstart-Guide)

So legst du direkt nach der Installation los und fügst deine erste Serie hinzu:

### 1. Den ersten Ordner anlegen
1. Öffne das **Lite Favourites** Addon in Kodi.
2. Da die Liste beim ersten Start noch leer ist, klicke auf den Button **[+] Ersten Ordner erstellen**.
3. Gib über die Bildschirmtastatur den gewünschten Namen ein (z. B. `Serien`) und bestätige. Der Ordner ist nun angelegt!

### 2. Eine Serie finden
1. Verlasse *Lite Favourites* und öffne dein Quell-Addon, zum Beispiel den **TMDbHelper**.
2. Navigiere dort zu einer Liste mit Inhalten, z. B. unter **Serien** ➡️ **Diese Woche im Trend**.
3. Wähle eine Serie aus, die du in deinen Favoriten speichern möchtest.

### 3. Zu den Favoriten hinzufügen
1. Öffne auf der Serie das Kodi-Kontextmenü (Rechtsklick, Taste `C` auf der Tastatur oder langes Drücken der OK-Taste auf der Fernbedienung).
2. Wähle den Eintrag zum Hinzufügen (z. B. **Zu Lite Favourites hinzufügen**).
3. Es öffnet sich ein Auswahlfenster deines Addons: Wähle hier deinen zuvor erstellten Ordner **Serien** aus.
4. **Fertig!** Das Addon lädt nun automatisch die hochauflösenden Poster, Fanarts und Beschreibungen herunter. Die Serie ist jetzt sauber strukturiert in *Lite Favourites* abrufbar.
5. Ihr könnt euch auch die Ordner Serien / Filme auf eurer Home-Menü verlinken wie bei mir zusehen ist.
6. Mein Ordner Serien beinhaltet Serien die ich gerade schaue.
Zusätzlich die Unterordner Eingestellt, Merkliste, Komplett, Staffelpause, da schiebe ich dann nach Lust und Laune hin und her.

---
## ☁️ Optionale Einrichtung: Dropbox-Sync

Der Sync ermöglicht es, deine Favoriten-Liste auf allen Kodi-Geräten (TV, Tablet, Smartphone) identisch zu halten.

### 1. Dropbox App erstellen
1. Logge dich bei [Dropbox Developers](https://www.dropbox.com/developers/apps) ein.
2. Klicke auf **"Create app"**.
3. Wähle: **"Scoped access"**, **"Full Dropbox"** und gib der App einen Namen.
4. Reiter **"Permissions"**: Aktiviere unter "Files and folders" folgende Punkte:
   - files.metadata.read
   - files.metadata.write
   - files.content.read
   - files.content.write
5. Klicke auf **"Submit"**, um die Berechtigungen zu speichern.
6. Kopiere im Reiter **"Settings"** den **App Key** und das **App Secret**.

### 2. Tokens generieren (am Computer)
Nutze das im Repository beiliegende Skript `dropbox_token.py`:
1. Öffne `dropbox_token.py` in einem Texteditor.
2. Trage oben deinen `APP_KEY` und dein `APP_SECRET` ein.
3. Starte das Skript (Python erforderlich): `python dropbox_token.py`.
4. Folge den Anweisungen in der Konsole und im Browser und kopiere den im Schritt 2 angezeigten App Folder Name und in Schritt 3 erhaltenen Code in die Konsole.
5. Das Skript zeigt dir danach den **Refresh Token** an.
6. Die Tokens werden zusätzlich lokal in der 'dropbox_tokens.txt' unter %USERPROFILE%\Downloads gespeichert! und beim beenden geöffnet

### 3. Addon in Kodi konfigurieren
Trage die Daten "App Key, App Secret und Refresh Token" in den Addon-Einstellungen ein oder editiere direkt die `settings.xml`. 

> **Info:** Der **Refresh Token** ist dein dauerhafter "Generalschlüssel".
> Er verfällt nicht und erlaubt dem Addon, selbstständig kurzlebige Access Tokens zu generieren.
> Du musst nur diese drei Werte hinterlegen – den Rest erledigt das Addon beim ersten Sync automatisch.

**Pfad:** `userdata/addon_data/plugin.program.lite.favourites/settings.xml`

Beispiel-Inhalt der settings.xml:
<settings version="2">
    <setting id="dropbox_app_key">DEIN_APP_KEY</setting>
    <setting id="dropbox_app_secret">DEIN_APP_SECRET</setting>
    <setting id="dropbox_refresh_token">DEIN_REFRESH_TOKEN</setting>
    <setting id="dropbox_folder">lite_favourites_jan</setting>
    <setting id="sync_interval">60</setting>
</settings>

### 4. Multi-Geräte Setup (Copy & Paste)
Sobald ein Gerät läuft, kannst du die Einstellungen/Dropboxtoken einfach übertragen:
1. Kopiere den Ordner `userdata/addon_data/plugin.program.lite.favourites` deines fertig konfigurierten Gerätes.
2. Füge ihn auf allen anderen Geräten (Android, Windows, CoreELEC etc.) im entsprechenden Verzeichnis ein.
3. **Fertig:** Alle Geräte nutzen nun denselben Dropbox-Sync-Kanal und sind sofort einsatzbereit, ohne dass du erneut Tokens generieren musst.
4. Im laufenden Betrieb kann direkt per Kontextmenü auf ein Item " Sync mit Dropbox" aufgerufen werden.
Je nachdem was älter oder neuer ist löst dann den Upload oder Download aus, oder nichts falls der Inhalt gleich ist.
Der Inhalt wird dann automatisch adhoc refresht.

---

## Vorschau
So sieht das auf meinem Kodi 22 Piers mit dem skin.arctic.zephyr.martian aus.
https://github.com/martian89/skin.arctic.zephyr.martian

<img width="960" height="540" alt="lite favourites" src="https://github.com/user-attachments/assets/e0603f69-cfd9-425f-a0f2-521260f953f1" />

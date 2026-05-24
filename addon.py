# 2026-05-10 by neires
# edit 2026-05-12
# edit 2026-05-13 add Neuer Ordner in dialog.select
# edit 2026-05-14 add import dialog - Alte Super Favourites XML
# edit 2026-05-14 add DUPLIKATS-CHECK für Import  Super Favourites
# edit 2026-05-21 add root Einstellungen, Sync-Dropbox, Globale Suche mit Turbo-Fokus & TMDb-Fallback
import sys
import os
import json
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import time
import threading
import xml.etree.ElementTree as ET
import re
from urllib.parse import unquote, parse_qs
from datetime import datetime

try:
    from urllib.parse import parse_qsl, urlencode, quote, unquote, parse_qs
except ImportError:
    from urlparse import parse_qsl, parse_qs
    from urllib import urlencode, unquote

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
DATA_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

if isinstance(DATA_PATH, bytes):
    DATA_PATH = DATA_PATH.decode('utf-8')
if isinstance(ADDON_PATH, bytes):
    ADDON_PATH = ADDON_PATH.decode('utf-8')

FAVS_FILE = os.path.join(DATA_PATH, 'favourites.json')
ICON_PATH = os.path.join(ADDON_PATH, 'resources/icon.png')

CACHE_DURATION = 3600
_favourites_cache = None
_cache_timestamp = 0

if not xbmcvfs.exists(DATA_PATH):
    xbmcvfs.mkdirs(DATA_PATH)

def safe_string(value):
    if isinstance(value, list):
        return ' / '.join([str(item) for item in value])
    if value is None:
        return ''
    return str(value)

def clean_info_dict(info_dict):
    if not info_dict:
        return {}
    cleaned = {}
    for key, value in info_dict.items():
        cleaned[key] = safe_string(value)
    return cleaned

def clean_artwork(art_dict):
    if not art_dict:
        return {}
    cleaned = {}
    if 'poster' in art_dict and art_dict['poster']:
        cleaned['poster'] = art_dict['poster']
    elif 'thumb' in art_dict and art_dict['thumb']:
        cleaned['poster'] = art_dict['thumb']
    return cleaned

def _norm(s):
    if s is None:
        return ''
    return str(s).strip().lower()

def _item_key(item):
    t = _norm(item.get('type'))

    if t == 'folder':
        return ('folder', _norm(item.get('id')))

    url = item.get('url') or ''
    tmdb_id, media_type = extract_tmdb_id_from_url(url) if url else (None, None)

    if tmdb_id and media_type:
        return ('tmdb', _norm(media_type), str(tmdb_id))

    if url:
        return ('url', _norm(url))

    return ('name', t, _norm(item.get('name')))

def _folder_has_duplicate(folder_items, candidate_item):
    cand_key = _item_key(candidate_item)
    for it in folder_items:
        if _item_key(it) == cand_key:
            return True
    return False

def _folder_display_name(folder_id):
    if folder_id == 'root':
        return 'Root'
    return str(folder_id).replace('/', ' / ')

def _find_duplicate_folders_anywhere(data, candidate_item):
    cand_key = _item_key(candidate_item)
    locations = []

    for fid, items in data.items():
        if not isinstance(items, list):
            continue
        for it in items:
            if _item_key(it) == cand_key:
                # WICHTIG: Gibt jetzt ein Dictionary mit ID und Name zurück!
                locations.append({'folder_id': fid, 'name': it.get('name')})
                break

    return locations

def _key_to_str(key_tuple):
    try:
        kind = key_tuple[0]
        if kind == 'tmdb':
            return f"tmdb|{key_tuple[1]}|{key_tuple[2]}"
        if kind == 'url':
            return f"url|{key_tuple[1]}"
        if kind == 'name':
            return f"name|{key_tuple[1]}|{key_tuple[2]}"
        if kind == 'folder':
            return f"folder|{key_tuple[1]}"
    except:
        pass
    return ""

def _int_label(lbl):
    try:
        v = xbmc.getInfoLabel(lbl)
        if v and v.isdigit():
            return int(v)
    except:
        pass
    return None

def _goto_lite_folder(folder_id, target_name=None):
    query = {'mode': 'browse', 'folder': folder_id}
    if target_name:
        query['focus_item'] = target_name
    url = build_url(query)
    xbmc.executebuiltin(f'Container.Update("{url}")')

def load_favourites():
    global _favourites_cache, _cache_timestamp
    import time
    current_time = time.time()
    if _favourites_cache is not None and (current_time - _cache_timestamp) < CACHE_DURATION:
        return _favourites_cache
    if xbmcvfs.exists(FAVS_FILE):
        try:
            f = xbmcvfs.File(FAVS_FILE, 'r')
            content = f.read()
            f.close()
            data = json.loads(content)
            _favourites_cache = data
            _cache_timestamp = current_time
            return data
        except Exception:
            pass
    return {'root': []}

def save_favourites(data):
    global _favourites_cache, _cache_timestamp
    try:
        f = xbmcvfs.File(FAVS_FILE, 'w')
        f.write(json.dumps(data, indent=2, ensure_ascii=False))
        f.close()
        import time
        _favourites_cache = data
        _cache_timestamp = time.time()
    except Exception:
        pass

def clear_cache():
    global _favourites_cache, _cache_timestamp
    _favourites_cache = None
    _cache_timestamp = 0

def build_url(query):
    return sys.argv[0] + '?' + urlencode(query)

def get_setting_int(setting_id, default=0):
    try:
        v = ADDON.getSetting(setting_id)
        if v is None or v == '':
            return int(default)
        return int(v)
    except Exception:
        return int(default)

def get_setting_bool(setting_id, default=False):
    try:
        v = ADDON.getSetting(setting_id)
        if v is None or v == '':
            return bool(default)
        return v.lower() == 'true'
    except Exception:
        return bool(default)

def get_want_ascending():
    sd = ADDON.getSetting('sort_direction')
    if sd is not None and sd != '':
        try:
            return int(sd) == 0
        except Exception:
            return True
    return get_setting_bool('sort_ascending', True)

def apply_container_sort():
    sort_idx = get_setting_int('sort_method', 0)
    if sort_idx == 1:
        sort_method = xbmcplugin.SORT_METHOD_VIDEO_YEAR
    elif sort_idx == 2:
        sort_method = xbmcplugin.SORT_METHOD_VIDEO_RATING
    else:
        sort_method = xbmcplugin.SORT_METHOD_LABEL

    xbmc.executebuiltin(f'Container.SetSortMethod({int(sort_method)})')

    want_ascending = get_want_ascending()
    current_ascending = xbmc.getCondVisibility('Container.SortDirection(ascending)')
    if want_ascending != current_ascending:
        xbmc.executebuiltin('Container.SetSortDirection')

def add_folder(folder_name, parent='root'):
    data = load_favourites()
    if parent not in data:
        data[parent] = []
    folder_id = parent + '/' + folder_name if parent != 'root' else folder_name
    data[parent].append({'type': 'folder', 'name': folder_name, 'id': folder_id})
    if folder_id not in data:
        data[folder_id] = []
    save_favourites(data)
    xbmcgui.Dialog().notification('Lite Favourites', 'Ordner erstellt: ' + folder_name, xbmcgui.NOTIFICATION_INFO, 2000)

def import_super_favourites():
    # Definiere den Standardpfad zu Super Favourites
    sf_dir = xbmcvfs.translatePath('special://userdata/addon_data/plugin.program.super.favourites/')
    if not xbmcvfs.exists(sf_dir):
        sf_dir = xbmcvfs.translatePath('special://userdata/addon_data/')

    # Öffne den Kodi-Dateibrowser
    dialog = xbmcgui.Dialog()
    xml_file = dialog.browse(1, 'Super Favourites XML auswählen', 'files', '.xml', False, False, sf_dir)

    if not xml_file:
        return

    progress = xbmcgui.DialogProgress()
    progress.create('Lite Favourites', 'Importiere Favoriten...')

    try:
        local_xml_path = xbmcvfs.translatePath(xml_file)
        import xml.etree.ElementTree as ET
        tree = ET.parse(local_xml_path)
        root = tree.getroot()

        # Lädt existierende JSON
        data = load_favourites()

        # --- SCHRITT 1: Vorhandene Ordner-Struktur analysieren ---
        tv_folder_id = None
        movie_folder_id = None

        if 'root' in data:
            for folder in data['root']:
                if folder.get('type') == 'folder':
                    f_id = folder.get('id')
                    f_name = str(folder.get('name', '')).lower()
                    
                    folder_content = data.get(f_id, [])
                    has_tv = any(i.get('type') == 'tvshow' for i in folder_content)
                    has_movie = any(i.get('type') in ('item', 'movie') for i in folder_content)

                    if has_tv and not tv_folder_id:
                        tv_folder_id = f_id
                    elif has_movie and not movie_folder_id:
                        movie_folder_id = f_id
                        
                    elif not tv_folder_id and any(x in f_name for x in ['serie', 'tv', 'show']):
                        tv_folder_id = f_id
                    elif not movie_folder_id and any(x in f_name for x in ['film', 'movie']):
                        movie_folder_id = f_id

        # --- SCHRITT 2: Fallback Ordner erstellen ---
        if not tv_folder_id:
            tv_folder_id = 'Serien'
            if 'root' not in data: data['root'] = []
            if not any(f.get('id') == tv_folder_id for f in data['root']):
                data['root'].append({"type": "folder", "name": "Serien", "id": tv_folder_id})
        
        if not movie_folder_id:
            movie_folder_id = 'Filme'
            if 'root' not in data: data['root'] = []
            if not any(f.get('id') == movie_folder_id for f in data['root']):
                data['root'].append({"type": "folder", "name": "Filme", "id": movie_folder_id})

        if tv_folder_id not in data: data[tv_folder_id] = []
        if movie_folder_id not in data: data[movie_folder_id] = []

        count_imported = 0
        count_skipped = 0
        favs = root.findall('favourite')
        total_favs = len(favs)

        # --- SCHRITT 3: XML durchlaufen ---
        for i, fav in enumerate(favs):
            name = fav.get('name')
            thumb = fav.get('thumb')
            
            percent = int((i / total_favs) * 100)
            progress.update(percent, f'Importiere: {name}')
            
            if thumb and "/w500/" in thumb:
                thumb = thumb.replace("/w500/", "/original/")
                
            raw_text = fav.text
            if not raw_text: continue
                
            match = re.search(r'"(plugin://.*?)"', raw_text)
            if not match: continue
                
            full_url = match.group(1)
            url_lower = full_url.lower()
            is_tv = 'type=tv' in url_lower or 'tvshow' in url_lower
            
            if "&sf_options=" in full_url:
                base_url, sf_options_encoded = full_url.split("&sf_options=", 1)
            else:
                base_url = full_url
                sf_options_encoded = ""

            plot = ""
            year = ""
            rating = ""
            genre = ""
            
            if sf_options_encoded:
                from urllib.parse import unquote, parse_qs
                sf_options_decoded = unquote(sf_options_encoded)
                sf_dict = parse_qs(sf_options_decoded)
                
                if 'desc' in sf_dict: plot = sf_dict['desc'][0]
                if 'meta' in sf_dict:
                    meta_decoded = unquote(sf_dict['meta'][0])
                    meta_dict = parse_qs(meta_decoded)
                    year = meta_dict.get('year', [''])[0]
                    rating = meta_dict.get('rating', [''])[0]
                    genre = meta_dict.get('genre', [''])[0]
                    genre = genre.replace(" + / + ", " / ").replace("+", " ")

            target_folder = tv_folder_id if is_tv else movie_folder_id
            item_type = "tvshow" if is_tv else "item"
            mediatype = "tvshow" if is_tv else "movie"

            new_entry = {
                "type": item_type,
                "name": name,
                "url": base_url,
                "art": {"poster": thumb},
                "info": {
                    "title": name,
                    "plot": plot,
                    "year": year,
                    "rating": rating,
                    "genre": genre,
                    "mediatype": mediatype,
                    "imdbnumber": "" 
                }
            }
            
            # --- NEU: SILENT DUPLIKATS-CHECK ---
            # Wir nutzen deine bestehende Funktion _find_duplicate_folders_anywhere
            if _find_duplicate_folders_anywhere(data, new_entry):
                count_skipped += 1
                continue # Überspringt das Speichern und macht beim nächsten Item weiter
            
            data[target_folder].append(new_entry)
            count_imported += 1

        save_favourites(data)
        progress.close()
        
        # Angepasste Erfolgsmeldung
        msg = f'{count_imported} neu importiert'
        if count_skipped > 0:
            msg += f', {count_skipped} übersprungen (Duplikate)'
            
        xbmcgui.Dialog().notification('Lite Favourites Import', msg, xbmcgui.NOTIFICATION_INFO, 4000)

    except Exception as e:
        if progress: progress.close()
        xbmcgui.Dialog().ok('Import Fehler', str(e))
        
def add_favourite(name, url, parent='root', item_type='item', art=None, info=None):
    data = load_favourites()
    if parent not in data:
        data[parent] = []

    # Initiales Item-Objekt
    fav_item = {
        'type': item_type,
        'name': name,
        'url': url
    }

    if art:
        fav_item['art'] = clean_artwork(art)
    
    # Sicherstellen, dass info ein Dictionary ist
    info_dict = info if info else {}

    # --- AUTOMATISCHE METADATEN-ERWEITERUNG BEIM HINZUFÜGEN ---
    try:
        tmdb_id, media_type = extract_tmdb_id_from_url(url)
        if tmdb_id:
            imdb_id = info_dict.get('imdbnumber') or info_dict.get('imdb_id')
            tmdb_rating = info_dict.get('rating')
            api_key_tmdb = get_tmdb_api_key_simple()

            # 1. IMDb-ID Fallback (Lokal/Online), falls nicht im Context vorhanden
            if not imdb_id:
                # Lokaler Check in TMDbHelper DB
                database_dir = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.themoviedb.helper/database_07/')
                db_path = os.path.join(database_dir, 'ItemDetails.db')
                if xbmcvfs.exists(db_path):
                    try:
                        import sqlite3
                        conn = sqlite3.connect(db_path)
                        cur = conn.cursor()
                        table = 'movie' if media_type == 'movie' else 'tvshow'
                        cur.execute(f"SELECT imdb_id, unique_ids, rating FROM {table} WHERE tmdb_id = ?", (tmdb_id,))
                        row = cur.fetchone()
                        if row:
                            imdb_id = row[0] or (json.loads(row[1]).get('imdb') if row[1] else None)
                            if not tmdb_rating: tmdb_rating = row[2]
                        conn.close()
                    except: pass

                # Online Check bei TMDb (für IMDb-ID & Rating Fallback)
                if not imdb_id and api_key_tmdb:
                    try:
                        import requests
                        tmdb_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={api_key_tmdb}&language=de"
                        tmdb_res = requests.get(tmdb_url, timeout=4).json()
                        imdb_id = tmdb_res.get('imdb_id')
                        if not imdb_id and media_type == 'tv':
                            ext_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/external_ids?api_key={api_key_tmdb}"
                            imdb_id = requests.get(ext_url, timeout=4).json().get('imdb_id')
                        if not tmdb_rating: tmdb_rating = tmdb_res.get('vote_average')
                    except: pass

            # 2. OMDb Abfrage für das IMDb Rating
            helper_addon = xbmcaddon.Addon('plugin.video.themoviedb.helper')
            omdb_key = helper_addon.getSetting('omdb_apikey')
            if omdb_key:
                try:
                    import requests
                    if imdb_id:
                        omdb_url = f"https://www.omdbapi.com/?i={imdb_id}&apikey={omdb_key}"
                    else:
                        year = info_dict.get('year', '')
                        omdb_url = f"https://www.omdbapi.com/?t={quote(name)}&y={year}&apikey={omdb_key}"
                    
                    res = requests.get(omdb_url, timeout=4).json()
                    if res.get("Response") == "True":
                        val = res.get("imdbRating")
                        if val and val != "N/A":
                            info_dict['rating'] = str(val)
                            if not imdb_id: imdb_id = res.get("imdbID")
                        elif tmdb_rating: # Fallback auf TMDb Rating
                            info_dict['rating'] = str(tmdb_rating)
                except:
                    if tmdb_rating: info_dict['rating'] = str(tmdb_rating)
            elif tmdb_rating:
                info_dict['rating'] = str(tmdb_rating)

            # IMDb ID speichern falls gefunden
            if imdb_id:
                info_dict['imdbnumber'] = str(imdb_id)

    except Exception as e:
        xbmc.log(f"LITE-FAV: Fehler beim Abrufen der Zusatzinfos: {str(e)}", xbmc.LOGDEBUG)

    # Info säubern und zuweisen
    fav_item['info'] = clean_info_dict(info_dict)

    # --- DUPLIKATSPRÜFUNG ---
    locations_info = _find_duplicate_folders_anywhere(data, fav_item)
    if locations_info:
        label = 'Serie' if item_type == 'tvshow' else 'Film'
        names = [_folder_display_name(info['folder_id']) for info in locations_info]

        if len(locations_info) == 1:
            target_folder = locations_info[0]['folder_id']
            target_name = locations_info[0]['name']
            msg = f'{label} ist bereits in "{names[0]}"\n\nZum vorhandenen Ordner wechseln?'
            if xbmcgui.Dialog().yesno('Duplikat gefunden', msg):
                _goto_lite_folder(target_folder, target_name)
            return False

        title = f'{label} ist bereits vorhanden in:'
        sel = xbmcgui.Dialog().select(title, names)
        if sel >= 0:
            target_folder = locations_info[sel]['folder_id']
            target_name = locations_info[sel]['name']
            _goto_lite_folder(target_folder, target_name)
        return False

    # Speichern
    data[parent].append(fav_item)
    save_favourites(data)
    xbmcgui.Dialog().notification('Lite Favourites', 'Favorit hinzugefügt: ' + name, xbmcgui.NOTIFICATION_INFO, 2000)
    return True

def remove_item(parent, index):
    data = load_favourites()
    if parent in data and index < len(data[parent]):
        item = data[parent][index]
        if item.get('type') == 'folder' and item.get('id') in data:
            del data[item['id']]
        del data[parent][index]
        save_favourites(data)
        xbmcgui.Dialog().notification('Lite Favourites', 'Gelöscht', xbmcgui.NOTIFICATION_INFO, 2000)

def move_item(source_parent, item_index, target_parent):
    data = load_favourites()

    if source_parent not in data or item_index >= len(data[source_parent]):
        return False
    if target_parent not in data:
        return False

    try:
        item = data[source_parent][item_index]
        item_type = item.get('type')

        if item_type != 'folder':
            if item_type == 'tvshow':
                allowed_root = 'Serien'
                label = 'Serie'
            else:
                allowed_root = 'Filme'
                label = 'Film'

            if target_parent == 'root':
                xbmcgui.Dialog().notification(
                    'Lite Favourites',
                    f'{label} kann nicht nach Root verschoben werden',
                    xbmcgui.NOTIFICATION_WARNING,
                    2500
                )
                return False

            if not (target_parent == allowed_root or target_parent.startswith(allowed_root + '/')):
                xbmcgui.Dialog().notification(
                    'Lite Favourites',
                    f'{label} kann nur in "{allowed_root}" verschoben werden',
                    xbmcgui.NOTIFICATION_WARNING,
                    3000
                )
                return False

        if source_parent == target_parent:
            xbmcgui.Dialog().notification(
                'Lite Favourites',
                'Bereits im gleichen Ordner',
                xbmcgui.NOTIFICATION_WARNING,
                2000
            )
            return False

        if item_type == 'folder':
            item_id = item.get('id', '')
            if item_id and target_parent.startswith(item_id + '/'):
                xbmcgui.Dialog().notification(
                    'Lite Favourites',
                    'Kann nicht in Unterordner verschieben',
                    xbmcgui.NOTIFICATION_ERROR,
                    2000
                )
                return False

        if _folder_has_duplicate(data[target_parent], item):
            xbmcgui.Dialog().notification(
                'Lite Favourites',
                'Bereits im Zielordner vorhanden',
                xbmcgui.NOTIFICATION_WARNING,
                2500
            )
            return False

        data[target_parent].append(item)
        del data[source_parent][item_index]
        save_favourites(data)

        item_name = item.get('name', '')
        if target_parent != 'root':
            parts = target_parent.split('/')
            target_name = parts[-1] if parts and parts[-1] else (parts[-2] if len(parts) > 1 else 'Unbekannt')
        else:
            target_name = 'Root'

        xbmcgui.Dialog().notification(
            'Lite Favourites',
            f"'{item_name}' nach '{target_name}' verschoben",
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
        return True

    except Exception:
        xbmcgui.Dialog().notification(
            'Lite Favourites',
            'Fehler beim Verschieben',
            xbmcgui.NOTIFICATION_ERROR,
            2000
        )
        return False

def get_tvshow_episodes(tvshow_url):
    try:
        import re
        if 'tmdb_id=' in tvshow_url:
            tmdb_id = re.search(r'tmdb_id=(\d+)', tvshow_url)
            if tmdb_id:
                tmdb_id = tmdb_id.group(1)
                base_url = 'plugin://plugin.video.themoviedb.helper/'
                episodes_url = base_url + '?info=flatseasons&tmdb_id=' + tmdb_id + '&type=tv'
                return episodes_url
    except Exception:
        pass
    return None

def extract_tmdb_id_from_url(url):
    import re
    tmdb_id_match = re.search(r'tmdb_id=(\d+)', url)
    if not tmdb_id_match:
        return None, None
    tmdb_id = tmdb_id_match.group(1)
    if 'tmdb_type=movie' in url:
        media_type = 'movie'
    elif 'tmdb_type=tv' in url:
        media_type = 'tv'
    else:
        if 'info=details&type=movie' in url or 'type=movie' in url:
            media_type = 'movie'
        elif 'info=details&type=tv' in url or 'type=tv' in url or 'info=trakt_upnext' in url:
            media_type = 'tv'
        else:
            media_type = 'tv'
    return tmdb_id, media_type

def extract_api_key_from_token(access_token):
    try:
        import base64
        import json
        import re
        parts = access_token.split('.')
        if len(parts) == 3:
            payload_encoded = parts[1]
            padding = 4 - len(payload_encoded) % 4
            if padding != 4:
                payload_encoded += '=' * padding
            payload_decoded = base64.urlsafe_b64decode(payload_encoded)
            payload_str = payload_decoded.decode('utf-8')
            payload_data = json.loads(payload_str)
            if 'aud' in payload_data:
                return payload_data['aud']
        api_key_pattern = r'"aud":"([a-f0-9]{32})"'
        match = re.search(api_key_pattern, access_token)
        if match:
            return match.group(1)
        hex_pattern = r'([a-f0-9]{32})'
        matches = re.findall(hex_pattern, access_token, re.IGNORECASE)
        for m in matches:
            if len(m) == 32:
                return m
    except Exception:
        pass
    return None

def get_tmdb_api_key_simple():
    try:
        import re
        import json
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.themoviedb.helper/settings.xml')
        if not xbmcvfs.exists(settings_path):
            return None
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
        token_match = re.search(r'access_token["\']\s*:\s*["\']([^"\']+)["\']', content)
        if not token_match:
            json_match = re.search(r'tmdb_user_token[^>]*>({.*?})</setting>', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).replace('&quot;', '"')
                try:
                    data = json.loads(json_str)
                    if 'access_token' in data:
                        access_token = data['access_token']
                    else:
                        return None
                except Exception:
                    return None
            else:
                return None
        else:
            access_token = token_match.group(1)
        api_key = extract_api_key_from_token(access_token)
        return api_key
    except Exception:
        return None

def update_item_info(parent, index):
    data = load_favourites()
    if parent not in data or index >= len(data[parent]):
        xbmcgui.Dialog().notification('Lite Favourites', 'Item nicht gefunden', xbmcgui.NOTIFICATION_ERROR, 2000)
        return

    item = data[parent][index]
    if 'url' not in item: return
    
    progress = xbmcgui.DialogProgress()
    progress.create('Lite Favourites', 'Aktualisiere Daten...')

    try:
        progress.update(10, 'Analysiere IDs...')
        item_name = item.get('name', '')
        item_url = item.get('url', '')
        tmdb_id, media_type = extract_tmdb_id_from_url(item_url)
        api_key_tmdb = get_tmdb_api_key_simple() # Deine vorhandene Funktion
        
        imdb_id = item.get('info', {}).get('imdbnumber')
        tmdb_rating = None

        # --- SCHRITT 1: IMDb ID finden (Lokal -> Online Fallback) ---
        if not imdb_id:
            progress.update(30, 'Suche IMDb ID lokal...')
            # Lokaler Check (TMDbHelper DB)
            database_dir = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.themoviedb.helper/database_07/')
            db_path = os.path.join(database_dir, 'ItemDetails.db')
            if xbmcvfs.exists(db_path):
                try:
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    cur = conn.cursor()
                    table = 'movie' if media_type == 'movie' else 'tvshow'
                    cur.execute(f"SELECT imdb_id, unique_ids, rating FROM {table} WHERE tmdb_id = ?", (tmdb_id,))
                    row = cur.fetchone()
                    if row:
                        imdb_id = row[0] or (json.loads(row[1]).get('imdb') if row[1] else None)
                        tmdb_rating = row[2]
                    conn.close()
                except: pass

            # Online-Fallback für IMDb ID via TMDb API (falls lokal nichts gefunden wurde)
            if not imdb_id and api_key_tmdb:
                progress.update(45, 'Suche IMDb ID online (TMDb)...')
                try:
                    import requests
                    tmdb_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={api_key_tmdb}&language=de"
                    tmdb_res = requests.get(tmdb_url, timeout=5).json()
                    imdb_id = tmdb_res.get('imdb_id') # Nur bei Movies direkt im Root
                    if not imdb_id: # Bei Serien steckt sie in external_ids
                        ext_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/external_ids?api_key={api_key_tmdb}"
                        imdb_id = requests.get(ext_url, timeout=5).json().get('imdb_id')
                    
                    if not tmdb_rating:
                        tmdb_rating = tmdb_res.get('vote_average')
                except: pass

        # --- SCHRITT 2: OMDb Abfrage für das IMDb Rating ---
        progress.update(70, 'Frage OMDb Rating ab...')
        final_rating = None
        
        helper_addon = xbmcaddon.Addon('plugin.video.themoviedb.helper')
        omdb_key = helper_addon.getSetting('omdb_apikey')

        if omdb_key:
            try:
                import requests
                if imdb_id:
                    omdb_url = f"https://www.omdbapi.com/?i={imdb_id}&apikey={omdb_key}"
                else:
                    year = item.get('info', {}).get('year', '')
                    omdb_url = f"https://www.omdbapi.com/?t={quote(item_name)}&y={year}&apikey={omdb_key}"

                res = requests.get(omdb_url, timeout=5).json()
                if res.get("Response") == "True":
                    val = res.get("imdbRating")
                    if val and val != "N/A":
                        final_rating = val
                        if not imdb_id: imdb_id = res.get("imdbID")
            except: pass

        # --- SCHRITT 3: Fallback auf TMDb-Rating, falls OMDb fehlschlägt ---
        if not final_rating and tmdb_rating:
            final_rating = str(tmdb_rating)
            xbmc.log(f"LITE-FAV: OMDb fehlgeschlagen, nutze TMDb Rating: {tmdb_rating}", xbmc.LOGINFO)

        # --- SCHRITT 4: Daten speichern ---
        if 'info' not in item: item['info'] = {}
        
        if final_rating:
            item['info']['rating'] = final_rating
        if imdb_id:
            item['info']['imdbnumber'] = imdb_id

        item['info'] = clean_info_dict(item['info'])
        data[parent][index] = item
        save_favourites(data)
        
        progress.close()
        xbmcgui.Dialog().notification('Lite Favourites', f"'{item_name}' aktualisiert", xbmcgui.NOTIFICATION_INFO, 2000)
        xbmc.executebuiltin('Container.Refresh')

    except Exception as e:
        if progress: progress.close()
        xbmcgui.Dialog().ok('Fehler', str(e))
        

def get_all_folders(data):
    folders = [('Root', 'root')]

    def collect(parent_id, indent=''):
        if parent_id in data:
            for it in data[parent_id]:
                if it.get('type') == 'folder':
                    folders.append((indent + it.get('name', ''), it.get('id', '')))
                    collect(it.get('id', ''), indent + '  ')

    collect('root', '')
    return folders

def find_root_folder_id(data, wanted_name):
    wanted = (wanted_name or '').strip().lower()
    for it in data.get('root', []):
        if it.get('type') == 'folder' and (it.get('name', '').strip().lower() == wanted):
            return it.get('id')
    return None

def get_scoped_folders(data, scope_name):
    scope_root = find_root_folder_id(data, scope_name)
    if not scope_root:
        return get_all_folders(data)

    folders = [(scope_name, scope_root)]

    def collect(parent_id, indent='  '):
        for it in data.get(parent_id, []):
            if it.get('type') == 'folder':
                folders.append((indent + it.get('name', ''), it.get('id', '')))
                collect(it.get('id', ''), indent + '  ')

    collect(scope_root, '  ')
    return folders

def detect_fav_type_from_context(list_item):
    try:
        mt = ''
        try:
            info = list_item.getVideoInfoTag()
            if info:
                mt = (info.getMediaType() or '').lower()
        except Exception:
            mt = ''
        if mt in ('tvshow', 'season', 'episode'):
            return 'tvshow'
        if mt in ('movie',):
            return 'item'
        try:
            dbt = (xbmc.getInfoLabel('ListItem.DBType') or '').lower()
            if dbt in ('tvshow', 'season', 'episode'):
                return 'tvshow'
            if dbt in ('movie',):
                return 'item'
        except Exception:
            pass
        p = (list_item.getPath() or '').lower()
        fp = (xbmc.getInfoLabel('ListItem.FolderPath') or '').lower()
        if 'tmdb_type=tv' in p or 'tmdb_type=tv' in fp or 'type=tv' in p or 'type=tv' in fp:
            return 'tvshow'
        if 'tmdb_type=movie' in p or 'tmdb_type=movie' in fp or 'type=movie' in p or 'type=movie' in fp:
            return 'item'
    except Exception:
        pass
    return 'item'

def search_items():
        handle = int(sys.argv[1])
        
        kb = xbmc.Keyboard('', 'Suchbegriff eingeben')
        kb.doModal()
        
        if not kb.isConfirmed() or not kb.getText().strip():
            xbmcplugin.endOfDirectory(handle, updateListing=False, cacheToDisc=False)
            return
            
        query = kb.getText().strip().lower()
        
        xbmcplugin.setContent(handle, 'files')
        xbmcplugin.setPluginCategory(handle, f'Suche: {query}')
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
        
        data = load_favourites()
        match_count = 0
        
        try:
            from urllib.parse import quote
        except ImportError:
            from urllib import quote
            
        for folder_id, items in data.items():
            if not isinstance(items, list): 
                continue
                
            for item in items:
                name = item.get('name', '')
                if query in name.lower():
                    match_count += 1
                    display_folder = _folder_display_name(folder_id)
                    item_type = item.get('type', 'item')
                    
                    if item_type == 'folder':
                        type_str = "Ordner"
                    elif item_type == 'tvshow':
                        type_str = "Serie"
                    else:
                        type_str = "Film"
                        
                    # --- FIX: DEN KOMPLETTEN TEXT ALS VARIABLE SPEICHERN ---
                    full_label = f"{name} [COLOR gray]({type_str} in: {display_folder})[/COLOR]"
                    li = xbmcgui.ListItem(full_label)
                    
                    if 'art' in item and item['art']:
                        li.setArt(clean_artwork(item['art']))
                        
                    # Wir übergeben nun full_label als title, damit Kodi es nicht überschreibt!
                    info_dict = {'title': full_label}
                    if item_type == 'tvshow':
                        info_dict['mediatype'] = 'tvshow'
                        info_dict['tvshowtitle'] = name # Hier behalten wir den reinen Namen für die DB
                    else:
                        info_dict['mediatype'] = 'movie'
                        
                    li.setInfo('video', info_dict)
                    # --------------------------------------------------------
                    
                    safe_focus = quote(name)
                    target_url = build_url({
                        'mode': 'search_goto',
                        'folder': folder_id,
                        'focus_item': safe_focus
                    })
                    
                    context_menu = [
                        ('Zum Ziel springen', 'RunPlugin(' + target_url + ')')
                    ]
                    li.addContextMenuItems(context_menu)
                    
                    xbmcplugin.addDirectoryItem(handle, target_url, li, isFolder=False)
                    
        if match_count == 0:
            li_retry = xbmcgui.ListItem('[I]Keine Treffer gefunden - Erneut suchen...[/I]')
            search_icon = 'DefaultAddonsSearch.png'
            li_retry.setArt({'icon': search_icon, 'thumb': search_icon, 'poster': search_icon})
            li_retry.setProperty('IsPlayable', 'false')
            retry_url = build_url({'mode': 'search'})
            xbmcplugin.addDirectoryItem(handle, retry_url, li_retry, isFolder=True)
            
            li_tmdb = xbmcgui.ListItem(f'[B][🔍] "{query}" mit TMDb Helper suchen...[/B]')
            tmdb_icon = 'DefaultVideo.png'
            li_tmdb.setArt({'icon': tmdb_icon, 'thumb': tmdb_icon, 'poster': tmdb_icon})
            li_tmdb.setProperty('IsPlayable', 'false')
            dummy_url = build_url({'mode': 'search_tmdb_dummy', 'query': query})
            xbmcplugin.addDirectoryItem(handle, dummy_url, li_tmdb, isFolder=False)
            
        xbmcplugin.endOfDirectory(handle, updateListing=False, cacheToDisc=False)

def list_directory(folder_id='root', focus_item=None):
        handle = int(sys.argv[1])
        data = load_favourites()
        
        folder_items = []
        media_items = []
        
        if folder_id in data:
            for item in data[folder_id]:
                t = item.get('type')
                if t == 'folder':
                    folder_items.append(item)
                else:
                    media_items.append(item)
                    
        if len(media_items) > 0:
            has_tvshows = any(i.get('type') == 'tvshow' for i in media_items)
            has_movies = any(i.get('type') == 'item' for i in media_items)
            if has_tvshows and not has_movies:
                content_type = 'tvshows'
            elif has_movies and not has_tvshows:
                content_type = 'movies'
            else:
                content_type = 'movies'
        else:
            fid = (folder_id or '')
            if fid == 'Serien' or fid.startswith('Serien/'):
                content_type = 'tvshows'
            elif fid == 'Filme' or fid.startswith('Filme/'):
                content_type = 'movies'
            else:
                content_type = 'movies'
                
        xbmcplugin.setContent(handle, content_type)
        xbmcplugin.setPluginCategory(handle, 'Lite Favourites')
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
        
        folder_items.sort(key=lambda x: str(x.get('name')).lower())
        media_items.sort(key=lambda x: str(x.get('name')).lower())
        final_list = folder_items + media_items
        
        # --- NEU: SYSTEM-BUTTONS IM ROOT MENÜ ---
        if folder_id == 'root':
            # 1. Suchen-Button
            li_search = xbmcgui.ListItem('Suchen...')
            search_icon = 'DefaultAddonsSearch.png'
            li_search.setArt({'icon': search_icon, 'thumb': search_icon, 'poster': search_icon})
            li_search.setProperty('IsPlayable', 'false')
            search_url = build_url({'mode': 'search'})
            xbmcplugin.addDirectoryItem(handle, search_url, li_search, isFolder=True)
            
            # 2. Dropbox-Sync-Button
            li_sync = xbmcgui.ListItem('Sync mit Dropbox')
            sync_icon = 'DefaultAddonService.png'
            li_sync.setArt({'icon': sync_icon, 'thumb': sync_icon, 'poster': sync_icon})
            li_sync.setProperty('IsPlayable', 'false')
            sync_url = build_url({'mode': 'sync_now'})
            xbmcplugin.addDirectoryItem(handle, sync_url, li_sync, isFolder=False)
            
            # 3. Einstellungen-Button
            li_settings = xbmcgui.ListItem('Einstellungen')
            settings_icon = 'DefaultAddonProgram.png'
            li_settings.setArt({'icon': settings_icon, 'thumb': settings_icon, 'poster': settings_icon})
            li_settings.setProperty('IsPlayable', 'false')
            settings_url = build_url({'mode': 'open_settings'})
            xbmcplugin.addDirectoryItem(handle, settings_url, li_settings, isFolder=False)
            
        if len(final_list) == 0:
            li = xbmcgui.ListItem('[B][+] Ersten Ordner erstellen[/B]')
            li.setArt({'icon': 'DefaultAddSource.png'})
            li.setProperty('IsPlayable', 'false')
            add_folder_url = build_url({'mode': 'add_folder', 'parent': folder_id})
            xbmcplugin.addDirectoryItem(handle, add_folder_url, li, isFolder=False)
            
        for idx, item in enumerate(final_list):
            if item.get('type') == 'folder':
                url = build_url({'mode': 'browse', 'folder': item['id']})
                li = xbmcgui.ListItem(item['name'])
                if xbmcvfs.exists(ICON_PATH):
                    li.setArt({'icon': ICON_PATH})
                else:
                    li.setArt({'icon': 'DefaultFolder.png'})
                    
                add_folder_here_url = build_url({'mode': 'add_folder', 'parent': folder_id})
                remove_url = build_url({'mode': 'remove', 'parent': folder_id, 'index': str(data[folder_id].index(item))})
                move_url = build_url({'mode': 'select_target_folder', 'source_parent': folder_id, 'source_index': str(data[folder_id].index(item))})
                
                context_menu = [
                    ('Ordner hier hinzufügen', 'RunPlugin(' + add_folder_here_url + ')'),
                    ('In Ordner verschieben', 'RunPlugin(' + move_url + ')'),
                    ('Löschen', 'RunPlugin(' + remove_url + ')'),
                    ('Sync mit Dropbox', 'RunPlugin(' + build_url({'mode': 'sync_now'}) + ')')
                ]
                li.addContextMenuItems(context_menu)
                xbmcplugin.addDirectoryItem(handle, url, li, isFolder=True)
                
            else:
                li = xbmcgui.ListItem(item['name'])
                if 'art' in item and item['art']:
                    li.setArt(clean_artwork(item['art']))
                    
                info_dict = {
                    'mediatype': 'tvshow' if item.get('type') == 'tvshow' else 'movie',
                    'title': item['name']
                }
                if item.get('type') == 'tvshow':
                    info_dict['tvshowtitle'] = item['name']
                    
                if 'info' in item and item['info']:
                    for key, value in item['info'].items():
                        if value:
                            info_dict[key] = value
                li.setInfo('video', info_dict)
                li.setProperty('IsPlayable', 'false')
                
                add_folder_here_url = build_url({'mode': 'add_folder', 'parent': folder_id})
                remove_url = build_url({'mode': 'remove', 'parent': folder_id, 'index': str(data[folder_id].index(item))})
                update_info_url = build_url({'mode': 'update_info', 'parent': folder_id, 'index': str(data[folder_id].index(item))})
                move_url = build_url({'mode': 'select_target_folder', 'source_parent': folder_id, 'source_index': str(data[folder_id].index(item))})
                
                context_menu = [
                    ('Info aktualisieren', 'RunPlugin(' + update_info_url + ')'),
                    ('Ordner hier hinzufügen', 'RunPlugin(' + add_folder_here_url + ')'),
                    ('In Ordner verschieben', 'RunPlugin(' + move_url + ')'),
                    ('Löschen', 'RunPlugin(' + remove_url + ')'),
                    ('Sync mit Dropbox', 'RunPlugin(' + build_url({'mode': 'sync_now'}) + ')')
                ]
                li.addContextMenuItems(context_menu)
                
                final_url = get_tvshow_episodes(item['url']) if item.get('type') == 'tvshow' else item['url']
                final_url = final_url if final_url else item['url']
                
                xbmcplugin.addDirectoryItem(handle, final_url, li, isFolder=(item.get('type') == 'tvshow'))
                
        xbmcplugin.endOfDirectory(handle, updateListing=False, cacheToDisc=True)
        
        if focus_item:
            target_pos = -1
            offset = 0
            
            # Offset-Korrektur: Wenn wir im Root sind, addieren wir die 3 System-Buttons oben drauf!
            if folder_id == 'root':
                offset += 3
            if len(final_list) == 0:
                offset += 1
                
            for idx, item in enumerate(final_list):
                if item.get('name') == focus_item:
                    target_pos = idx + offset
                    break
                    
            if target_pos != -1:
                xbmc.log(f"LITE-FAV: Starte Turbo-Bot fuer '{focus_item}' an Index {target_pos}...", xbmc.LOGWARNING)
                
                def turbo_focus_task():
                    xbmc.sleep(500)
                    ITEMS_PER_ROW = 9
                    rows_down = target_pos // ITEMS_PER_ROW
                    steps_right = target_pos % ITEMS_PER_ROW
                    
                    xbmc.executebuiltin('Action(FirstPage)')
                    xbmc.sleep(50) 
                    xbmc.executebuiltin('Action(FirstPage)')
                    xbmc.sleep(100)
                    
                    for _ in range(rows_down):
                        xbmc.executebuiltin('Action(Down)')
                        xbmc.sleep(10)
                        
                    for _ in range(steps_right):
                        xbmc.executebuiltin('Action(Right)')
                        xbmc.sleep(10)
                        
                    xbmc.log(f"LITE-FAV: Turbo-Bot hat Ziel '{focus_item}' erreicht!", xbmc.LOGWARNING)
                    
                t = threading.Thread(target=turbo_focus_task)
                t.start()

def add_to_favourites_from_context():
    xbmc.sleep(200)
    list_item = getattr(sys, 'listitem', None)
    if not list_item:
        xbmcgui.Dialog().notification('Lite Favourites', 'Kein Item ausgewählt', xbmcgui.NOTIFICATION_ERROR, 2000)
        return

    label = list_item.getLabel()
    path = list_item.getPath()

    art = {}
    poster = list_item.getArt('poster')
    if poster:
        art['poster'] = poster
    else:
        thumb = list_item.getArt('thumb')
        if thumb:
            art['poster'] = thumb

    video_info = {}
    try:
        info = list_item.getVideoInfoTag()
        if info:
            video_info['title'] = info.getTitle()
            video_info['plot'] = info.getPlot()
            video_info['year'] = info.getYear()
            video_info['rating'] = info.getRating()
            video_info['genre'] = safe_string(info.getGenre())
            video_info['studio'] = safe_string(info.getStudio())
    except Exception:
        pass

    if not path:
        xbmcgui.Dialog().notification('Lite Favourites', 'Ungültiger Pfad', xbmcgui.NOTIFICATION_ERROR, 2000)
        return

    item_type = detect_fav_type_from_context(list_item)
    scope = 'Serien' if item_type == 'tvshow' else 'Filme'

    data = load_favourites()
    folders = get_scoped_folders(data, scope)
    
    # "Neuer Ordner" Option zur Liste hinzufügen
    folder_names = ["[ Neuer Ordner... ]"] + [f[0] for f in folders]
    
    dialog = xbmcgui.Dialog()
    xbmc.sleep(100)
    selected = dialog.select('Zielordner auswählen', folder_names)
    
    if selected == 0:
        # User möchte einen neuen Ordner erstellen
        kb = xbmc.Keyboard('', f'Neuen Ordner in "{scope}" erstellen')
        kb.doModal()
        if kb.isConfirmed() and kb.getText():
            new_folder_name = kb.getText()
            # Finde die Root-ID für den Scope (Serien oder Filme)
            parent_id = find_root_folder_id(data, scope) or 'root'
            
            # Ordner erstellen
            add_folder(new_folder_name, parent_id)
            
            # Da add_folder die Daten speichert, müssen wir sie für den Favoriten neu laden
            data = load_favourites()
            new_folder_id = parent_id + '/' + new_folder_name if parent_id != 'root' else new_folder_name
            
            # Item direkt in den neu erstellten Ordner speichern
            video_info['mediatype'] = 'tvshow' if item_type == 'tvshow' else 'movie'
            video_info = clean_info_dict(video_info)
            art = clean_artwork(art)
            if add_favourite(label, path, new_folder_id, item_type, art, video_info):
                xbmcgui.Dialog().notification('Lite Favourites', f'In neuen Ordner "{new_folder_name}" gespeichert', xbmcgui.NOTIFICATION_INFO, 3000)

    elif selected > 0:
        # User hat einen existierenden Ordner gewählt (Index - 1 wegen "Neuer Ordner" Eintrag)
        folder_id = folders[selected - 1][1]
        video_info['mediatype'] = 'tvshow' if item_type == 'tvshow' else 'movie'
        video_info = clean_info_dict(video_info)
        art = clean_artwork(art)
        if add_favourite(label, path, folder_id, item_type, art, video_info):
            xbmcgui.Dialog().notification('Lite Favourites', 'Zu "' + folders[selected - 1][0].strip() + '" hinzugefügt', xbmcgui.NOTIFICATION_INFO, 3000)

# ============ DROPBOX SYNC FUNKTIONEN ============

def _parse_dropbox_timestamp(timestamp_str):
    """Parser für Dropbox-Zeitstempel (ISO 8601) mit dateutil"""
    if not timestamp_str:
        return 0
    
    try:
        from dateutil import parser
        dt = parser.isoparse(timestamp_str)
        return dt.timestamp()
    except Exception as e:
        xbmc.log(f"_parse_dropbox_timestamp Fehler: {str(e)}", xbmc.LOGERROR)
        return 0

def get_dropbox_access_token():
    """Holt einen gültigen Access Token (holt bei Bedarf einen neuen)"""
    import urllib.request
    import urllib.error
    
    refresh_token = ADDON.getSetting('dropbox_refresh_token')
    app_key = ADDON.getSetting('dropbox_app_key')
    app_secret = ADDON.getSetting('dropbox_app_secret')
    
    if not refresh_token or not app_key or not app_secret:
        xbmc.log("Dropbox: Fehlende Zugangsdaten", xbmc.LOGWARNING)
        return None
    
    # Prüfen, ob wir bereits einen gültigen Access Token haben
    access_token = ADDON.getSetting('dropbox_access_token')
    expires_at = ADDON.getSetting('dropbox_token_expires_at')
    
    if access_token and expires_at:
        try:
            if float(expires_at) > time.time() + 300:
                return access_token
        except:
            pass
    
    # Neuen Access Token holen
    xbmc.log("Dropbox: Hole neuen Access Token...", xbmc.LOGINFO)
    
    url = "https://api.dropboxapi.com/oauth2/token"
    
    data = urllib.parse.urlencode({
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'client_id': app_key,
        'client_secret': app_secret
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            new_token = response_data.get('access_token')
            expires_in = response_data.get('expires_in', 14400)
            
            if new_token:
                ADDON.setSetting('dropbox_access_token', new_token)
                ADDON.setSetting('dropbox_token_expires_at', str(time.time() + expires_in))
                xbmc.log("Dropbox: Neuer Access Token erfolgreich geholt", xbmc.LOGINFO)
                return new_token
            else:
                xbmc.log("Dropbox: Kein Access Token in Antwort", xbmc.LOGERROR)
                return None
                
    except Exception as e:
        xbmc.log(f"Dropbox: Fehler beim Token-Refresh: {str(e)}", xbmc.LOGERROR)
        return None

def get_file_timestamp_dropbox(access_token, dropbox_folder, filename='favourites.json'):
    """Holt den Zeitstempel der Datei von Dropbox"""
    import urllib.request
    import urllib.error
    import traceback
    
    xbmc.log("=== get_file_timestamp_dropbox START ===", xbmc.LOGINFO)
    
    try:
        url = "https://api.dropboxapi.com/2/files/get_metadata"
        dropbox_path = f"/{dropbox_folder}/{filename}"
        
        xbmc.log(f"URL: {url}", xbmc.LOGINFO)
        xbmc.log(f"Path: {dropbox_path}", xbmc.LOGINFO)
        
        # Test: json.dumps funktioniert?
        try:
            test_json = json.dumps({'path': dropbox_path})
            xbmc.log(f"json.dumps funktioniert: {test_json[:50]}", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"json.dumps FEHLER: {str(e)}", xbmc.LOGERROR)
        
        data = json.dumps({'path': dropbox_path}).encode('utf-8')
        xbmc.log(f"Data erstellt, Länge: {len(data)}", xbmc.LOGINFO)
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
        )
        xbmc.log("Request erstellt", xbmc.LOGINFO)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            xbmc.log("Response erhalten", xbmc.LOGINFO)
            response_data = json.loads(response.read().decode('utf-8'))
            xbmc.log(f"Response Data: {response_data}", xbmc.LOGINFO)
            dropbox_modified = response_data.get('server_modified', '')
            xbmc.log(f"server_modified: {dropbox_modified}", xbmc.LOGINFO)
            if dropbox_modified:
                timestamp = _parse_dropbox_timestamp(dropbox_modified)
                xbmc.log(f"Timestamp: {timestamp}", xbmc.LOGINFO)
                return timestamp
            return None
            
    except urllib.error.HTTPError as e:
        xbmc.log(f"HTTPError: Code={e.code}, msg={e.msg}", xbmc.LOGERROR)
        if e.code == 401:
            raise Exception("Token expired")
        elif e.code == 409:
            return None
        else:
            return None
    except Exception as e:
        xbmc.log(f"Allgemeiner Fehler: {str(e)}", xbmc.LOGERROR)
        xbmc.log(f"Traceback: {traceback.format_exc()}", xbmc.LOGERROR)
        return None

def get_file_timestamp_local(filename='favourites.json'):
    """Holt den Zeitstempel der lokalen Datei"""
    filepath = os.path.join(DATA_PATH, filename)
    
    if not xbmcvfs.exists(filepath):
        return None
    
    try:
        return os.path.getmtime(filepath)
    except Exception as e:
        xbmc.log(f"Fehler beim Abrufen des lokalen Zeitstempels: {str(e)}", xbmc.LOGERROR)
        return None

def get_dropbox_file_content(access_token, dropbox_folder, filename='favourites.json'):
    """Liest den Inhalt einer Datei von Dropbox"""
    import urllib.request
    import urllib.error
    
    dropbox_path = f"/{dropbox_folder}/{filename}"
    url = "https://content.dropboxapi.com/2/files/download"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Dropbox-API-Arg': json.dumps({'path': dropbox_path})
    }
    
    req = urllib.request.Request(url, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise Exception("Token expired")
        xbmc.log(f"Fehler beim Lesen der Dropbox-Datei: {e.code}", xbmc.LOGERROR)
        return None
    except Exception as e:
        xbmc.log(f"Fehler beim Lesen der Dropbox-Datei: {str(e)}", xbmc.LOGERROR)
        return None

def download_from_dropbox(access_token, dropbox_folder, filename='favourites.json'):
    """Lädt die Datei von Dropbox herunter"""
    import urllib.request
    import urllib.error
    
    dropbox_path = f"/{dropbox_folder}/{filename}"
    local_path = os.path.join(DATA_PATH, filename)
    
    url = "https://content.dropboxapi.com/2/files/download"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Dropbox-API-Arg': json.dumps({'path': dropbox_path})
    }
    
    req = urllib.request.Request(url, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            
            if not xbmcvfs.exists(DATA_PATH):
                xbmcvfs.mkdirs(DATA_PATH)
            
            with open(local_path, 'wb') as f:
                f.write(content)
            
            clear_cache()
            xbmc.log(f"Datei von Dropbox heruntergeladen: {local_path}", xbmc.LOGINFO)
            return True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise Exception("Token expired")
        xbmc.log(f"Fehler beim Download von Dropbox: {e.code}", xbmc.LOGERROR)
        return False
    except Exception as e:
        xbmc.log(f"Fehler beim Download von Dropbox: {str(e)}", xbmc.LOGERROR)
        return False

def upload_to_dropbox(access_token, dropbox_folder, filename='favourites.json'):
    """Lädt die Datei zu Dropbox hoch"""
    import urllib.request
    import urllib.error
    
    dropbox_path = f"/{dropbox_folder}/{filename}"
    local_path = os.path.join(DATA_PATH, filename)
    
    if not xbmcvfs.exists(local_path):
        xbmc.log(f"Lokale Datei nicht gefunden: {local_path}", xbmc.LOGWARNING)
        return False
    
    url = "https://content.dropboxapi.com/2/files/upload"
    
    with open(local_path, 'rb') as f:
        file_content = f.read()
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/octet-stream',
        'Dropbox-API-Arg': json.dumps({'path': dropbox_path, 'mode': 'overwrite'})
    }
    
    req = urllib.request.Request(url, data=file_content, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            xbmc.log(f"Datei zu Dropbox hochgeladen: {dropbox_path}", xbmc.LOGINFO)
            return True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise Exception("Token expired")
        xbmc.log(f"Fehler beim Upload zu Dropbox: {e.code}", xbmc.LOGERROR)
        return False
    except Exception as e:
        xbmc.log(f"Fehler beim Upload zu Dropbox: {str(e)}", xbmc.LOGERROR)
        return False

def sync_with_dropbox():
    """Hauptfunktion für die Synchronisation mit Dropbox"""
    dropbox_folder = ADDON.getSetting('dropbox_folder')
    
    if not dropbox_folder:
        status = "Fehler: Ordner nicht konfiguriert"
        ADDON.setSetting('sync_status', status)
        return False
    
    access_token = get_dropbox_access_token()
    if not access_token:
        status = "Fehler: Kein gültiger Access Token"
        ADDON.setSetting('sync_status', status)
        return False
    
    xbmc.log(f"Starte Sync mit Dropbox, Ordner: {dropbox_folder}", xbmc.LOGINFO)
    
    local_path = os.path.join(DATA_PATH, 'favourites.json')
    local_exists = xbmcvfs.exists(local_path)
    
    # Dropbox-Inhalt und Zeitstempel abrufen
    dropbox_content = None
    dropbox_exists = False
    dropbox_timestamp = None
    
    try:
        dropbox_timestamp = get_file_timestamp_dropbox(access_token, dropbox_folder)
        dropbox_exists = dropbox_timestamp is not None
        if dropbox_exists:
            dropbox_content = get_dropbox_file_content(access_token, dropbox_folder)
    except Exception as e:
        if "Token expired" in str(e):
            xbmc.log("Token abgelaufen, breche ab", xbmc.LOGINFO)
            status = "Token abgelaufen, bitte neu starten"
            ADDON.setSetting('sync_status', status)
            return False
    
    # Lokalen Inhalt und Zeitstempel lesen
    local_content = None
    local_timestamp = None
    if local_exists:
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                local_content = f.read()
            local_timestamp = os.path.getmtime(local_path)
        except Exception as e:
            xbmc.log(f"Fehler beim Lesen der lokalen Datei: {str(e)}", xbmc.LOGERROR)
    
    # Fall 1: Keine Datei vorhanden
    if not dropbox_exists and not local_exists:
        status = "Keine Datei gefunden"
        ADDON.setSetting('sync_status', status)
        return False
    
    # Fall 2: Nur lokal vorhanden -> Upload
    elif not dropbox_exists:
        status = "Nur lokal vorhanden -> Upload"
        ADDON.setSetting('sync_status', status)
        result = upload_to_dropbox(access_token, dropbox_folder)
        if result:
            ADDON.setSetting('last_sync_time', datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
        return result
    
    # Fall 3: Nur in Dropbox vorhanden -> Download
    elif not local_exists:
        status = "Nur in Dropbox vorhanden -> Download"
        ADDON.setSetting('sync_status', status)
        result = download_from_dropbox(access_token, dropbox_folder)
        if result:
            ADDON.setSetting('last_sync_time', datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
        return result
    
    # Fall 4: Beide vorhanden -> Inhalt vergleichen
    else:
        # 1. Prüfen ob Inhalte identisch sind
        if local_content == dropbox_content:
            status = "Synchron (Inhalte identisch)"
            ADDON.setSetting('sync_status', status)
            ADDON.setSetting('last_sync_time', datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
            return True
        
        # 2. Inhalte unterschiedlich -> Zeitstempel vergleichen (mit Toleranz)
        tolerance = 60.0  # 60 Sekunden Toleranz
        
        xbmc.log(f"Local Timestamp: {local_timestamp}, Dropbox Timestamp: {dropbox_timestamp}", xbmc.LOGINFO)
        
        if local_timestamp > dropbox_timestamp + tolerance:
            # Lokal neuer -> Upload
            status = f"Lokal neuer -> Upload (lokal: {datetime.fromtimestamp(local_timestamp).strftime('%H:%M:%S')}, Dropbox: {datetime.fromtimestamp(dropbox_timestamp).strftime('%H:%M:%S')})"
            ADDON.setSetting('sync_status', status)
            result = upload_to_dropbox(access_token, dropbox_folder)
            
        elif dropbox_timestamp > local_timestamp + tolerance:
            # Dropbox neuer -> Download
            status = f"Dropbox neuer -> Download (Dropbox: {datetime.fromtimestamp(dropbox_timestamp).strftime('%H:%M:%S')}, lokal: {datetime.fromtimestamp(local_timestamp).strftime('%H:%M:%S')})"
            ADDON.setSetting('sync_status', status)
            result = download_from_dropbox(access_token, dropbox_folder)
            
        else:
            # Zeitstempel zu nah beieinander -> Konflikt, lokal bevorzugen (Upload)
            status = f"Zeitstempel-Konflikt (Unterschied < {tolerance} Sek.) -> Upload (lokal bevorzugt)"
            ADDON.setSetting('sync_status', status)
            result = upload_to_dropbox(access_token, dropbox_folder)
        
        if result:
            ADDON.setSetting('last_sync_time', datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
        return result

def schedule_sync():
    """Timer für regelmäßige Synchronisation"""
    interval = int(ADDON.getSetting('sync_interval'))
    
    if interval <= 0:
        return
    
    last_sync = ADDON.getSetting('last_sync_time')
    
    if last_sync != "Nie":
        try:
            last_sync_time = datetime.strptime(last_sync, '%d.%m.%Y %H:%M:%S')
            time_diff = (datetime.now() - last_sync_time).total_seconds() / 60
            
            if time_diff < interval:
                return
        except:
            pass
    
    sync_with_dropbox()

def router(paramstring):
        params = dict(parse_qsl(paramstring))
        
        if not params:
            access_token = ADDON.getSetting('dropbox_access_token')
            if access_token and int(ADDON.getSetting('sync_interval')) > 0:
                schedule_sync()
            list_directory()
            
        elif params.get('mode') == 'browse':
            focus_target = params.get('focus_item')
            if focus_target:
                import urllib.parse
                focus_target = urllib.parse.unquote(focus_target)
            list_directory(params.get('folder', 'root'), focus_target)
            
        elif params.get('mode') == 'add_folder':
            kb = xbmc.Keyboard('', 'Ordnername eingeben')
            kb.doModal()
            if kb.isConfirmed():
                name = kb.getText()
                if name:
                    add_folder(name, params.get('parent', 'root'))
                    xbmc.executebuiltin('Container.Refresh')
                    
        elif params.get('mode') == 'add_fav':
            kb = xbmc.Keyboard('', 'Favoriten-Name eingeben')
            kb.doModal()
            if kb.isConfirmed():
                name = kb.getText()
                if name:
                    kb2 = xbmc.Keyboard('', 'URL/Pfad eingeben (z.B. plugin://...)')
                    kb2.doModal()
                    if kb2.isConfirmed():
                        url = kb2.getText()
                        if url:
                            add_favourite(name, url, params.get('parent', 'root'))
                            xbmc.executebuiltin('Container.Refresh')
                            
        elif params.get('mode') == 'add_from_context':
            add_to_favourites_from_context()
            
        elif params.get('mode') == 'remove':
            dialog = xbmcgui.Dialog()
            if dialog.yesno('Bestätigung', 'Wirklich löschen?'):
                remove_item(params.get('parent', 'root'), int(params.get('index', 0)))
                xbmc.executebuiltin('Container.Refresh')
                
        elif params.get('mode') == 'clear_cache':
            clear_cache()
            xbmcgui.Dialog().notification('Lite Favourites', 'Cache geleert', xbmcgui.NOTIFICATION_INFO, 2000)
            xbmc.executebuiltin('Container.Refresh')
            
        elif params.get('mode') == 'update_info':
            update_item_info(params.get('parent', 'root'), int(params.get('index', 0)))
            
        elif params.get('mode') == 'select_target_folder':
            data = load_favourites()
            source_parent = params.get('source_parent', 'root')
            source_index = int(params.get('source_index', 0))
            
            if source_parent not in data or source_index >= len(data[source_parent]):
                return
                
            item = data[source_parent][source_index]
            item_type = item.get('type')
            folders = get_all_folders(data)
            allowed_root = None
            
            if item_type == 'tvshow':
                allowed_root = 'Serien'
            elif item_type == 'item':
                allowed_root = 'Filme'
                
            if allowed_root:
                folders = [
                    (folder_name, folder_id)
                    for (folder_name, folder_id) in folders
                    if folder_id != 'root' and (folder_id == allowed_root or folder_id.startswith(allowed_root + '/'))
                ]
                if not folders:
                    xbmcgui.Dialog().notification(
                        'Lite Favourites',
                        f'Keine Zielordner unter "{allowed_root}"',
                        xbmcgui.NOTIFICATION_WARNING,
                        2500
                    )
                    return
                    
            if item_type == 'folder':
                folder_self_id = item.get('id', '')
                filtered_folders = []
                for folder_name, folder_id in folders:
                    if folder_id != folder_self_id and not folder_id.startswith(folder_self_id + '/'):
                        filtered_folders.append((folder_name, folder_id))
                folders = filtered_folders
                
            folder_names = [f[0] for f in folders]
            dialog = xbmcgui.Dialog()
            selected = dialog.select('Zielordner auswählen', folder_names)
            
            if selected >= 0:
                target_parent = folders[selected][1]
                if move_item(source_parent, source_index, target_parent):
                    xbmc.executebuiltin('Container.Refresh')
                    
        elif params.get('mode') == 'sync_now':
            xbmcgui.Dialog().notification('Lite Favourites', 'Synchronisation wird gestartet...', xbmcgui.NOTIFICATION_INFO, 2000)
            sync_with_dropbox()
            xbmc.executebuiltin('Container.Refresh')
            
        elif params.get('mode') == 'import_sf':
            import_super_favourites()
            xbmc.executebuiltin('Dialog.Close(settings)')
            xbmc.executebuiltin('Container.Refresh')
            
        elif params.get('mode') == 'search':
            search_items()
            
        elif params.get('mode') == 'search_goto':
            folder = params.get('folder', 'root')
            focus_target = params.get('focus_item', '')
            
            query = {'mode': 'browse', 'folder': folder}
            if focus_target:
                query['focus_item'] = focus_target
                
            url = build_url(query)
            xbmc.executebuiltin(f'Container.Update("{url}",replace)')
            
        elif params.get('mode') == 'open_settings':
            xbmc.executebuiltin(f'Addon.OpenSettings({ADDON_ID})')
            
        # --- NEU: DER DUMMY FÜR DEN TMDB HELPER ---
        elif params.get('mode') == 'search_tmdb_dummy':
            query = params.get('query', '')
            
            try:
                from urllib.parse import quote
            except ImportError:
                from urllib import quote
                
            safe_query = quote(query)
            
            # TMDb Helper braucht zwingend den Typ. Wir lassen den User kurz wählen:
            dialog = xbmcgui.Dialog()
            ret = dialog.select('TMDb Helper Suche: Was suchst du?', ['Filme', 'Serien'])
            
            if ret == 0:
                search_type = 'movie'
            elif ret == 1:
                search_type = 'tv'
            else:
                return # User hat abgebrochen
                
            # Die fertige, fehlerfreie URL für den TMDb Helper
            tmdb_url = f"plugin://plugin.video.themoviedb.helper/?info=search&type={search_type}&query={safe_query}"
            
            # Suchergebnis-Ansicht öffnen
            xbmc.executebuiltin(f'Container.Update("{tmdb_url}")')
            
if __name__ == '__main__':
    router(sys.argv[2][1:])

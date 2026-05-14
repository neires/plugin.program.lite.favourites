import sys
import xbmc

# Setze die richtigen sys.argv Parameter
sys.argv = ['plugin://plugin.program.lite.favourites/', '1', '?mode=add_from_context']

# Importiere und führe den Router aus
import addon
addon.router(sys.argv[2][1:])
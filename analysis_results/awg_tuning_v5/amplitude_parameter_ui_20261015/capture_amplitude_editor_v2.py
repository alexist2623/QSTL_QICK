"""Retry the same private rendering with an explicitly loaded Windows font.

The first screenshots are retained: their offscreen system-font rendering was
blank. No production widget code, settings, dimensions or contents are edited.
"""
from pathlib import Path
import hashlib

original = Path(__file__).with_name('capture_amplitude_editor.py')
source = original.read_text(encoding='utf-8')
assert hashlib.sha256(original.read_bytes()).hexdigest() == '85768ad97b298770ff9509d05b5ddb740f2849b36b221304fad2e7e27f71e74d'
source = source.replace("'screenshots.json'", "'screenshots_v2.json'")
source = source.replace("'preset_hahn_manual.png'", "'preset_hahn_manual_v2.png'")
source = source.replace("'custom_calibration.png'", "'custom_calibration_v2.png'")
source = source.replace("app.setFont(QtGui.QFont('Segoe UI', 9))", """
font_path = 'C:/Windows/Fonts/segoeui.ttf'
font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
assert font_id >= 0, 'Could not load the explicit offscreen font'
font_family = QtGui.QFontDatabase.applicationFontFamilies(font_id)[0]
app.setFont(QtGui.QFont(font_family, 9))
""")
exec(compile(source, str(original), 'exec'), globals())

from PyQt6.QtWidgets import *
from json_schema_dialog import SchemaEditor

app = QApplication([])

# Invalid path.
dialog = SchemaEditor("")
if dialog.initial_valid:
    print("[1] PASS")
else:
    print("[1] FAIL")

# Broken JSON.
dialog = SchemaEditor("tests/json_schema/invalid_schema_1.json")
if dialog.initial_valid:
    print("[2] PASS")
else:
    print("[2] FAIL")

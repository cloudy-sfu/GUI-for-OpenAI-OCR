from PyQt6.QtWidgets import QApplication

from json_schema_dialog import SchemaEditor

app = QApplication([])
app.setStyleSheet(
    f'QWidget {{'
    f'    font-family: "Microsoft YaHei", Calibri, Ubuntu; '
    f'    font-size: 12pt;'
    f'}}'
)
dialog = SchemaEditor("tests/json_schema/user_profile.json")
# dialog = SchemaEditor()
if dialog.initial_valid:
    action = dialog.exec()

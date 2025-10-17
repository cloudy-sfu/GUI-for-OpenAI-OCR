from PyQt6.QtWidgets import QApplication

from table_dialog import TableDialog

app = QApplication([])
dialog = TableDialog(
    columns=["A", "B", "C", "D", "E"],
    data=[[f"r{r + 1}c{c + 1}" for c in range(5)] for r in range(200)],
    # indices auto 1..N
)
dialog.exec()

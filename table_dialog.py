from itertools import product

from PyQt6.QtWidgets import *


class TableDialog(QDialog):
    def __init__(self, data, columns=None, indices=None):
        super().__init__()
        m = len(data)
        try:
            n = len(columns or data[0])
        except IndexError:
            raise Exception("Argument 'columns' is not provided, and 'data' is empty. "
                            "Cannot make a table.")
        assert all(len(data[i]) == n for i in range(m)), \
            (f"Based on provided 'data' and 'columns', each row (element of 'data') "
             f"must be of length {n}.")

        layout = QVBoxLayout()
        table = QTableWidget()
        table.setRowCount(m)
        table.setColumnCount(n)
        for i, j in product(range(m), range(n)):
            value = data[i][j]
            if value is None:
                continue
            cell = QTableWidgetItem(str(value))
            table.setItem(i, j, cell)
        if indices is not None:
            table.setVerticalHeaderLabels(indices)
        if columns is not None:
            table.setHorizontalHeaderLabels(columns)
        table.resizeColumnsToContents()
        scroll_bar_w = table.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)
        edge_w = table.frameWidth() * 2
        natural_width = (sum(table.columnWidth(j) for j in range(n))
                         + table.verticalHeader().width()
                         + scroll_bar_w
                         + edge_w)
        natural_height = (sum(table.rowHeight(i) for i in range(m))
                          + table.horizontalHeader().height()
                          + scroll_bar_w
                          + edge_w)


        screen_size = self.screen().size()
        desired_table_width = round(0.3 * screen_size.width())
        desired_table_height = round(0.5 * screen_size.height())
        table.setMinimumWidth(min(natural_width, desired_table_width))
        table.setMinimumHeight(min(natural_height, desired_table_height))
        layout.addWidget(table)
        self.setLayout(layout)

        self.table = table
        self.layout = layout

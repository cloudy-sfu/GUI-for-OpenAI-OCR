import json
import os
from operator import attrgetter

import jsonschema
from PyQt6.QtCore import Qt, pyqtSignal, QSignalBlocker
from PyQt6.QtGui import QAction, QFontMetrics
from PyQt6.QtWidgets import *

class SchemaEditor(QDialog):
    def __init__(self, path=None, parent=None):
        super().__init__(parent)
        screen_size = self.screen().size()
        window_width = round(0.75 * screen_size.width())
        window_height = round(window_width / 1.6)
        self.setMinimumWidth(window_width)
        self.setMinimumHeight(window_height)

        # Main window
        layout_1 = QVBoxLayout()
        layout = QSplitter(Qt.Orientation.Horizontal)

        # Left column
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Node", "", "Type", "Description"])
        # Show full text if there’s room
        self.tree.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.tree.itemSelectionChanged.connect(self.open_tree_selected)
        self.path = []  # identical location to selected node
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Right column
        right_col_1 = QWidget()
        right_col = QVBoxLayout()
        right_col_1.setLayout(right_col)

        # Right column -> Field name
        right_col.addWidget(QLabel("Field name:"))
        self.field_name = QLineEdit()
        right_col.addWidget(self.field_name)

        # Right column -> Required?
        self.required_ = QCheckBox()
        self.required_.setText("Required")
        right_col.addWidget(self.required_)

        # Right column -> Type
        right_col.addWidget(QLabel("Type:"))
        self.type_list = QListWidget()
        self.type_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.type_list.addItems([
            "string", "number", "object", "array", "boolean", "null"
        ])
        font = QFontMetrics(self.type_list.font())
        line_height = font.height()
        n_lines = self.type_list.count()
        spacing = self.type_list.spacing()
        frame_width = self.type_list.frameWidth()
        zoom_pct = QApplication.primaryScreen().devicePixelRatio()
        self.type_list.setFixedHeight(int(
            (line_height * n_lines + spacing * (n_lines - 1) + frame_width * 2) * zoom_pct
        ))
        right_col.addWidget(self.type_list)

        # Right column -> Description
        right_col.addWidget(QLabel("Description:"))
        self.description = QTextEdit()
        right_col.addWidget(self.description)

        # Right column -> Submit
        update_node_layout = QHBoxLayout()
        self.update_node_button = QPushButton()
        self.update_node_button.setText("Update")
        self.update_node_button.setShortcut("Ctrl+S")
        self.update_node_button.clicked.connect(self.update_node)
        update_node_layout.addStretch()
        update_node_layout.addWidget(self.update_node_button)
        update_node_layout.addStretch()
        right_col.addLayout(update_node_layout)

        # Menu bar -> Edit
        help_ = QAction("&Help", self)
        help_.triggered.connect(self.help)
        help_.setShortcut("F1")

        # Menu bar -> Validate
        v_schema = QAction("Validate &schema", self)
        v_schema.triggered.connect(self.validate_schema)

        # Menu bar -> First-level buttons
        edit_ = QMenu('&Edit', self)
        edit_.addActions([
            help_,
        ])
        validate = QMenu("&Validate", self)
        validate.addActions([
            v_schema,
        ])

        # Menu bar
        menu = QMenuBar(self)
        menu.addMenu(edit_)
        menu.addMenu(validate)
        layout_1.setMenuBar(menu)

        # Dialog buttons
        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)

        # Collect to main window
        layout.addWidget(self.tree)
        right_col.addStretch()
        layout.addWidget(right_col_1)
        # left:right = 3:2, after adding all widgets
        layout.setStretchFactor(0, 3)
        layout.setStretchFactor(1, 2)
        layout_1.addWidget(layout)
        layout_1.addWidget(dialog_buttons)
        self.setLayout(layout_1)

        # Properties
        self.initial_prevented = False
        default_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
            "required": []
        }
        if path is None:
            self.schema = default_schema
        else:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.schema = json.load(f)
            # path=None is caught, so TypeError impossible
            except (FileNotFoundError, json.JSONDecodeError):
                self.initial_prevented = True
                self.schema = default_schema
                self.icon_message(
                    "Fail to open schema",
                    "Schema file doesn't exist or isn't a schema.",
                    QStyle.StandardPixmap.SP_FileIcon,
                )
                return
        self.refresh_tree()

    def help(self):
        self.icon_message(
            "Help",
            "[Shortcuts]\n"
            "Expand: Ctrl Shift = (it expands the selected node; to expand all, select "
            "the root node)\n"
            "Collapse: Ctrl -\n"
            "Update: Ctrl S (it saves the currently selected node)\n"
            "\n"
            "[Symbols]\n"
            "Required field: *\n"
            "Element of array: E\n"
        )

    def _validate_schema(self):
        try:
            jsonschema.Draft7Validator.check_schema(self.schema)
        except jsonschema.exceptions.SchemaError as e:
            error_message = "Schema is invalid:\n"
            path_str = "schema"
            for p in e.path:
                if isinstance(p, str):
                    p_ = "\"" + p + "\""
                else:
                    p_ = str(p)
                path_str += "[" + p_ + "]"
            error_message += f"At {path_str}, {e.message}.\n"
            return False, error_message
        else:
            return True, "Schema is valid."

    def validate_schema(self):
        is_valid, message = self._validate_schema()
        if is_valid:
            level = "info"
        else:
            level = "warn"
        self.silent_message(level, "Validator", message)

    def silent_message(self, level, title, text):
        match level:
            case "info":
                icon = QStyle.StandardPixmap.SP_MessageBoxInformation
            case "warn":
                icon = QStyle.StandardPixmap.SP_MessageBoxWarning
            case "critical":
                icon = QStyle.StandardPixmap.SP_MessageBoxCritical
            case "question":
                icon = QStyle.StandardPixmap.SP_MessageBoxQuestion
            case _:
                raise ValueError("Function silent_message gets unsupported level.")
        size = QApplication.style().pixelMetric(QStyle.PixelMetric.PM_MessageBoxIconSize)
        message = QMessageBox(self)
        pix = QApplication.style().standardIcon(icon).pixmap(size, size)
        message.setIconPixmap(pix)
        message.setWindowTitle(title)
        message.setText(text)
        message.exec()

    def icon_message(self, title, text, icon=None):
        size = QApplication.style().pixelMetric(QStyle.PixelMetric.PM_MessageBoxIconSize)
        message = QMessageBox(self)
        if icon is not None:
            pix = QApplication.style().standardIcon(icon).pixmap(size, size)
            message.setIconPixmap(pix)
        message.setWindowTitle(title)
        message.setText(text)
        message.exec()

    def refresh_tree(self):
        self.tree.clear()
        root_item = QTreeWidgetItem([
            "root",
            "*",
            display_type(self.schema.get("type")),
            self.schema.get("description", "")
        ])
        self.tree.addTopLevelItem(root_item)
        json_to_tree(
            root_item,
            self.schema.get("properties", {}),
            self.schema.get("required", []),
        )
        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)
        self.tree.resizeColumnToContents(2)

    def open_tree_selected(self):
        selected_items = self.tree.selectedItems()
        if len(selected_items) < 1:
            return
        node = selected_items[0]
        self.path = node_in_tree_to_path(node)
        if not self.path:  # root node
            self.required_.setEnabled(False)
            self.field_name.setEnabled(False)
            self.type_list.setEnabled(False)
            self.description.setEnabled(True)

            self.required_.setChecked(True)
            self.field_name.setText("")
            self.type_list.clearSelection()
            self.description.setText(self.schema.get("description", ""))
            return

        p2 = path_to_dict_pointer(self.schema, self.path[:-2])
        p1 = p2[self.path[-2]]
        self_ = p1[self.path[-1]]
        if is_array(p1.get("type")):  # Element of array
            self.required_.setEnabled(False)
            self.field_name.setEnabled(False)
            self.type_list.setEnabled(True)
            self.description.setEnabled(False)

            self.required_.setChecked(False)
            self.field_name.setText("")
            self.description.clear()
        else:
            self.required_.setEnabled(True)
            self.field_name.setEnabled(True)
            self.type_list.setEnabled(True)
            self.description.setEnabled(True)

            self.required_.setChecked(self.path[-1] in p2.get("required", []))
            self.field_name.setText(self.path[-1])
            self.description.setText(self_.get("description", ""))

        type_ = self_.get("type")
        if type_ is None:
            self.type_list.clearSelection()
        elif isinstance(type_, str):
            for i in range(self.type_list.count()):
                item = self.type_list.item(i)
                item.setSelected(item.text() == type_)
        else:
            for i in range(self.type_list.count()):
                item = self.type_list.item(i)
                item.setSelected(item.text() in type_)

    def update_node(self):
        field_name = self.field_name.text()
        required = self.required_.isChecked()
        type_list = [item.text() for item in self.type_list.selectedItems()]
        description = self.description.toPlainText()

        if not self.path:  # root node
            self.schema["description"] = description
            is_valid, message = self._validate_schema()
            if is_valid:
                self.refresh_tree()
            else:
                self.silent_message("warn", "Validator", message)
            return
        if not type_list:
            self.silent_message(
                "warn", "Invalid change", "Type cannot be empty.")
            return
        p2 = path_to_dict_pointer(self.schema, self.path[:-2])
        p1 = p2[self.path[-2]]
        self_ = p1[self.path[-1]]
        if len(type_list) == 1:
            self_["type"] = type_list[0]
        else:
            self_["type"] = type_list
        if not is_array(p1.get("type")):  # Not element of array
            self_["description"] = description
            new_field_name = field_name
            old_field_name = self.path[-1]
            required_set = set(p2["required"])
            # When renamed
            if new_field_name != old_field_name:
                p1[new_field_name] = self_
                del p1[old_field_name]
                self.path[-1] = new_field_name
                required_set = required_set.difference({old_field_name})
            # Safely update required list
            if required:
                required_set = required_set.union({new_field_name})
            else:
                required_set = required_set.difference({new_field_name})
            p2["required"] = list(required_set)
        is_valid, message = self._validate_schema()
        if is_valid:
            self.refresh_tree()
        else:
            self.silent_message("warn", "Validator", message)


def path_to_dict_pointer(dict_, path):
    p = dict_
    for l in path:
        p = p[l]
    return p


def node_in_tree_to_path(node):
    path = []
    while node:
        field_name = node.data(0, Qt.ItemDataRole.EditRole)
        if field_name:
            path.append(field_name)
            path.append("properties")
        else:
            path.append("items")
        node = node.parent()
    path.pop()  # Don't need root node and redundant properties beyond root
    path.pop()
    path.reverse()
    return path


def display_type(type_) -> str:
    if type_ is None:
        return ""
    elif isinstance(type_, str):
        return type_
    elif isinstance(type_, list):
        return " | ".join(type_)
    else:
        raise ValueError(f"JSON schema is invalid: field type \"{type_}\" is invalid.")


def json_to_tree(parent, dict_, required):
    assert isinstance(parent, QTreeWidgetItem), "Parent node is not a tree item."
    for field, property_ in dict_.items():
        self_ = QTreeWidgetItem([
            field,
            "*" * (field in required),
            display_type(property_.get("type")),
            property_.get("description", ""),
        ])
        parent.addChild(self_)
        if "properties" in property_.keys():
            json_to_tree(
                self_,
                property_.get("properties", {}),
                property_.get("required", []),
            )
        elif ("items" in property_.keys()) and is_array(property_.get("type")):
            item = QTreeWidgetItem([
                "", "E",
                display_type(property_["items"].get("type")), ""
            ])
            self_.addChild(item)
            json_to_tree(
                item,
                property_["items"].get("properties", {}),
                property_["items"].get("required", []),
            )


def is_array(type_) -> bool:
    if type_ is None:
        return False
    elif isinstance(type_, str):
        return type_ == "array"
    elif isinstance(type_, list):
        return "array" in type_
    else:
        raise ValueError(f"JSON schema is invalid: field type \"{type_}\" is invalid.")


if __name__ == '__main__':
    app = QApplication([])
    app.setStyleSheet(
        f'QWidget {{'
        f'    font-family: "Microsoft YaHei", Calibri, Ubuntu; '
        f'    font-size: 12pt;'
        f'}}'
    )
    dlg = SchemaEditor("tests/json_schema/user_profile.json")
    # dlg = JsonSchemaEditorDialog()
    dlg.exec()

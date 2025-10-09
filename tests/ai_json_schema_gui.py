import json
import os.path
from operator import attrgetter
from typing import Any, Dict, List, Optional, Union

import jsonschema
from PyQt6.QtCore import Qt, pyqtSignal, QSignalBlocker
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import *


class SchemaNodeEditor(QWidget):
    """Widget for editing individual schema node properties"""

    dataChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False  # must be before mentioned self.on_type_changed
        layout = QVBoxLayout()

        # Type selector
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        # Map supports the user's five core types plus boolean/null
        self.type_combo.addItems(
            ["object", "array", "string", "number", "integer", "boolean", "null"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        # Multiple types support
        self.multi_type_check = QCheckBox("Allow multiple types")
        self.multi_type_check.toggled.connect(self.on_multi_type_toggled)
        layout.addWidget(self.multi_type_check)

        self.type_list = QListWidget()
        self.type_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.type_list.addItems(
            ["object", "array", "string", "number", "integer", "boolean", "null"])
        self.type_list.setMaximumHeight(100)
        self.type_list.setVisible(False)
        self.type_list.itemSelectionChanged.connect(self.on_type_selection_changed)
        layout.addWidget(self.type_list)

        # Title field
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        self.title_edit.textChanged.connect(self.dataChanged.emit)
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)

        # Description field
        layout.addWidget(QLabel("Description:"))
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(120)
        self.description_edit.textChanged.connect(self.dataChanged.emit)
        layout.addWidget(self.description_edit)

        # Additional properties based on type
        self.properties_group = QGroupBox("Type-specific Properties")
        self.properties_layout = QVBoxLayout()  # create layout (no parent)
        self.properties_group.setLayout(self.properties_layout)
        layout.addWidget(self.properties_group)  # add the group box to the dialog's layout

        # Required checkbox (for properties in objects)
        self.required_check = QCheckBox("Required (for object property)")
        self.required_check.toggled.connect(self.dataChanged.emit)
        layout.addWidget(self.required_check)

        layout.addWidget(QLabel("Output information:"))
        self.error_message = QTextEdit()
        self.error_message.setEnabled(False)
        layout.addWidget(self.error_message)

        layout.addStretch()
        layout.addWidget(QLabel("Must validate schema before submitting."))
        self.setLayout(layout)

        # Initialize with default
        self.on_type_changed(self.type_combo.currentText())

    def on_type_changed(self, type_str):
        rebuilding = self._loading
        self._loading = True
        try:
            self._clear_properties_layout()
            if type_str == "string":
                self.add_string_properties()
            elif type_str in ("number", "integer"):
                self.add_number_properties()
            elif type_str == "array":
                self.add_array_properties()
            # object / boolean / null: nothing to add
        finally:
            self._loading = rebuilding
        if not self._loading:
            self.dataChanged.emit()

    def on_multi_type_toggled(self, checked):
        self.type_combo.setVisible(not checked)
        self.type_list.setVisible(checked)
        if not self._loading:
            self.dataChanged.emit()

    def on_type_selection_changed(self):
        if not self._loading:
            self.dataChanged.emit()

    def add_string_properties(self):
        # Min/max length
        min_layout = QHBoxLayout()
        min_layout.addWidget(QLabel("Min Length:"))
        self.min_length = QSpinBox()
        self.min_length.setMinimum(0)
        self.min_length.setMaximum(10 ** 9)
        self.min_length.setValue(0)
        self.min_length.valueChanged.connect(self.dataChanged.emit)
        min_layout.addWidget(self.min_length)
        self.properties_layout.addLayout(min_layout)

        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("Max Length:"))
        self.max_length = QSpinBox()
        self.max_length.setMinimum(0)
        self.max_length.setMaximum(10 ** 9)
        self.max_length.setValue(0)
        self.max_length.valueChanged.connect(self.dataChanged.emit)
        max_layout.addWidget(self.max_length)
        self.properties_layout.addLayout(max_layout)

    def add_number_properties(self):
        # Min/max value
        min_layout = QHBoxLayout()
        min_layout.addWidget(QLabel("Minimum:"))
        self.min_value = QLineEdit()
        self.min_value.setPlaceholderText("e.g., 0")
        self.min_value.textChanged.connect(self.dataChanged.emit)
        min_layout.addWidget(self.min_value)
        self.properties_layout.addLayout(min_layout)

        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("Maximum:"))
        self.max_value = QLineEdit()
        self.max_value.setPlaceholderText("e.g., 100")
        self.max_value.textChanged.connect(self.dataChanged.emit)
        max_layout.addWidget(self.max_value)
        self.properties_layout.addLayout(max_layout)

    def add_array_properties(self):
        # Min/max items
        min_layout = QHBoxLayout()
        min_layout.addWidget(QLabel("Min Items:"))
        self.min_items = QSpinBox()
        self.min_items.setMinimum(0)
        self.min_items.setMaximum(10 ** 9)
        self.min_items.setValue(0)
        self.min_items.valueChanged.connect(self.dataChanged.emit)
        min_layout.addWidget(self.min_items)
        self.properties_layout.addLayout(min_layout)

        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("Max Items:"))
        self.max_items = QSpinBox()
        self.max_items.setMinimum(0)
        self.max_items.setMaximum(10 ** 9)
        self.max_items.setValue(0)
        self.max_items.valueChanged.connect(self.dataChanged.emit)
        max_layout.addWidget(self.max_items)
        self.properties_layout.addLayout(max_layout)

    def get_node_data(self) -> Dict[str, Any]:
        """Get the current node data as a schema dict"""
        data: Dict[str, Any] = {}

        # Type
        if self.multi_type_check.isChecked():
            selected_types = [item.text() for item in self.type_list.selectedItems()]
            if selected_types:
                data["type"] = selected_types if len(selected_types) > 1 else \
                selected_types[0]
        else:
            data["type"] = self.type_combo.currentText()

        # Title and description
        if self.title_edit.text():
            data["title"] = self.title_edit.text()
        if self.description_edit.toPlainText():
            data["description"] = self.description_edit.toPlainText()

        # Type-specific properties
        current_type = self.type_combo.currentText()
        if current_type == "string":
            if hasattr(self, 'min_length') and self.min_length.value() > 0:
                data["minLength"] = self.min_length.value()
            if hasattr(self, 'max_length') and self.max_length.value() > 0:
                data["maxLength"] = self.max_length.value()
        elif current_type in ["number", "integer"]:
            if hasattr(self, 'min_value') and self.min_value.text().strip():
                try:
                    data["minimum"] = float(self.min_value.text())
                except ValueError:
                    pass
            if hasattr(self, 'max_value') and self.max_value.text().strip():
                try:
                    data["maximum"] = float(self.max_value.text())
                except ValueError:
                    pass
        elif current_type == "array":
            if hasattr(self, 'min_items') and self.min_items.value() > 0:
                data["minItems"] = self.min_items.value()
            if hasattr(self, 'max_items') and self.max_items.value() > 0:
                data["maxItems"] = self.max_items.value()

        return data

    def set_node_data(self, data: Dict[str, Any]):
        """Set the node data from a schema dict"""
        self._loading = True
        # hold the reference till the end of function, although _blockers is not used.
        with (
                QSignalBlocker(self.type_combo),
                QSignalBlocker(self.type_list),
                QSignalBlocker(self.title_edit),
                QSignalBlocker(self.description_edit),
                QSignalBlocker(self.multi_type_check),
                QSignalBlocker(self.required_check),
        ):
            # Type
            if "type" in data:
                if isinstance(data["type"], list):
                    self.multi_type_check.setChecked(True)
                    self.type_list.clearSelection()
                    for type_str in data["type"]:
                        items = self.type_list.findItems(type_str, Qt.MatchFlag.MatchExactly)
                        if items:
                            items[0].setSelected(True)
                else:
                    self.multi_type_check.setChecked(False)
                    if isinstance(data["type"], str):
                        if self.type_combo.findText(data["type"]) >= 0:
                            self.type_combo.setCurrentText(data["type"])
            # force rebuild of type widgets for the selected type, without emitting
            self.on_type_changed(self.type_combo.currentText())

            # Title and description
            self.title_edit.setText(data.get("title", ""))
            self.description_edit.setPlainText(data.get("description", ""))

            # Type-specific properties
            t = data.get("type", self.type_combo.currentText())
            if t == "string":
                if "minLength" in data and hasattr(self, 'min_length'):
                    self.min_length.setValue(int(data["minLength"]))
                if "maxLength" in data and hasattr(self, 'max_length'):
                    self.max_length.setValue(int(data["maxLength"]))
            elif t in ["number", "integer"]:
                if "minimum" in data and hasattr(self, 'min_value'):
                    self.min_value.setText(str(data["minimum"]))
                if "maximum" in data and hasattr(self, 'max_value'):
                    self.max_value.setText(str(data["maximum"]))
            elif t == "array":
                if "minItems" in data and hasattr(self, 'min_items'):
                    self.min_items.setValue(int(data["minItems"]))
                if "maxItems" in data and hasattr(self, 'max_items'):
                    self.max_items.setValue(int(data["maxItems"]))

        self._loading = False

    def _purge_layout(self, lay):
        # Recursively remove widgets, sub‑layouts, spacers
        while True:
            item = lay.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None:
                w.deleteLater()
                continue
            sub = item.layout()
            if sub is not None:
                self._purge_layout(sub)
                sub.deleteLater()
                continue
            # spacer item: nothing else to do

    def _clear_properties_layout(self):
        # 1) purge visual children
        self._purge_layout(self.properties_layout)
        # 2) drop stale attribute refs so hasattr checks don’t see old widgets
        for name in ("min_length", "max_length", "min_value", "max_value",
                     "min_items", "max_items"):
            if hasattr(self, name):
                try:
                    getattr(self, name).deleteLater()
                except Exception:
                    pass
                setattr(self, name, None)
                delattr(self, name)
        # no setLayout() here; the group box already owns properties_layout
        self.properties_group.update()


def _type_to_label(t: Union[str, List[str], None]) -> str:
    if t is None:
        return ""
    if isinstance(t, list):
        return " | ".join(t)
    return t


def _default_schema_for_type(t: str) -> Dict[str, Any]:
    if t == "object":
        return {"type": "object", "properties": {}, "required": []}
    if t == "array":
        # tuple-validation with finite items (heterogeneous allowed)
        return {"type": "array", "items": [], "additionalItems": False}
    if t == "string":
        return {"type": "string"}
    if t == "integer":
        return {"type": "integer"}
    if t == "number":
        return {"type": "number"}
    if t == "boolean":
        return {"type": "boolean"}
    if t == "null":
        return {"type": "null"}
    # Fallback
    return {"type": "string"}


def _bind_item(item: QTreeWidgetItem, node: Dict[str, Any], role: tuple):
    # role: ("root", None, None) or ("prop", prop_name, parent_obj) or
    # ("item", index, parent_array)
    item.setData(0, Qt.ItemDataRole.UserRole, {"node": node, "role": role})
    # update type/description columns
    item.setText(1, _type_to_label(node.get("type")))
    item.setText(2, node.get("description", ""))


class JsonSchemaEditorDialog(QDialog):
    def __init__(self, path=None, parent=None):
        super().__init__(parent)
        self.file_path: Optional[str] = None
        self.saved_path: Optional[str] = None
        self.schema_data: Dict[str, Any] = {
            "$schema": "http://json-schema.org/draft-07/schema#", "type": "object",
            "properties": {}, "required": []}
        self._updating = False

        # Initialize UI
        self.setWindowTitle("JSON Schema Editor")
        self.resize(1100, 720)
        layout = QVBoxLayout(self)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        # Tree widget for schema structure
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Node", "Type", "Description"])
        self.tree.itemSelectionChanged.connect(self.on_selection_changed)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.setColumnWidth(0, 300)
        splitter.addWidget(self.tree)

        # Edit menu
        add_property_btn = QAction("Add &property", self)
        add_property_btn.triggered.connect(self.add_property)
        add_property_btn.setShortcut("N")
        add_item_btn = QAction("&Append array item", self)
        add_item_btn.triggered.connect(self.add_array_item)
        add_item_btn.setShortcut("A")
        delete_btn = QAction("Delete mode", self)
        delete_btn.triggered.connect(self.delete_node)
        delete_btn.setShortcut("Del")
        # TODO: issue, list move up&down elements are deleted
        # TODO: issue, list move up&down list index out of range in move_node_up
        #     items_list[idx - 1], items_list[idx] = items_list[idx], items_list[idx - 1]
        move_up_btn = QAction("Move &up", self)
        move_up_btn.triggered.connect(self.move_node_up)
        move_up_btn.setShortcut("Ctrl+Up")
        move_down_btn = QAction("Move &down", self)
        move_down_btn.triggered.connect(self.move_node_down)
        move_down_btn.setShortcut("Ctrl+Down")
        expand_all_btn = QAction("&Expand all", self)
        expand_all_btn.triggered.connect(self.tree.expandAll)
        expand_all_btn.setShortcut("=")  # plus
        collapse_all_btn = QAction("&Collapse all", self)
        collapse_all_btn.triggered.connect(self.tree.collapseAll)
        collapse_all_btn.setShortcut("-")
        # Validate menu
        v_schema = QAction("Validate &schema", self)
        v_schema.triggered.connect(self.validate_schema)
        v_instance = QAction("Validate &instance", self)
        v_instance.triggered.connect(self.validate_instance)
        # First-level buttons
        edit_ = QMenu('&Edit', self)
        edit_.addActions([
            add_property_btn, add_item_btn, delete_btn,
            move_up_btn, move_down_btn, expand_all_btn, collapse_all_btn,
        ])
        validate = QMenu("&Validate", self)
        validate.addActions([
            v_schema,
        ])
        # Menu bar
        menu = QMenuBar(self)
        menu.addMenu(edit_)
        menu.addMenu(validate)
        layout.setMenuBar(menu)

        # Property editor
        self.property_editor = SchemaNodeEditor()
        self.property_editor.dataChanged.connect(self.update_current_node)
        splitter.addWidget(self.property_editor)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        # Dialog buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except FileNotFoundError:
                pass
            else:
                if isinstance(data, dict):
                    self.schema_data = data
                else:
                    QMessageBox.critical(
                        self, "Load Failed",
                        "Root of schema must be a JSON object."
                    )
        self.file_path = path

        # rebuild tree
        try:
            self.tree.clear()
            # root node represents the schema itself
            root_item = QTreeWidgetItem(
                ["schema", _type_to_label(self.schema_data.get("type")),
                 self.schema_data.get("description", "")])
            self.tree.addTopLevelItem(root_item)
            _bind_item(root_item, node=self.schema_data, role=("root", None, None))
            self._populate_children(root_item, self.schema_data)
            self.tree.expandItem(root_item)
            self.on_selection_changed()
        except Exception as ex:
            QMessageBox.critical(
                self, "Load Failed", f"Failed to load schema:\n{ex}")

    def _populate_children(self, parent_item: QTreeWidgetItem, node: Dict[str, Any]):
        t = node.get("type")
        if isinstance(t, list):
            # If multiple types include object or array, allow children for those
            # Prefer showing object/array children if present
            if "object" in t and "properties" in node:
                self._add_object_children(parent_item, node)
            if "array" in t and "items" in node and isinstance(node["items"], list):
                self._add_array_children(parent_item, node)
            return
        if t == "object":
            self._add_object_children(parent_item, node)
        elif t == "array":
            self._add_array_children(parent_item, node)

    def _add_object_children(self, parent_item: QTreeWidgetItem,
                             obj_schema: Dict[str, Any]):
        props = obj_schema.setdefault("properties", {})
        req = obj_schema.setdefault("required", [])
        for name, child in props.items():
            label = f"{name}{' *' if name in req else ''}"
            child_item = QTreeWidgetItem(
                [label, _type_to_label(child.get("type")), child.get("description", "")])
            parent_item.addChild(child_item)
            _bind_item(child_item, node=child, role=("prop", name, obj_schema))
            self._populate_children(child_item, child)

    def _add_array_children(self, parent_item: QTreeWidgetItem,
                            arr_schema: Dict[str, Any]):
        items_list = arr_schema.setdefault("items", [])
        if not isinstance(items_list, list):
            # Coerce to tuple validation list form for this editor
            items_list = [items_list]
            arr_schema["items"] = items_list
            arr_schema["additionalItems"] = False
        for idx, child in enumerate(items_list):
            child_item = QTreeWidgetItem(
                [f"[{idx}]", _type_to_label(child.get("type")), child.get("description", "")])
            parent_item.addChild(child_item)
            _bind_item(child_item, node=child, role=("item", idx, arr_schema))
            self._populate_children(child_item, child)

    def _current_item_ctx(self):
        items = self.tree.selectedItems()
        if not items:
            return None
        item = items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return item, data["node"], data["role"]

    def on_selection_changed(self):
        ctx = self._current_item_ctx()
        self._updating = True
        try:
            if not ctx:
                self.property_editor.setEnabled(False)
                return
            self.property_editor.setEnabled(True)
            item, node, role = ctx
            # Load node data into editor
            with QSignalBlocker(self.property_editor):
                self.property_editor.set_node_data(node)
            # Required checkbox only meaningful for object properties
            if role[0] == "prop":
                name = role[1]
                parent_obj = role[2]
                req = parent_obj.setdefault("required", [])
                self.property_editor.required_check.setEnabled(True)
                self.property_editor.required_check.setChecked(name in req)
            else:
                self.property_editor.required_check.setEnabled(False)
                self.property_editor.required_check.setChecked(False)
        finally:
            self._updating = False

    def update_current_node(self):
        if self._updating:
            return
        ctx = self._current_item_ctx()
        if not ctx:
            return
        item, node, role = ctx

        # Merge editor data into node while preserving children when type unchanged
        new_data = self.property_editor.get_node_data()

        # Handle required toggle
        if role[0] == "prop":
            name = role[1]
            parent_obj = role[2]
            req = parent_obj.setdefault("required", [])
            if self.property_editor.required_check.isChecked():
                if name not in req:
                    req.append(name)
            else:
                if name in req:
                    req.remove(name)
            # Update label with * for required
            item.setText(0, f"{name}{' *' if name in req else ''}")

        # Detect type change to manage children keys
        old_type = node.get("type")
        new_type = new_data.get("type", old_type)

        # Replace scalar attributes
        # Keep properties/items if staying same structured type
        keep_props = (old_type == "object" and new_type == "object") or (
                    old_type == ["object"] and new_type == "object")
        keep_items = (old_type == "array" and new_type == "array") or (
                    old_type == ["array"] and new_type == "array")

        # Remove structural keys when needed
        if not keep_props and "properties" in node:
            node.pop("properties", None)
            node.pop("required", None)
        if not keep_items and "items" in node:
            node.pop("items", None)
            node.pop("additionalItems", None)

        # Overwrite scalar keys first
        # Clear existing simple keys
        for k in list(node.keys()):
            if k in ("properties", "items", "required", "additionalItems"):
                continue
            if k.startswith("$"):
                continue
            node.pop(k, None)
        # Apply new scalar data
        for k, v in new_data.items():
            node[k] = v

        # Ensure structural defaults for object/array
        t = node.get("type")
        t_list = t if isinstance(t, list) else [t]
        if "object" in t_list:
            node.setdefault("properties", {})
            node.setdefault("required", [])
        if "array" in t_list:
            node.setdefault("items", [])
            if not isinstance(node["items"], list):
                node["items"] = [node["items"]]
            node.setdefault("additionalItems", False)

        # Update tree row
        item.setText(1, _type_to_label(node.get("type")))
        item.setText(2, node.get("description", ""))

        # Rebuild children for this item to reflect structural changes
        self._refresh_item_children(item, node)

    def _refresh_item_children(self, item: QTreeWidgetItem, node: Dict[str, Any]):
        # Remove all children and repopulate
        while item.childCount():
            item.removeChild(item.child(0))
        # Re-bind item metadata (type/desc columns already updated)
        role = item.data(0, Qt.ItemDataRole.UserRole)["role"]
        _bind_item(item, node=node, role=role)
        self._populate_children(item, node)
        self.tree.expandItem(item)

    def add_property(self):
        ctx = self._current_item_ctx()
        if not ctx:
            QMessageBox.warning(self, "Add Property",
                                "Please select the parent node too add property.")
            return
        item, node, role = ctx
        # Target object node
        target_item, target_node = item, node
        print(target_node)
        if node.get("type") != "object":
            # If a child selected, allow adding to nearest ancestor object
            parent = item.parent()
            while parent:
                pdata = parent.data(0, Qt.ItemDataRole.UserRole)
                if pdata and pdata["node"].get("type") == "object":
                    target_item = parent
                    target_node = pdata["node"]
                    break
                parent = parent.parent()
            else:
                QMessageBox.warning(self, "Add Property",
                                    "Select an object node (dict) to add a property.")
                return
        name, ok = QInputDialog.getText(self, "Add Property", "Property name:")
        if not ok or not name:
            return
        props = target_node.setdefault("properties", {})
        if name in props:
            QMessageBox.warning(self, "Add Property",
                                f'Property "{name}" already exists.')
            return
        child_schema = _default_schema_for_type("string")
        props[name] = child_schema  # This line correctly modifies the data model
        target_node.setdefault("required", [])
        self._refresh_item_children(target_item, target_node)

        # Add to tree
        # child_item = QTreeWidgetItem(
        #     [f"{name}", _type_to_label(child_schema.get("type")), ""])
        # target_item.addChild(child_item)
        # _bind_item(child_item, node=child_schema, role=("prop", name, target_node))
        # self.tree.expandItem(target_item)
        # self.tree.setCurrentItem(child_item)

    def add_array_item(self):
        ctx = self._current_item_ctx()
        if not ctx:
            QMessageBox.warning(self, "Add Property",
                                "Please select the array to add item.")
            return
        item, node, role = ctx
        # Target array node
        target_item, target_node = item, node
        if node.get("type") != "array":
            # ascend to nearest array ancestor
            parent = item.parent()
            while parent:
                pdata = parent.data(0, Qt.ItemDataRole.UserRole)
                if pdata and pdata["node"].get("type") == "array":
                    target_item = parent
                    target_node = pdata["node"]
                    break
                parent = parent.parent()
            else:
                QMessageBox.warning(self, "Add Array Item",
                                    "Select an array (list) node to add an item.")
                return
        target_node.setdefault("additionalItems", False)
        items_list = target_node.setdefault("items", [])
        child_schema = _default_schema_for_type("string")
        items_list.append(child_schema)
        self._refresh_item_children(target_item, target_node)

        # Add to tree
        idx = target_item.childCount()
        child_item = QTreeWidgetItem(
            [f"[{idx}]", _type_to_label(child_schema.get("type")), ""])
        target_item.addChild(child_item)
        _bind_item(child_item, node=child_schema, role=("item", idx, target_node))
        self.tree.expandItem(target_item)
        self.tree.setCurrentItem(child_item)

    def delete_node(self):
        ctx = self._current_item_ctx()
        if not ctx:
            return
        item, node, role = ctx
        if role[0] == "root":
            QMessageBox.warning(
                self, "Delete", "Cannot delete the root schema node.")
            return
        parent_item = item.parent()
        if not parent_item:
            return
        if role[0] == "prop":
            name = role[1]
            obj_schema = role[2]
            # remove from properties and required
            obj_schema.get("properties", {}).pop(name, None)
            if "required" in obj_schema and name in obj_schema["required"]:
                obj_schema["required"].remove(name)
            # remove tree item
            parent_item.removeChild(item)
        elif role[0] == "item":
            idx = role[1]
            arr_schema = role[2]
            items_list = arr_schema.get("items", [])
            if isinstance(items_list, list) and 0 <= idx < len(items_list):
                items_list.pop(idx)
            # remove tree item and reindex siblings
            parent_item.removeChild(item)
            self._reindex_array_children(parent_item, arr_schema)
        # select parent afterward
        self.tree.setCurrentItem(parent_item)

    def _reindex_array_children(self, parent_item: QTreeWidgetItem,
                                arr_schema: Dict[str, Any]):
        # Rebuild children labels and roles to keep indices in sync
        while parent_item.childCount():
            parent_item.removeChild(parent_item.child(0))
        self._add_array_children(parent_item, arr_schema)

    def move_node_up(self):
        ctx = self._current_item_ctx()
        if not ctx:
            return
        item, node, role = ctx
        parent_item = item.parent()
        if not parent_item:
            return
        if role[0] == "item":
            arr_schema = role[2]
            items_list = arr_schema.get("items", [])
            idx = role[1]
            if idx <= 0 or not isinstance(items_list, list):
                return
            # swap
            items_list[idx - 1], items_list[idx] = items_list[idx], items_list[idx - 1]
            # refresh children to reindex
            self._reindex_array_children(parent_item, arr_schema)
            # select moved item (now at idx-1)
            self.tree.setCurrentItem(parent_item.child(idx - 1))
        elif role[0] == "prop":
            # reorder object properties for visual order persistence
            name = role[1]
            obj_schema = role[2]
            props = obj_schema.get("properties", {})
            keys = list(props.keys())
            i = keys.index(name)
            if i <= 0:
                return
            keys[i - 1], keys[i] = keys[i], keys[i - 1]
            # rebuild dict with new insertion order
            new_props = {k: props[k] for k in keys}
            obj_schema["properties"] = new_props
            # refresh subtree
            self._refresh_item_children(parent_item, obj_schema)
            # select moved property
            self.tree.setCurrentItem(parent_item.child(i - 1))

    def move_node_down(self):
        ctx = self._current_item_ctx()
        if not ctx:
            return
        item, node, role = ctx
        parent_item = item.parent()
        if not parent_item:
            return
        if role[0] == "item":
            arr_schema = role[2]
            items_list = arr_schema.get("items", [])
            idx = role[1]
            if not isinstance(items_list, list) or idx >= len(items_list) - 1:
                return
            # swap
            items_list[idx + 1], items_list[idx] = items_list[idx], items_list[idx + 1]
            # refresh children
            self._reindex_array_children(parent_item, arr_schema)
            # select moved item (now at idx+1)
            self.tree.setCurrentItem(parent_item.child(idx + 1))
        elif role[0] == "prop":
            name = role[1]
            obj_schema = role[2]
            props = obj_schema.get("properties", {})
            keys = list(props.keys())
            i = keys.index(name)
            if i >= len(keys) - 1:
                return
            keys[i + 1], keys[i] = keys[i], keys[i + 1]
            new_props = {k: props[k] for k in keys}
            obj_schema["properties"] = new_props
            self._refresh_item_children(parent_item, obj_schema)
            self.tree.setCurrentItem(parent_item.child(i + 1))

    def show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        node = data["node"]
        role = data["role"]
        menu = QMenu(self)

        add_prop_act = QAction("Add Property", self)
        add_prop_act.triggered.connect(self.add_property)
        add_item_act = QAction("Add Array Item", self)
        add_item_act.triggered.connect(self.add_array_item)
        del_act = QAction("Delete", self)
        del_act.triggered.connect(self.delete_node)
        up_act = QAction("Move Up", self)
        up_act.triggered.connect(self.move_node_up)
        down_act = QAction("Move Down", self)
        down_act.triggered.connect(self.move_node_down)
        expand_act = QAction("Expand", self)
        expand_act.triggered.connect(lambda: self.tree.expandItem(item))
        collapse_act = QAction("Collapse", self)
        collapse_act.triggered.connect(lambda: self.tree.collapseItem(item))

        t = node.get("type")
        t_list = t if isinstance(t, list) else [t]
        if "object" in t_list:
            menu.addAction(add_prop_act)
        if "array" in t_list:
            menu.addAction(add_item_act)
        if role[0] != "root":
            menu.addAction(del_act)
            if role[0] in ("item", "prop"):
                menu.addSeparator()
                menu.addAction(up_act)
                menu.addAction(down_act)
        menu.addSeparator()
        menu.addAction(expand_act)
        menu.addAction(collapse_act)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def validate_schema(self):
        self.property_editor.error_message.clear()
        try:
            jsonschema.Draft7Validator.check_schema(self.schema_data)
        except jsonschema.exceptions.SchemaError as e:
            # Format like user's snippet (schema-level path)
            path_str = "schema"
            for p in e.path:
                if isinstance(p, str):
                    p_ = "\"" + p + "\""
                else:
                    p_ = str(p)
                path_str += "[" + p_ + "]"
            self.property_editor.error_message.append(f"At {path_str}, {e.message}.\n")
            QMessageBox.critical(
                self, "Schema Invalid", "See output information for details.")
            return False
        else:
            self.property_editor.error_message.append("Schema structure is valid.")
            return True

    def validate_instance(self):
        inst_path, _ = QFileDialog.getOpenFileName(
            self, "Open JSON instance", "",
            "JSON Files (*.json);;All Files (*)")
        self.property_editor.error_message.clear()
        if inst_path:
            try:
                with open(inst_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                validator = jsonschema.Draft7Validator(self.schema_data)
                errors = sorted(validator.iter_errors(data), key=attrgetter('path'))
                if errors:
                    for e in errors:
                        path_str = "$"
                        for p in e.path:
                            if isinstance(p, str):
                                p_ = "\"" + p + "\""
                            else:
                                p_ = str(p)
                            path_str += "[" + p_ + "]"
                        self.property_editor.error_message.append(
                            f"At {path_str}, {e.message}.\n")
                    QMessageBox.warning(
                        self, "Instance Errors",
                        f"Found {len(errors)} validation error(s). See output "
                        f"information for details."
                    )
            except Exception as ex:
                QMessageBox.critical(
                    self, "Instance Validation Failed",
                    f"Failed to validate instance:\n{ex}"
                )

    def on_accept(self):
        # Validate schema structure first
        if not self.validate_schema():
            # Keep dialog open to fix
            return
        # Save schema to file
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Schema", "",
            "JSON Schema (*.json);;All Files (*)"
        )
        if not save_path:
            # user canceled save; keep dialog open
            return
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.schema_data, f, indent=4, ensure_ascii=False)
            self.saved_path = save_path
            QMessageBox.information(
                self, "Saved", f"Schema saved to:\n{save_path}")
            self.accept()
        except Exception as ex:
            QMessageBox.critical(
                self, "Save Failed", f"Failed to save schema:\n{ex}")

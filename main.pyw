import os
import sys
from datetime import datetime
from functools import partial
from operator import attrgetter

import openai
from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QImage
from PyQt6.QtWidgets import *

from config import Config
from json_schema_gui import SchemaEditor

not_initialized_message = \
"""Fail to connect to large language model. Possible reasons: \n
(1) OpenAI API key is invalid. \n 
"""
if hasattr(sys, '_MEIPASS'):  # pyinstaller
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.abspath(".")
schemas_dir = os.path.join(base_dir, "raw", "json_schema")
os.makedirs(schemas_dir, exist_ok=True)


class OpenAIConfigDialog(QDialog):
    def __init__(self, parent=None, existed_api_key=""):
        super().__init__(parent)
        self.setWindowTitle('Config OpenAI')

        screen_size = self.screen().size()
        window_width = round(0.25 * screen_size.width())
        self.setMinimumWidth(window_width)

        # Main layout
        layout = QVBoxLayout(self)
        # API Key Input
        api_key_label = QLabel('OpenAI API Key:', self)
        layout.addWidget(api_key_label)
        self.api_key_input = QPlainTextEdit(self)
        self.api_key_input.setPlainText(existed_api_key)
        layout.addWidget(self.api_key_input)
        # Check Button
        check_button = QPushButton('Validate', self)
        check_button.clicked.connect(self.check_api_key)
        check_button_row = QHBoxLayout()
        check_button_row.addStretch()
        check_button_row.addWidget(check_button)  # Center
        check_button_row.addStretch()
        layout.addLayout(check_button_row)
        # Model Selection
        model_label = QLabel('OpenAI model:', self)
        layout.addWidget(model_label)
        self.model_combo_box = QComboBox(self)
        layout.addWidget(self.model_combo_box)
        # OK and Cancel Buttons
        self.confirmation = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.confirmation.accepted.connect(self.accept)
        self.confirmation.rejected.connect(self.reject)
        self.confirmation.setEnabled(False)  # disabled before validated
        layout.addWidget(self.confirmation)
        self.setLayout(layout)

        self.dialog_warning = QMessageBox()
        self.dialog_warning.setIcon(QMessageBox.Icon.Warning)
        self.dialog_warning.setWindowTitle("Warning")
        self.dialog_warning.setStandardButtons(QMessageBox.StandardButton.Ok)

    def check_api_key(self):
        api_key = self.api_key_input.toPlainText().strip()
        try:
            client = openai.OpenAI(api_key=api_key)
            model_list = client.models.list().data
        except openai.APIConnectionError:
            self.dialog_warning.setText("Network error: fail to contact OpenAI server.")
            self.dialog_warning.exec()
            self.confirmation.setEnabled(False)
            return
        except openai.AuthenticationError:
            self.dialog_warning.setText("Authentication error: invalid API key.")
            self.dialog_warning.exec()
            self.confirmation.setEnabled(False)
            return
        if not model_list:
            self.dialog_warning.setText("No available model.")
            self.dialog_warning.exec()
            self.confirmation.setEnabled(False)
            return
        self.model_combo_box.clear()
        model_list = sorted(
            model_list, key=attrgetter('created'), reverse=True)
        for model in model_list:
            id_ = model.id
            created_date = datetime.fromtimestamp(model.created).date()
            display_name = f"{id_} [{created_date}]"
            self.model_combo_box.addItem(display_name, userData=id_)
        self.confirmation.setEnabled(True)



def pixmap_to_pillow_image(pixmap):
    q_image = pixmap.toImage()
    q_image = q_image.convertToFormat(QImage.Format.Format_RGBA8888)
    width = q_image.width()
    height = q_image.height()
    if q_image.bits() is None:
        return None
    buffer = q_image.bits().asarray(q_image.sizeInBytes())
    pillow_image = Image.frombytes("RGBA", (width, height),
                                   buffer, "raw", "BGRA")
    return pillow_image


class MyWindow(QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__(flags=Qt.WindowType.Window)

        # Logical, e.g. 2560*1440 150% -> 1707*960
        screen_size = self.screen().size()
        window_height =  round(0.6 * screen_size.height())
        window_width = round(1.6 * window_height)

        self.resize(window_width, window_height)
        self.setWindowTitle('GUI for OpenAI OCR')
        self.center()

        self.busy = False
        self.config = Config()
        self.json_schema_path = ""

        self.create_menu_bar()
        self.source_displayed = QLabel(self)
        self.openai_model_name = QLabel(self)
        self.openai_model_name.setText(self.config["openai_model"])
        self.json_schema_path_displayed = QLabel(self)
        self.pbar = QProgressBar(self)
        self.message = QTextEdit(self)

        main_part = QWidget()
        main_layout = QFormLayout(main_part)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        main_layout.addRow('Source:', self.source_displayed)
        main_layout.addRow('Model:', self.openai_model_name)
        main_layout.addRow("Template:", self.json_schema_path_displayed)
        main_layout.addRow('Progress:', self.pbar)
        main_layout.addRow('Message:', self.message)
        self.setCentralWidget(main_part)

        self.status = QStatusBar(self)
        self.status.showMessage('Ready.', 0)
        self.setStatusBar(self.status)

    def create_separator(self):
        sep = QAction(self)
        sep.setSeparator(True)
        return sep

    def create_menu_bar(self):
        # Settings menu
        config_openai = QAction('&Config model', self)
        config_openai.triggered.connect(self.config_openai)
        json_schema_folder = QAction("Schema: &Open default folder", self)
        json_schema_folder.triggered.connect(partial(os.startfile, schemas_dir))
        json_schema_new = QAction("Schema: &Create and select", self)
        json_schema_new.triggered.connect(self.create_json_schema)
        json_schema_ = QAction("Schema: &Edit and select", self)
        json_schema_load = QAction("Schema: &Select", self)
        close = QAction('&Exit', self)
        close.triggered.connect(self.close)
        close.setShortcut('Ctrl+W')
        # Recognize menu
        reco_folder = QAction('From &folder', self)
        reco_folder.triggered.connect(self.ocr_batch)
        reco_file = QAction('From &single image', self)
        reco_file.triggered.connect(self.ocr_single)
        reco_clipboard = QAction('From &clipboard', self)
        reco_clipboard.triggered.connect(self.ocr_clipboard)
        reco_clipboard.setShortcut('Ctrl+Shift+V')
        # First-level buttons
        settings = QMenu('&Settings', self)
        settings.addActions([
            config_openai, self.create_separator(),
            json_schema_folder, json_schema_, json_schema_new, json_schema_load,
            self.create_separator(), close
        ])
        recognize = QMenu('&Recognize', self)
        recognize.addActions([reco_folder, reco_file, reco_clipboard])
        # Menu bar
        menu = QMenuBar(self)
        menu.addMenu(settings)
        menu.addMenu(recognize)
        self.setMenuBar(menu)

    @staticmethod
    def status_check_decorator(action_name, *args, **kwargs):
        def status_check_decorator_1(pyfunc):
            def status_check(self):
                if not self.busy:
                    self.busy = True
                    self.status.showMessage(f'{action_name} ...', 0)
                    self.pbar.setValue(0)
                    self.message.clear()
                    pyfunc(self, *args, **kwargs)
            return status_check

        return status_check_decorator_1

    def delayed_thread_finished(self):
        self.pbar.setValue(100)
        self.status.showMessage('Ready.', 0)
        self.busy = False

    @status_check_decorator(action_name="Set JSON schema")
    def set_json_schema(self):
        pass

    @status_check_decorator(action_name='Recognize folder')
    def ocr_batch(self):
        if self.ocr_engine is None:
            self.message.append(not_initialized_message)
            self.delayed_thread_finished()
            return
        fp = QFileDialog.getExistingDirectory(
            caption='Images to recognize', options=QFileDialog.Option.ShowDirsOnly)
        if not (fp and os.path.isdir(fp)):
            self.message.append('The source to recognize does not exist.')
            self.delayed_thread_finished()
            return
        dist = QFileDialog.getExistingDirectory(
            caption='Export to', options=QFileDialog.Option.ShowDirsOnly)
        os.makedirs(dist, exist_ok=True)
        self.source_displayed.setText(fp)
        self.operator = FolderOCR(fp, dist, self.ocr_engine)
        self.operator.start()
        self.operator.progress.connect(self.pbar.setValue)
        self.operator.gui_message.connect(self.message.append)
        self.operator.done.connect(self.delayed_thread_finished)

    @status_check_decorator(action_name='Recognize from clipboard')
    def ocr_clipboard(self):
        if self.ocr_engine is None:
            self.message.append(not_initialized_message)
            self.delayed_thread_finished()
            return
        clipboard = QApplication.clipboard()
        pixmap = clipboard.pixmap()
        image = pixmap_to_pillow_image(pixmap)
        if not image:
            self.message.append('There is no picture in the clipboard.')
            self.delayed_thread_finished()
            return
        self.source_displayed.setText('Clipboard')
        self.operator = ClipboardOCR(image, self.ocr_engine)
        self.operator.start()
        self.operator.progress.connect(self.pbar.setValue)
        self.operator.gui_message.connect(self.message.append)
        self.operator.done.connect(self.delayed_thread_finished)

    @status_check_decorator(action_name='OCR for single image')
    def ocr_single(self):
        if self.ocr_engine is None:
            self.message.append(not_initialized_message)
            self.delayed_thread_finished()
            return
        fp, _ = QFileDialog.getOpenFileName(filter='Images (*.png *.jpeg *.jpg)')
        if not (fp and os.path.isfile(fp)):
            self.message.append('The image to recognize does not exist.')
            self.delayed_thread_finished()
            return
        self.source_displayed.setText(fp)
        self.operator = FileOCR(fp, self.ocr_engine)
        self.operator.start()
        self.operator.progress.connect(self.pbar.setValue)
        self.operator.gui_message.connect(self.message.append)
        self.operator.done.connect(self.delayed_thread_finished)

    def center(self):
        fg = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        fg.moveCenter(cp)
        self.move(fg.topLeft())


    @status_check_decorator(action_name='Config OpenAI model')
    def config_openai(self):
        dialog_config_openai = OpenAIConfigDialog(
            parent=self, existed_api_key=self.config["openai_api_key"])
        action = dialog_config_openai.exec()
        if action != QDialog.DialogCode.Accepted:
            self.delayed_thread_finished()
            return
        config_new = {
            "openai_api_key": dialog_config_openai.api_key_input.toPlainText().strip(),
            "openai_model": dialog_config_openai.model_combo_box.currentData(),
        }
        self.config.update(config_new)
        self.config.dump()
        self.openai_model_name.setText(config_new["openai_model"])
        self.delayed_thread_finished()
        return

    @status_check_decorator(action_name='Create new schema')
    def create_json_schema(self):
        dialog = SchemaEditor()
        if dialog.initial_prevented:
            return
        action = dialog.exec()
        if action != QDialog.DialogCode.Accepted:
            self.delayed_thread_finished()
            return


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(
        f'QWidget {{'
        f'    font-family: "Microsoft YaHei", Calibri, Ubuntu; '
        f'    font-size: 12pt;'
        f'}}'
    )
    myw = MyWindow()
    myw.show()
    sys.exit(app.exec())

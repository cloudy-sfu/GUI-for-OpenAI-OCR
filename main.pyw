import base64
import json
import os
import sys
from functools import partial

from PyQt6.QtCore import Qt, QBuffer, QByteArray, QIODevice
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import *

from config import Config
from json_schema_dialog import SchemaEditor
from open_ai_config_dialog import OpenAIConfigDialog
from ocr import OCR

not_initialized_message = \
"""Fail to connect to large language model. Possible reasons: \n
(1) OpenAI API key is invalid. \n 
"""


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
        # Hold reference to prevent OCR engine as local variable being destroyed
        self.operator = None

        self.create_menu_bar()
        self.source = QLabel(self)
        self.openai_model_name = QLabel(self)
        self.openai_model_name.setText(self.config["openai_model"])
        self.json_schema_path = QLabel(self)
        self.pbar = QProgressBar(self)
        self.ocr_result = QTextEdit(self)

        main_part = QWidget()
        main_layout = QFormLayout(main_part)
        main_layout.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        main_layout.addRow('Source:', self.source)
        main_layout.addRow('Model:', self.openai_model_name)
        main_layout.addRow("Schema:", self.json_schema_path)
        main_layout.addRow('Progress:', self.pbar)
        main_layout.addRow('Result:', self.ocr_result)
        self.setCentralWidget(main_part)

        self.status = QStatusBar(self)
        self.status.showMessage('Ready.', 0)
        self.setStatusBar(self.status)

    def create_menu_bar(self):
        # Settings menu
        config_openai = QAction('Config OpenAI &model', self)
        config_openai.triggered.connect(self.config_openai)
        json_schema_existed = QAction("Config output schema: open &existed", self)
        json_schema_existed.triggered.connect(self.existed_json_schema)
        json_schema_new = QAction("Config output schema: create &new", self)
        json_schema_new.triggered.connect(self.new_json_schema)
        max_retries = QAction("Config max &retries", self)
        max_retries.triggered.connect(self.set_max_retries)

        # Recognize menu
        reco_folder = QAction('From &folder', self)
        reco_folder.triggered.connect(self.ocr_batch)
        reco_file = QAction('From &single image', self)
        reco_file.triggered.connect(self.ocr_single)
        reco_clipboard = QAction('From &clipboard', self)
        reco_clipboard.triggered.connect(self.ocr_clipboard)
        reco_clipboard.setShortcut('Ctrl+Shift+V')

        # First-level buttons
        settings = QMenu('&Config', self)
        settings.addActions([
            # disabled: max_retries
            config_openai, json_schema_existed, json_schema_new,
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
                    self.ocr_result.clear()
                    pyfunc(self, *args, **kwargs)
            return status_check

        return status_check_decorator_1

    def delayed_thread_finished(self):
        self.pbar.setValue(100)
        self.status.showMessage('Ready.', 0)
        self.busy = False

    @status_check_decorator(action_name='Recognize folder')
    def ocr_batch(self):
        if self.ocr_engine is None:
            self.silent_message("warn", "OCR Engine", not_initialized_message)
            self.delayed_thread_finished()
            return
        src = QFileDialog.getExistingDirectory(
            caption='Images to recognize', options=QFileDialog.Option.ShowDirsOnly)
        if not (src and os.path.isdir(src)):
            self.icon_message(
                "OCR Engine", "The source to recognize does not exist.",
                QStyle.StandardPixmap.SP_DirIcon,
            )
            self.delayed_thread_finished()
            return
        dist = QFileDialog.getExistingDirectory(
            caption='Export to', options=QFileDialog.Option.ShowDirsOnly)
        os.makedirs(dist, exist_ok=True)
        self.source.setText(src)
        self.operator = FolderOCR(src, dist, self.ocr_engine)
        self.operator.start()
        self.operator.progress.connect(self.pbar.setValue)
        self.operator.gui_message.connect(
            partial(self.silent_message, "warn", "OCR Engine"))
        self.operator.done.connect(self.delayed_thread_finished)

    @status_check_decorator(action_name='Recognize from clipboard')
    def ocr_clipboard(self):
        self.source.setText("Clipboard")
        pixmap = QApplication.clipboard().pixmap()
        if pixmap.isNull():
            self.silent_message(
                "warn", "OCR Engine", "No picture in the clipboard.")
            self.delayed_thread_finished()
            return
        try:
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            pixmap.save(buffer, "PNG")
            base64_image = base64.b64encode(byte_array.data()).decode("utf-8")
            data_url = f"data:image/png;base64,{base64_image}"
        except Exception as e:
            self.silent_message(
                "warn", "Clipboard",
                "Fail to convert image in clipboard to OpenAI required format. "
                f"Detail: {e}"
            )
            self.delayed_thread_finished()
            return
        try:
            with open(self.json_schema_path.text(), "r") as f:
                schema = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.silent_message(
                "warn", "OCR Engine", "Output schema is unset or invalid.")
            self.delayed_thread_finished()
            return
        self.operator = OCR(
            api_key=self.config["openai_api_key"],
            model_name=self.config["openai_model"],
            json_schema=schema,
            data_url=data_url,
        )
        self.operator.start()
        self.operator.error_message.connect(
            partial(self.silent_message, "warn", "OCR Engine"))
        self.operator.result.connect(self.ocr_result.setText)
        self.operator.done.connect(self.delayed_thread_finished)

    @status_check_decorator(action_name='OCR for single image')
    def ocr_single(self):
        if self.ocr_engine is None:
            self.silent_message("warn", "OCR Engine", not_initialized_message)
            self.delayed_thread_finished()
            return
        fp, _ = QFileDialog.getOpenFileName(filter='Images (*.png *.jpeg *.jpg)')
        if not (fp and os.path.isfile(fp)):
            self.silent_message(
                "warn", "OCR Engine",
                "The image to recognize does not exist."
            )
            self.delayed_thread_finished()
            return
        self.source.setText(fp)
        self.operator = FileOCR(fp, self.ocr_engine)
        self.operator.start()
        self.operator.progress.connect(self.pbar.setValue)
        self.operator.gui_message.connect(
            partial(self.silent_message, "warn", "OCR Engine"))
        self.operator.done.connect(self.delayed_thread_finished)

    def center(self):
        frame = self.frameGeometry()
        center = self.screen().availableGeometry().center()
        frame.moveCenter(center)
        self.move(frame.topLeft())

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

    @status_check_decorator(action_name='Config output schema')
    def existed_json_schema(self):
        fp, _ = QFileDialog.getOpenFileName(filter='Output schema (*.json)')
        dialog = SchemaEditor(fp)
        if not dialog.initial_valid:
            self.delayed_thread_finished()
            return
        action = dialog.exec()
        if action != QDialog.DialogCode.Accepted:
            self.delayed_thread_finished()
            return
        self.json_schema_path.setText(dialog.filepath)
        self.delayed_thread_finished()

    @status_check_decorator(action_name='Config output schema')
    def new_json_schema(self):
        dialog = SchemaEditor()
        if not dialog.initial_valid:
            self.delayed_thread_finished()
            return
        action = dialog.exec()
        if action != QDialog.DialogCode.Accepted:
            self.delayed_thread_finished()
            return
        self.json_schema_path.setText(dialog.filepath)
        self.delayed_thread_finished()

    def set_max_retries(self):
        max_retries, ok = QInputDialog.getInt(
            self,
            "Config max retries",
            "When output structured text from the \n"
            "OpenAI model does not fit the predefined schema, \n"
            "how many times to retry?",
            value=self.config["max_retries"],
            min=1,
            max=10,
        )
        if not ok:
            return
        self.config.update({"max_retries": max_retries})

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

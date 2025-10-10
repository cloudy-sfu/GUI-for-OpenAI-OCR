from datetime import datetime
from operator import attrgetter

import openai
from PyQt6.QtWidgets import *


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

    def check_api_key(self):
        api_key = self.api_key_input.toPlainText().strip()
        try:
            client = openai.OpenAI(api_key=api_key)
            model_list = client.models.list().data
        except openai.APIConnectionError:
            self.silent_message(
                "warn", "Network",
                "Fail to contact OpenAI server."
            )
            self.confirmation.setEnabled(False)
            return
        except openai.AuthenticationError:
            self.silent_message(
                "warn", "Authentication", "Invalid API key."
            )
            self.confirmation.setEnabled(False)
            return
        if not model_list:
            self.silent_message(
                "warn", "Authentication", "No available model."
            )
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

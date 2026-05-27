from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
)

from ui.browser_tab import BrowserData


class BrowserModelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Browser Model")
        self.setFixedSize(420, 240)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        layout = QVBoxLayout(self)
        label = QLabel("Create a new model-specific browser tab")
        label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")
        self.model_options = BrowserData.BROWSER_MODEL_CHOICES
        self.model_input = QComboBox()
        self.model_input.addItems([entry["model"] for entry in self.model_options])
        self.model_input.setEditable(False)
        self.role_input = QComboBox()
        self.role_input.addItems(BrowserData.get_role_names())
        self.role_input.setEditable(False)

        form.addRow("Name", self.name_input)
        form.addRow("Model", self.model_input)
        form.addRow("Role", self.role_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.selected_name = None
        self.selected_model = None
        self.selected_role_name = None

    def _accept(self):
        self.selected_name = self.name_input.text().strip()
        self.selected_model = self.model_input.currentText().strip()
        self.selected_role_name = self.role_input.currentText().strip()
        self.accept()

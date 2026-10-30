from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class ProbeLabelsDialog(QDialog):
    def __init__(self, probe_labels, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure Probe Labels")
        self.resize(680, 360)

        self._table = QTableWidget(len(probe_labels), 2)
        self._table.setHorizontalHeaderLabels(("Probe ID", "Friendly label"))
        self._table.horizontalHeader().setStretchLastSection(True)
        for row, (address, label) in enumerate(probe_labels):
            address_item = QTableWidgetItem(address)
            address_item.setFlags(address_item.flags() & ~address_item.flags().ItemIsEditable)
            self._table.setItem(row, 0, address_item)
            self._table.setItem(row, 1, QTableWidgetItem(label))

        self._hint = QLabel(
            "Labels are saved by probe ID and apply to future sessions. "
            "Discovered probes appear here while scanning."
        )
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._hint)
        layout.addWidget(self._table)
        layout.addWidget(buttons)

    def labels(self) -> tuple[tuple[str, str], ...]:
        result = []
        for row in range(self._table.rowCount()):
            address = self._table.item(row, 0).text().strip()
            label_item = self._table.item(row, 1)
            label = label_item.text().strip() if label_item else ""
            if address and label:
                result.append((address, label))
        return tuple(result)

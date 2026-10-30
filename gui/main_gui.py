import sys

from PySide6.QtWidgets import QApplication

from gui.acquisition_window import AcquisitionWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = AcquisitionWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

from PySide6.QtWidgets import QMainWindow

from gui.app_state import AppState
from gui.acquisition_controller import AcquisitionController
from gui.acquisition_tab import AcquisitionTab


class AcquisitionWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Weber Smoker Data Acquisition")
        self.resize(1000, 650)
        self.app_state = AppState()
        self.acquisition_controller = AcquisitionController(
            app_state=self.app_state,
            parent=self,
        )
        self.setCentralWidget(
            AcquisitionTab(
                app_state=self.app_state,
                acquisition_controller=self.acquisition_controller,
            )
        )

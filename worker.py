from collections.abc import Callable

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget


class OperationWorker(QThread):
    links_changed = pyqtSignal(str)
    tally_changed = pyqtSignal(str)
    output_changed = pyqtSignal(str)
    operation_finished = pyqtSignal(bool, bool)
    failed = pyqtSignal(str)

    def __init__(
        self,
        operation: Callable[[], tuple[str | None, str | None, bool]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._operation = operation

    def run(self) -> None:
        try:
            links_html, tally_html, show_viewer = self._operation()
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        stopped = False
        if links_html is not None:
            self.links_changed.emit(links_html)
        if tally_html is not None:
            stopped = (
                "Operation cancelled." in tally_html
                or "stopped by user" in tally_html
            )
            self.tally_changed.emit(tally_html)
        self.operation_finished.emit(stopped, show_viewer)

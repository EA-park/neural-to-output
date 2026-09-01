"""Desktop setup UI for the n2o pipeline (signal -> decoder -> command -> robot).

The UI-equivalent of `demos/quickstart.py` -- see `ROADMAP.md`'s "quickstart를 UI로"
entry. Picks the same kind of components `quickstart.py` wires by hand, then runs
`N2O.run()` in a background thread so the window stays responsive.

Robot parts are a dynamic list (파츠/Parts group) instead of fixed arm/hand rows --
"+ 파츠 추가" adds a row, each row picks a kind (arm/hand/leg) from a dropdown and can
be removed again. A row's "설정" button only enables once Controller is
"motor_driver" -- port only matters against real hardware, not simulation -- and
opens a small dialog to set its port. Only "arm"/"hand" are actually backed by an
`n2o.robot` class today (`SO101Arm`/`AmazingHand`) -- "leg" has no `n2o.robot.leg`
package yet, so running with one selected shows a clear "not supported" message
instead of silently doing nothing (same pattern as the Unity simulation backend
guard below).

"손을 팔 말단에 연결" (파츠 group) only enables once an arm row and a hand row both
exist with Controller set to "simulation" -- checked, `n2o.robot.attach_hand_to_arm`
welds the hand onto the arm's MuJoCo end-effector site (see `n2o.robot.simulation.
Simulator`) instead of just placing both in the same window unconnected.

Run with: `uv run --group app python apps/quickstart_ui.py`
"""

import importlib.metadata
import platform
import sys
import tempfile
import traceback
from datetime import UTC, datetime
from pathlib import Path

import PySide6
from PySide6.QtCore import QObject, QPoint, Qt, QThread, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QIcon,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from n2o import N2O
from n2o.command import GripSpreadCommand, OfnerCommand
from n2o.decoder import OfnerEEGNet
from n2o.robot.arm import SO101Arm
from n2o.robot.hand import AmazingHand
from n2o.signal.dataset import DatasetLoader

ICON_PATH = __file__.rsplit("/", 1)[0] + "/../docs/assets/N2O_logo.png"

# Same teal accent as the docs site (mkdocs.yml's `theme.palette.accent: teal`) --
# one brand-colored touch on an otherwise near-monochrome UI, mirroring
# docs/stylesheets/extra.css's own "single accent stripe" approach.
_ACCENT = "#00bfa5"
_ACCENT_HOVER = "#00a693"
_REQUIRED = "#f5a623"  # amber -- distinct from the teal accent, marks mandatory fields
_DANGER = "#e53935"  # a part row's remove ("x") button hover -- destructive action

_LIGHT = {
    "bg": "#fafafa",
    "panel": "#ffffff",
    "border": "#e0e0e0",
    "text": "#1a1a1a",
    "muted": "#6b6b6b",
    "field_bg": "#ffffff",
    "log_bg": "#1e1e1e",
    "log_text": "#d4d4d4",
}
_DARK = {
    "bg": "#202124",
    "panel": "#28292c",
    "border": "#3c3d40",
    "text": "#eaeaea",
    "muted": "#9a9a9a",
    "field_bg": "#2f3033",
    "log_bg": "#141414",
    "log_text": "#d4d4d4",
}


def _is_dark_mode() -> bool:
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False  # Qt < 6.5 -- no color-scheme query, fall back to light


def _make_down_arrow_icon(color: str) -> str:
    """Renders a small filled-triangle PNG and returns its path.

    Once `QComboBox` gets a custom border/padding via QSS, Fusion stops drawing its
    own built-in drop-down arrow (a known Qt behavior -- confirmed by rendering a
    bare, unstyled `QComboBox` side by side with one carrying just the border/padding
    rules above: only the styled one loses the arrow) -- `::down-arrow` needs a real
    image to fill that gap, and QSS `image: url(...)` needs an actual file, not a
    generated pixmap in memory."""
    pixmap = QPixmap(10, 10)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon([QPoint(1, 3), QPoint(9, 3), QPoint(5, 8)])
    painter.end()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as icon_file:
        path = icon_file.name
    pixmap.save(path)
    return path


def _build_stylesheet(colors: dict) -> str:
    arrow_icon_path = _make_down_arrow_icon(colors["muted"])
    return f"""
        QWidget {{
            background: {colors["bg"]};
            color: {colors["text"]};
            font-size: 13px;
        }}
        QGroupBox {{
            background: {colors["panel"]};
            border: 1px solid {colors["border"]};
            border-radius: 8px;
            margin-top: 14px;
            padding: 12px;
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: {colors["text"]};
        }}
        QLabel#logoBadge {{
            background: #ffffff;
            border: 1px solid {colors["border"]};
            border-radius: 8px;
        }}
        QLabel#headerTitle {{
            font-size: 18px;
            font-weight: 600;
        }}
        QLabel#headerSubtitle, QLabel#sectionLabel {{
            color: {colors["muted"]};
        }}
        QComboBox, QLineEdit {{
            background: {colors["field_bg"]};
            border: 1px solid {colors["border"]};
            border-radius: 6px;
            padding: 5px 8px;
            min-height: 20px;
        }}
        QComboBox:focus, QLineEdit:focus {{
            border: 1px solid {_ACCENT};
        }}
        QComboBox:disabled, QLineEdit:disabled {{
            background: {colors["bg"]};
            color: {colors["muted"]};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 22px;
            border-left: 1px solid {colors["border"]};
        }}
        QComboBox::down-arrow {{
            image: url({arrow_icon_path});
            width: 10px;
            height: 10px;
        }}
        QComboBox QAbstractItemView {{
            background: {colors["field_bg"]};
            border: 1px solid {colors["border"]};
            outline: none;
            selection-background-color: {_ACCENT};
            selection-color: #ffffff;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 4px 8px;
        }}
        QComboBox[required="true"], QGroupBox[required="true"] {{
            border-left: 3px solid {_REQUIRED};
        }}
        QPushButton {{
            background: {colors["panel"]};
            border: 1px solid {colors["border"]};
            border-radius: 6px;
            padding: 5px 10px;
        }}
        QPushButton:hover {{
            border: 1px solid {_ACCENT};
        }}
        QPushButton:disabled {{
            background: {colors["bg"]};
            color: {colors["muted"]};
        }}
        QPushButton#removeButton:hover {{
            border: 1px solid {_DANGER};
            color: {_DANGER};
        }}
        QPushButton#runButton {{
            background: {_ACCENT};
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 10px;
            font-weight: 600;
            font-size: 14px;
        }}
        QPushButton#runButton:hover {{
            background: {_ACCENT_HOVER};
        }}
        QPushButton#runButton:disabled {{
            background: {colors["border"]};
            color: {colors["muted"]};
        }}
        QPlainTextEdit#logPanel {{
            background: {colors["log_bg"]};
            color: {colors["log_text"]};
            border: 1px solid {colors["border"]};
            border-radius: 8px;
            padding: 8px;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 12px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {colors["border"]};
            border-radius: 4px;
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {_ACCENT};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
            border: none;
            background: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 12px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal {{
            background: {colors["border"]};
            border-radius: 4px;
            min-width: 24px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {_ACCENT};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
            border: none;
            background: none;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
    """


# Only combinations that are actually wired end-to-end today (see demos/quickstart.py,
# examples/04_hand_intent_classification_amazinghand.ipynb) -- not a general registry.
DECODERS = {"OfnerEEGNet": OfnerEEGNet}
COMMANDS = {"OfnerCommand": OfnerCommand, "GripSpreadCommand": GripSpreadCommand}
CONTROLLERS = ["simulation", "motor_driver"]
SIMULATION_BACKENDS = ["MuJoCo", "Unity"]

# "leg" (의족/prosthetic-leg terminology, not a limping robot) has no n2o.robot.leg
# package yet -- see _build_n2o()'s guard. If a "hand"-equivalent terminal effector
# for a leg ever gets added, "foot" would be the right name for it, mirroring
# arm/hand -- but that's a separate part from "leg" itself, same as arm/hand are.
PART_KINDS = ["arm", "hand", "leg"]
# Only the models an n2o.robot class actually exists for -- "leg" has none yet, so its
# model dropdown is left empty (see PartRow._populate_models()/_build_n2o()'s guard).
PART_MODELS = {"arm": ["SO101Arm"], "hand": ["AmazingHand"], "leg": []}
DEFAULT_PORTS = {"SO101Arm": "/dev/ttyACM0", "AmazingHand": "/dev/ttyACM1"}


class PartRow(QWidget):
    """One row in the 파츠/Parts group: a kind dropdown (arm/hand/leg), a model
    dropdown (e.g. "AmazingHand" for kind "hand" -- populated from `PART_MODELS[kind]`,
    empty for a kind with no model yet), a "설정" button for that model's port (opened
    via the window's shared `ask_port()`), and a "×" button to remove this row.
    `port_value` resets to the newly-selected model's own default whenever kind/model
    changes -- a leftover arm port makes no sense once the row becomes a hand."""

    removed = Signal(object)

    def __init__(self, window, kind):
        super().__init__()
        self._window = window
        self.port_value = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.kind_combo = QComboBox()
        self.kind_combo.addItems(PART_KINDS)
        self.kind_combo.setCurrentText(kind)
        self.kind_combo.setEditable(True)
        self.kind_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.kind_combo.currentTextChanged.connect(self._on_kind_changed)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)

        self.settings_button = QPushButton("설정")
        self.settings_button.clicked.connect(self._open_settings)

        self.remove_button = QPushButton("×")
        self.remove_button.setObjectName("removeButton")
        self.remove_button.setFixedWidth(28)
        self.remove_button.clicked.connect(lambda: self.removed.emit(self))

        layout.addWidget(self.kind_combo)
        layout.addWidget(self.model_combo)
        layout.addWidget(self.settings_button)
        layout.addWidget(self.remove_button)

        self._populate_models(kind)

    def set_kind_model_locked(self, locked: bool):
        """Disables kind_combo/model_combo -- used for a "leg" row once Controller
        means driving real hardware (see `QuickstartWindow.
        update_part_availability()`): no real leg controller exists to pick a model
        for. `settings_button` is left to that same method (its enabled state already
        depends on Controller by itself, independent of locking) and `remove_button`
        stays enabled either way -- a locked row should still be removable."""
        self.kind_combo.setEnabled(not locked)
        self.model_combo.setEnabled(not locked)

    def _on_kind_changed(self, kind):
        self._populate_models(kind)
        self._window.update_part_availability()

    def _populate_models(self, kind):
        self.model_combo.clear()
        self.model_combo.addItems(PART_MODELS.get(kind, []))

    def _on_model_changed(self, model):
        self.port_value = DEFAULT_PORTS.get(model, "")

    def _open_settings(self):
        label = self.model_combo.currentText() or self.kind_combo.currentText()
        port = self._window.ask_port(f"{label} 설정", self.port_value)
        if port is not None:
            self.port_value = port


class _LogStream(QObject):
    """Redirects stdout+stderr to the log panel -- stdout carries `N2O.run()`'s own
    print() progress, stderr carries pooch/tqdm's dataset-download progress bar
    (`DatasetLoader.read()` downloads straight from `moabb`/`pooch`, which write
    there, not stdout). Without this, a slow/first-time dataset download looks like
    the UI hung on "추론 진행 중" with no sign anything is happening -- the real
    progress was only ever visible in the terminal `quickstart_ui.py` was launched
    from, never in the GUI's own log panel."""

    text_written = Signal(str)

    def write(self, text):
        if text:
            self.text_written.emit(text)

    def flush(self):
        pass

    def isatty(self):
        # tqdm (pooch's progress bar) checks this to decide how it renders -- `str`
        # has no meaningful "no" answer here, but being explicit avoids tqdm falling
        # back to some library-version-dependent default for a stream with no
        # `isatty` at all.
        return False


class RunWorker(QObject):
    finished = Signal()
    failed = Signal(str)

    def __init__(self, n2o, controller):
        super().__init__()
        self.n2o = n2o
        self.controller = controller

    def run(self):
        try:
            self.n2o.run(controller=self.controller)
        except Exception:  # noqa: BLE001 -- shown in the GUI log instead of crashing it
            self.failed.emit(traceback.format_exc())
        finally:
            self.finished.emit()


class QuickstartWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("N2O Quick Start")
        self._thread = None
        self._worker = None
        self._build_central_widget()

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(10)

        logo = QLabel()
        logo.setObjectName("logoBadge")
        pixmap = QPixmap(ICON_PATH)
        if not pixmap.isNull():
            # The logo PNG has an opaque white background (fine on the docs site's own
            # light header) -- a plain white badge behind it here reads as an
            # intentional tile instead of a stray white box in dark mode. Badge width
            # follows the scaled pixmap's own width (plus padding) so the full,
            # non-square logo shows instead of being cropped by a fixed square size.
            pixmap = pixmap.scaledToHeight(
                28, Qt.TransformationMode.SmoothTransformation
            )
            logo.setPixmap(pixmap)
            logo.setFixedSize(pixmap.width() + 16, 40)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("N2O Quick Start")
        title.setObjectName("headerTitle")
        subtitle = QLabel("signal → decoder → command → robot 초기 설정")
        subtitle.setObjectName("headerSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch()
        return header

    def _build_central_widget(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        layout.addLayout(self._build_header())

        form_box = QGroupBox("초기 설정")
        form = QFormLayout(form_box)
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(12)

        self.signal_combo = QComboBox()
        self.signal_combo.addItems(DatasetLoader.list_libraries())
        self.signal_combo.setCurrentText("Ofner2017")
        form.addRow("Signal (dataset name)", self.signal_combo)

        self.decoder_combo = QComboBox()
        self.decoder_combo.addItems(DECODERS.keys())
        form.addRow("Decoder", self.decoder_combo)

        self.command_combo = QComboBox()
        self.command_combo.addItems(COMMANDS.keys())
        form.addRow("Command", self.command_combo)

        self.controller_combo = QComboBox()
        self.controller_combo.addItems(CONTROLLERS)

        # MuJoCo is the only simulation backend actually wired up (n2o.robot.simulation)
        # -- Unity is a second backend in progress, not in this codebase yet (see
        # _on_run_clicked's guard). A dropdown (not radio buttons) so this scales to
        # more backends later without the row growing wider -- it already gets the
        # same scrollable popup as every other combo here once the list outgrows the
        # visible area (see QScrollBar styling above).
        self.simulation_backend_combo = QComboBox()
        self.simulation_backend_combo.addItems(SIMULATION_BACKENDS)

        controller_row = QHBoxLayout()
        controller_row.addWidget(self.controller_combo)
        controller_row.addWidget(self.simulation_backend_combo)
        form.addRow("Controller", controller_row)

        self.controller_combo.currentTextChanged.connect(
            self._update_simulation_backend_visibility
        )
        self._update_simulation_backend_visibility()

        # Editable so every dropdown's popup gets the same hover-follows-mouse fill
        # Signal already had (a plain, non-editable QComboBox popup only ever shows
        # Fusion's thin hover outline, never a solid fill -- confirmed by hand on a
        # real desktop, not just this sandbox's display-less renderer).
        for combo in (
            self.signal_combo,
            self.decoder_combo,
            self.command_combo,
            self.controller_combo,
            self.simulation_backend_combo,
        ):
            combo.setEditable(True)
            combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        # Signal/Decoder/Command always hold a value already (no "없음" option) --
        # marked required so the one field that genuinely can be left empty (파츠,
        # via its own required-marked QGroupBox below) doesn't read as the odd one
        # out, not because these three are ever actually blank.
        for required_field in (
            self.signal_combo,
            self.decoder_combo,
            self.command_combo,
        ):
            required_field.setProperty("required", True)

        layout.addWidget(form_box)

        self.part_rows = []
        layout.addWidget(self._build_parts_group())
        self.controller_combo.currentTextChanged.connect(self.update_part_availability)

        self.run_button = QPushButton("실행")
        self.run_button.setObjectName("runButton")
        self.run_button.setMinimumHeight(36)
        self.run_button.clicked.connect(self._on_run_clicked)
        layout.addWidget(self.run_button)

        log_label = QLabel("실행 로그")
        log_label.setObjectName("sectionLabel")
        layout.addWidget(log_label)

        self.log = QPlainTextEdit(readOnly=True)
        self.log.setObjectName("logPanel")
        self.log.setFont(QFont("monospace"))
        layout.addWidget(self.log)

        self._log_stream = _LogStream()
        self._log_stream.text_written.connect(self._append_log, Qt.QueuedConnection)

    def _update_simulation_backend_visibility(self):
        is_simulation = self.controller_combo.currentText() == "simulation"
        self.simulation_backend_combo.setVisible(is_simulation)

    def _build_parts_group(self) -> QGroupBox:
        group = QGroupBox("파츠")
        group.setProperty("required", True)
        outer = QVBoxLayout(group)

        self._parts_list_layout = QVBoxLayout()
        self._parts_list_layout.setSpacing(8)
        outer.addLayout(self._parts_list_layout)

        add_button = QPushButton("+ 파츠 추가")
        add_button.clicked.connect(lambda: self._add_part_row())
        outer.addWidget(add_button)

        # Only meaningful for the MuJoCo simulation backend, and only once both an
        # arm and a hand row exist -- see update_part_availability(). Real hardware
        # mounting is a physical assembly question, not something n2o decides.
        self.attach_hand_checkbox = QCheckBox("손을 팔 말단에 연결 (시뮬레이션)")
        self.attach_hand_checkbox.setEnabled(False)
        outer.addWidget(self.attach_hand_checkbox)

        return group

    def _add_part_row(self, kind=None):
        row = PartRow(self, kind or PART_KINDS[0])
        row.removed.connect(self._remove_part_row)
        self._parts_list_layout.addWidget(row)
        self.part_rows.append(row)
        self.update_part_availability()

    def _remove_part_row(self, row):
        self.part_rows.remove(row)
        self._parts_list_layout.removeWidget(row)
        row.deleteLater()

    def update_part_availability(self):
        # "leg" has no real controller (see _build_n2o()'s guard) -- writing one is
        # much harder than arm/hand's (torque control + sensor fusion for actual
        # walking, not a lookup-table gesture) -- so a "leg" row locks (everything but
        # its × stays clickable) once Controller means driving real hardware, instead
        # of silently falling back to some other kind. Simulation is unaffected --
        # MuJoCo already has a working leg model to simulate against (MyoSuite's
        # myoOSL), and switching back to it unlocks the row again.
        is_motor_driver = self.controller_combo.currentText() == "motor_driver"
        for row in self.part_rows:
            is_leg_locked = is_motor_driver and row.kind_combo.currentText() == "leg"
            row.set_kind_model_locked(is_leg_locked)
            row.settings_button.setEnabled(is_motor_driver and not is_leg_locked)

        kinds = [row.kind_combo.currentText() for row in self.part_rows]
        self.attach_hand_checkbox.setEnabled(
            self.controller_combo.currentText() == "simulation"
            and "arm" in kinds
            and "hand" in kinds
        )

    def ask_port(self, title, current_port):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        form = QFormLayout(dialog)
        port_edit = QLineEdit(current_port)
        form.addRow("Port", port_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return port_edit.text()
        return None

    def _append_log(self, text):
        """Appends `text`, treating a bare `\\r` (tqdm's own in-place progress-bar
        update, e.g. pooch's download bar or `N2O._decode_with_progress()`'s own
        dots) the way a real terminal would -- overwrite the current line -- instead
        of leaving a literal `\\r` in the document, which `QPlainTextEdit` doesn't
        interpret and would otherwise just print as visible line noise."""
        cursor = self.log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        for i, chunk in enumerate(text.split("\r")):
            if i > 0:
                cursor.select(cursor.SelectionType.LineUnderCursor)
                cursor.removeSelectedText()
            cursor.insertText(chunk)
        self.log.setTextCursor(cursor)

    def _on_run_clicked(self):
        if not self.part_rows:
            QMessageBox.warning(
                self, "설정 필요", "파츠를 최소 하나는 추가해야 합니다."
            )
            return

        if (
            self.controller_combo.currentText() == "simulation"
            and self.simulation_backend_combo.currentText() != "MuJoCo"
        ):
            QMessageBox.warning(
                self,
                "아직 지원 안 함",
                "Unity 시뮬레이션 백엔드는 아직 개발 중입니다 -- MuJoCo를 선택해주세요.",
            )
            return

        try:
            n2o = self._build_n2o()
        except Exception:  # noqa: BLE001 -- shown in a dialog instead of crashing the GUI
            self._show_error_dialog("설정 오류", traceback.format_exc())
            return

        self.run_button.setEnabled(False)
        self.log.clear()

        self._thread = QThread()
        self._worker = RunWorker(n2o, self.controller_combo.currentText())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_run_finished)
        self._worker.failed.connect(self._on_run_failed)
        self._worker.finished.connect(self._thread.quit)

        self._restore_stdout = sys.stdout
        self._restore_stderr = sys.stderr
        sys.stdout = self._log_stream
        sys.stderr = self._log_stream

        self._thread.start()

    def _build_n2o(self):
        n2o = N2O()
        n2o.signal = DatasetLoader(name=self.signal_combo.currentText())
        n2o.decoder = DECODERS[self.decoder_combo.currentText()]()
        n2o.command = COMMANDS[self.command_combo.currentText()]()
        n2o.robot.attach_hand_to_arm = self.attach_hand_checkbox.isChecked()

        seen_kinds = set()
        for row in self.part_rows:
            kind = row.kind_combo.currentText()
            model = row.model_combo.currentText()
            if kind in seen_kinds:
                raise ValueError(
                    f"'{kind}' 파츠가 중복 지정되었습니다 -- 하나만 지정할 수 있습니다."
                )
            seen_kinds.add(kind)
            if model == "SO101Arm":
                n2o.robot.arm = SO101Arm(port=row.port_value)
            elif model == "AmazingHand":
                n2o.robot.hand = AmazingHand(port=row.port_value)
            else:
                raise NotImplementedError(
                    f"'{kind}' 파츠(모델: {model or '없음'})는 아직 n2o에 구현되지 않았습니다 -- ROADMAP.md 참고"
                )
        return n2o

    def _on_run_finished(self):
        sys.stdout = self._restore_stdout
        sys.stderr = self._restore_stderr
        self.run_button.setEnabled(True)

    def _on_run_failed(self, tb_text):
        self._append_log(tb_text)
        self._show_error_dialog("실행 오류", tb_text)

    def _show_error_dialog(self, title, tb_text):
        """A traceback alone ("에러남!") isn't enough for anyone else to fix this --
        "리포트 저장" bundles it with the environment/config info a developer would
        actually need (OS, package versions, current dropdown selections) into one
        text file the user can attach wherever they report the bug.

        The full traceback goes in `setDetailedText()` (a collapsed, scrollable
        "Show Details..." panel), not `setText()` -- putting it directly in `setText()`
        makes the dialog grow to fit every line with no scrolling, which can push its
        own buttons past the screen edge on a long traceback."""
        stripped = tb_text.strip()
        summary = stripped.splitlines()[-1] if stripped else "알 수 없는 오류"

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle(title)
        box.setText(summary)
        box.setDetailedText(tb_text)
        report_button = box.addButton(
            "리포트 저장...", QMessageBox.ButtonRole.ActionRole
        )
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if box.clickedButton() is report_button:
            self._save_error_report(tb_text)

    def _build_error_report(self, tb_text):
        try:
            n2o_version = importlib.metadata.version("neural-to-output")
        except importlib.metadata.PackageNotFoundError:
            n2o_version = "알 수 없음"

        lines = [
            "# n2o Quickstart 오류 리포트",
            "",
            f"- 시각: {datetime.now(UTC).isoformat()}",
            f"- OS: {platform.platform()}",
            f"- Python: {platform.python_version()}",
            f"- PySide6: {PySide6.__version__}",
            f"- neural-to-output: {n2o_version}",
            "",
            "## 현재 설정",
            f"- Signal: {self.signal_combo.currentText()}",
            f"- Decoder: {self.decoder_combo.currentText()}",
            f"- Command: {self.command_combo.currentText()}",
            f"- Controller: {self.controller_combo.currentText()}",
            f"- Simulation backend: {self.simulation_backend_combo.currentText()}",
            "- Parts: "
            + (
                ", ".join(
                    f"{row.kind_combo.currentText()}/{row.model_combo.currentText() or '없음'}"
                    for row in self.part_rows
                )
                or "(없음)"
            ),
            "",
            "## Traceback",
            "```",
            tb_text.rstrip("\n"),
            "```",
        ]
        return "\n".join(lines)

    def _save_error_report(self, tb_text):
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "오류 리포트 저장",
            f"n2o_error_report_{timestamp}.txt",
            "Text files (*.txt)",
        )
        if not path:
            return
        Path(path).write_text(self._build_error_report(tb_text), encoding="utf-8")
        QMessageBox.information(self, "저장됨", f"{path}에 저장했습니다.")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(ICON_PATH))
    app.setStyleSheet(_build_stylesheet(_DARK if _is_dark_mode() else _LIGHT))
    window = QuickstartWindow()
    window.resize(720, 720)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

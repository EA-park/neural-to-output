"""Desktop console for the n2o pipeline (signal -> decoder -> command -> robot).

The UI-equivalent of `demos/quickstart.py` -- see `ROADMAP.md`'s "quickstart를 UI로"
entry. Picks the same kind of components `quickstart.py` wires by hand, then hands
off to a small `RunPanel` window to actually drive `N2O.run()`.

Two windows, two jobs:

- `ConsoleWindow` -- configuration only. Its "다음" button builds the `N2O` instance
  and calls `n2o.prepare(controller)` (see `n2o.N2O.prepare()`) -- for `"simulation"`
  this is the point the MuJoCo viewer window actually opens (Unity has no local
  window to open; it connects lazily on the first real `drive()` call instead, same
  as always). Nothing has actually run yet at this point -- `prepare()` only sets up
  `self.robot.controller`/`self.robot.simulator`, it never reads a signal or moves
  anything. Once `prepare()` succeeds, `ConsoleWindow` opens a `RunPanel` next to
  itself and backgrounds itself (tray icon if the desktop supports one, otherwise a
  plain taskbar-minimize -- see `_enter_background_mode()`) so the simulation window
  isn't competing with a config form the user is done with, and so their taskbar
  doesn't end up cluttered on top of the simulation/Unity windows already there.
- `RunPanel` -- a small standalone window with its own "실행" button. Only clicking
  *that* actually calls `n2o.run(controller)` (which internally calls `prepare()`
  again, a no-op by then since `self.robot.simulator` is already assigned -- see
  `N2O.run()`/`N2O.prepare()`). Applies to every controller, not just "simulation" --
  a `motor_driver` run also stops at this confirmation panel before touching real
  hardware, since driving a real robot with no "are you sure" step at all is the
  riskier default. "설정으로 돌아가기" closes this panel and restores `ConsoleWindow`;
  disabled while a run is actually in flight (`N2O.run()`'s cycle loop itself has no
  cancellation hook, so closing this panel mid-run would just orphan the background
  thread with no way to see its outcome). For a `simulation` run specifically,
  closing the MuJoCo viewer window *does* stop it -- `_MujocoModel.drive_ctrl()`
  raises `n2o.robot.simulation.mujoco.ViewerClosed` the moment the window it was
  animating is gone, which surfaces here as a normal "실행 오류" dialog. There's no
  equivalent for `motor_driver` (no window to close) or for the Unity backend (a
  separate, possibly-remote process this app doesn't control).

Robot parts are a dynamic list (파츠/Parts group) instead of fixed arm/hand rows --
"+ 파츠 추가" adds a row, each row picks a kind (arm/hand) from a dropdown and can be
removed again. A row's "설정" button opens a small dialog for whatever that part
actually needs right now -- see `PartRow._open_settings()`.

Controller has a third option beyond the uniform "simulation"/"motor_driver":
"개별 선택" reveals an inline controller dropdown on every part row (`PartRow.
controller_combo`) so each part can run on a different controller at the same
time -- e.g. the arm on real hardware while the hand is simulated. Choosing
"simulation" on a row then reveals its own simulation-backend/Unity-engine/rig.json
choices inside that row's "설정" dialog rather than the window-level combos (which
apply uniformly and are hidden in this mode) -- one MuJoCo `Simulator` and/or one
`UnitySimulator` gets built per backend actually in use, covering every part that
picked it, and assigned into `n2o.robot.part_simulators` per part (see `Robot.
part_controllers`/`part_simulators`, and `ConsoleWindow._apply_individual_controllers()`).
The Unity endpoint field is still shared window-level (one connection for every
Unity-backed part, not one per part).

Controller "simulation" also picks a backend (MuJoCo/Unity, 시뮬레이션 백엔드
dropdown). MuJoCo is `n2o.run()`'s own default -- `_build_n2o()` leaves
`n2o.robot.simulator` unset and lets `prepare()` auto-build one. Unity means
assigning an `n2o.robot.simulation.unity.UnitySimulator` onto `n2o.robot.simulator`
ourselves first (see that class's own docstring for why `n2o.run()`/`prepare()` can't
do this on its own) -- its "host:port" field (엔드포인트, only visible for the Unity
backend) is where a separate Unity process is expected to be listening. Because that
Unity process is manually operated (the user has to press Play themselves before a
connection can succeed), a Unity-backend `RunPanel` shows an extra "Unity 안내" box
(steps + a small scrollable usage-tips panel) and, on a failed connection attempt,
swaps the usual scary Critical/traceback "실행 오류" dialog for a friendlier
Warning-icon one telling the user to check Play and retry -- see `RunPanel.
_build_unity_guidance_box()`/`_on_run_failed()`.

Picking Unity also reveals a second, independent choice (Unity 엔진 dropdown,
`unity_engine_combo`) for *how* the Unity side actually simulates -- the official
MuJoCo Unity plugin (real MuJoCo physics running in-process inside Unity, loads
either MJCF directly) or our own `ArticulationBody`-based rig, built from a JSON
descriptor `n2o.robot.simulation.unity.solver.ClosedLoopRigSolver` generates from
the same MJCF (see the companion `neural-to-output-unity` repo's own README for
the Unity-side scripts either engine needs -- this repo ships no Unity project
or C# source itself). This choice never changes what
`UnitySimulator` sends over the wire -- `_build_n2o()`'s Unity branch is
identical either way -- it only changes which setup steps `RunPanel`'s guidance
box names (`_engine_setup_tip()`).

Attaching the hand to the arm's end-effector isn't a floating window-level
checkbox -- it's a "부착 대상" dropdown inside the *hand* row's own "설정" dialog
(`없음`/`arm`), only offered once an arm row exists, is itself simulating, and
shares the hand's same backend (welding across two unrelated physics worlds --
say a MuJoCo arm and a Unity hand -- makes no sense). `n2o.robot.
attach_hand_to_arm` (`_build_n2o()`/`_apply_individual_controllers()`) is set from
`any(row.attach_to == "arm" for row in part_rows)`; for the MuJoCo backend it
welds the hand onto the arm's end-effector site (`n2o.robot.simulation.
Simulator`); for the Unity Native (PhysX) engine, the hand's own "rig.json
재생성" button instead generates one *combined* rig.json (both parts merged onto
that same site via `ClosedLoopRigSolver`'s `attach=` option) rather than two
separate files.

Run with: `uv run --group app python apps/console.py`
"""

import html
import importlib.metadata
import inspect
import json
import platform
import re
import socket
import subprocess
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
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from n2o import N2O
from n2o.command import GripSpreadCommand, OfnerCommand, OfnerHandCommand
from n2o.decoder import OfnerEEGNet
from n2o.robot import ControllerType
from n2o.robot.arm import SO101Arm
from n2o.robot.hand import AmazingHand
from n2o.robot.simulation import Simulator
from n2o.robot.simulation.mujoco.simulator import ARM_GRIPPER_SITE, HAND_PREFIX
from n2o.robot.simulation.unity import UnitySimulator
from n2o.robot.simulation.unity.solver import ClosedLoopRigSolver, rig_json_status
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
        QGroupBox#summaryBox {{
            background: #ffffff;
            color: #1a1a1a;
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
COMMANDS = {
    "OfnerCommand": OfnerCommand,
    "OfnerHandCommand": OfnerHandCommand,
    "GripSpreadCommand": GripSpreadCommand,
}
CONTROLLERS = ["simulation", "motor_driver", "개별 선택"]
# What each PartRow's own controller_combo offers -- "개별 선택" only makes sense
# as the *window-level* choice that reveals these per-part combos in the first
# place, so it isn't itself one of the per-part options.
PART_CONTROLLERS = ["simulation", "motor_driver"]
SIMULATION_BACKENDS = ["MuJoCo", "Unity"]
DEFAULT_UNITY_ENDPOINT = "127.0.0.1:9999"  # UnitySimulator's own host/port defaults
# A second, independent choice from SIMULATION_BACKENDS -- see
# self.unity_engine_combo's own comment for what each option means. Named
# "engine" (not another "backend") specifically so it can't be confused with
# SIMULATION_BACKENDS in code or in the UI.
UNITY_ENGINES = ["MuJoCo Plugin", "Unity Native (PhysX)"]

PART_KINDS = ["arm", "hand"]
PART_MODELS = {"arm": ["SO101Arm"], "hand": ["AmazingHand"]}
DEFAULT_PORTS = {"SO101Arm": "/dev/ttyACM0", "AmazingHand": "/dev/ttyACM1"}

# Model name -> bare robot MJCF path (not the scene.xml wrapper `simulation/mujoco/
# simulator.py` uses -- ClosedLoopRigSolver takes the plain robot MJCF, matching
# the file names RunPanel._engine_setup_tip() already tells the user to point the
# CLI at). Resolved from each Part class's own module file rather than a path
# relative to this file, so it works the same whether n2o is an editable checkout
# or an installed package. A model absent from this dict has no bundled MJCF --
# neither Unity engine needs one, so Unity backend isn't offered for it at all
# (see PartRow._open_settings()).
MJCF_PATHS = {
    "SO101Arm": Path(inspect.getfile(SO101Arm)).parent / "mjcf" / "so101_new_calib.xml",
    "AmazingHand": Path(inspect.getfile(AmazingHand)).parent / "mjcf" / "robot.xml",
}


def _find_unity_listening_ports() -> list[int]:
    """Returns local TCP ports some process named like "Unity" (Editor or a
    Standalone Player -- both show up this way in `ss`'s process column) is
    currently listening on. A running Unity process always has several of these
    (its own internal profiler/editor-messaging/debugger sockets) whether or not
    your own socket-listener script has started -- this only tells you *what's
    open*, not *which one is yours*; `_check_unity_connection()` below still needs
    to disambiguate when more than one comes back.

    Linux-only (`ss`, from iproute2) -- this app ships a Linux `.desktop` launcher,
    no macOS/Windows support exists elsewhere in this file either. Returns an empty
    list rather than raising if `ss` isn't on PATH, so this stays a best-effort
    diagnostic instead of a hard requirement for the Unity backend to work at all."""
    try:
        output = subprocess.run(
            ["ss", "-ltnp"], capture_output=True, text=True, timeout=5, check=False
        ).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    ports = []
    for line in output.splitlines():
        if "unity" not in line.lower():
            continue
        match = re.search(r":(\d+)\s+\S+\s+users:", line)
        if match:
            ports.append(int(match.group(1)))
    return ports


def _tcp_ping(host: str, port: int, timeout: float = 1.5) -> bool:
    """Best-effort "is anything answering here" check -- a real TCP connect/close,
    not ICMP (`UnitySimulator.launch_viewer()` itself does a TCP connect, so this
    mirrors the actual failure mode instead of a ping that could succeed while the
    real connection still wouldn't)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _build_error_report(config_lines, tb_text) -> str:
    try:
        n2o_version = importlib.metadata.version("neural-to-output")
    except importlib.metadata.PackageNotFoundError:
        n2o_version = "알 수 없음"

    lines = [
        "# n2o Console 오류 리포트",
        "",
        f"- 시각: {datetime.now(UTC).isoformat()}",
        f"- OS: {platform.platform()}",
        f"- Python: {platform.python_version()}",
        f"- PySide6: {PySide6.__version__}",
        f"- neural-to-output: {n2o_version}",
        "",
        "## 현재 설정",
        *config_lines,
        "",
        "## Traceback",
        "```",
        tb_text.rstrip("\n"),
        "```",
    ]
    return "\n".join(lines)


def _save_error_report(parent, config_lines, tb_text):
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path, _ = QFileDialog.getSaveFileName(
        parent,
        "오류 리포트 저장",
        f"n2o_error_report_{timestamp}.txt",
        "Text files (*.txt)",
    )
    if not path:
        return
    Path(path).write_text(_build_error_report(config_lines, tb_text), encoding="utf-8")
    QMessageBox.information(parent, "저장됨", f"{path}에 저장했습니다.")


def show_error_dialog(parent, title, tb_text, config_lines, *, summary=None, icon=QMessageBox.Icon.Critical):
    """Shared by `ConsoleWindow` (설정 오류, e.g. `n2o.prepare()` failing to open a
    simulation viewer) and `RunPanel` (실행 오류, `N2O.run()` itself failing) -- a
    bare traceback ("에러남!") isn't enough for anyone else to fix this, so
    "리포트 저장" bundles it with the environment/config info a developer would
    actually need (OS, package versions, the config selections in `config_lines`)
    into one text file the user can attach wherever they report the bug.

    The full traceback goes in `setDetailedText()` (a collapsed, scrollable
    "Show Details..." panel), not `setText()` -- putting it directly in `setText()`
    makes the dialog grow to fit every line with no scrolling, which can push its
    own buttons past the screen edge on a long traceback.

    `summary`/`icon` let a caller override the headline text and icon for a known,
    recoverable failure (e.g. `RunPanel`'s Unity-connection-error case) while still
    reusing this same "Show Details.../리포트 저장..." machinery -- the raw
    traceback's last line makes a poor headline for an error the user already knows
    how to fix."""
    stripped = tb_text.strip()
    if summary is None:
        summary = stripped.splitlines()[-1] if stripped else "알 수 없는 오류"

    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(summary)
    box.setDetailedText(tb_text)
    report_button = box.addButton("리포트 저장...", QMessageBox.ButtonRole.ActionRole)
    box.addButton(QMessageBox.StandardButton.Ok)
    box.exec()
    if box.clickedButton() is report_button:
        _save_error_report(parent, config_lines, tb_text)


_RIG_STATUS_TEXT = {
    "missing": "⚠ rig.json 없음 -- 생성 필요",
    "stale": "⚠ rig.json이 오래됨 -- 다시 생성 권장",
    "current": "✓ rig.json 최신",
}


class PartRow(QWidget):
    """One row in the 파츠/Parts group: a kind dropdown (arm/hand), a model
    dropdown (e.g. "AmazingHand" for kind "hand" -- populated from `PART_MODELS[kind]`,
    empty for a kind with no model yet), an inline controller dropdown (only visible
    once the window's own Controller is "개별 선택" -- see `ConsoleWindow.
    _update_simulation_backend_visibility()`), a "설정" button opening this row's own
    settings dialog, and a "×" button to remove this row.

    `port_value` resets to the newly-selected model's own default whenever kind/model
    changes -- a leftover arm port makes no sense once the row becomes a hand.
    `sim_backend`/`unity_engine` are this row's own simulation choices in "개별 선택"
    mode (irrelevant, but harmless, otherwise) -- set via `_open_settings()`'s dialog,
    not directly editable in the row itself (no room for three more dropdowns per
    row). `attach_to` is `None` or `"arm"` -- only ever set on a "hand" row, replacing
    the old single global "손을 팔에 연결" checkbox (see `ConsoleWindow.
    _build_n2o()`) with a per-part choice that says explicitly *which* part this one
    attaches to, set from the same settings dialog."""

    removed = Signal(object)

    def __init__(self, window, kind):
        super().__init__()
        self._window = window
        self.port_value = ""
        self.sim_backend = SIMULATION_BACKENDS[0]
        self.unity_engine = UNITY_ENGINES[0]
        self.attach_to = None

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

        self.controller_combo = QComboBox()
        self.controller_combo.addItems(PART_CONTROLLERS)
        self.controller_combo.setEditable(True)
        self.controller_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.controller_combo.setVisible(False)
        self.controller_combo.currentTextChanged.connect(
            lambda _: self._window.refresh_part_dependent_ui()
        )

        self.settings_button = QPushButton("설정")
        self.settings_button.clicked.connect(self._open_settings)

        self.remove_button = QPushButton("×")
        self.remove_button.setObjectName("removeButton")
        self.remove_button.setFixedWidth(28)
        self.remove_button.clicked.connect(lambda: self.removed.emit(self))

        layout.addWidget(self.kind_combo)
        layout.addWidget(self.model_combo)
        layout.addWidget(self.controller_combo)
        layout.addWidget(self.settings_button)
        layout.addWidget(self.remove_button)

        self._populate_models(kind)

    def _on_kind_changed(self, kind):
        self._populate_models(kind)
        self._window.refresh_part_dependent_ui()

    def _populate_models(self, kind):
        self.model_combo.clear()
        self.model_combo.addItems(PART_MODELS.get(kind, []))

    def _on_model_changed(self, model):
        self.port_value = DEFAULT_PORTS.get(model, "")

    def _own_controller(self) -> str:
        """This row's effective controller -- its own inline dropdown once the
        window is in "개별 선택" mode, otherwise whatever the window's uniform
        Controller is ("simulation" or "motor_driver") -- every part shares
        that one value outside "개별 선택"."""
        mode = self._window.controller_combo.currentText()
        if mode == "개별 선택":
            return self.controller_combo.currentText()
        return mode

    def _open_settings(self):
        model = self.model_combo.currentText()
        kind = self.kind_combo.currentText()
        label = model or kind
        own_controller = self._own_controller()
        is_individual = self._window._is_individual_mode()
        has_mjcf = model in MJCF_PATHS

        # backend_combo/engine_combo/attach_combo commit to `self` live (as they
        # change), not deferred to "OK" like port_edit below -- each has a visible
        # side effect (rig.json status, which options the other offers) that has
        # to update while the dialog is still open. Snapshot here so Cancel can
        # still restore them to what they were before this dialog opened.
        original_sim_backend = self.sim_backend
        original_unity_engine = self.unity_engine
        original_attach_to = self.attach_to

        dialog = QDialog(self)
        dialog.setWindowTitle(f"{label} 설정")
        form = QFormLayout(dialog)

        port_edit = None
        backend_combo = None
        engine_combo = None
        attach_combo = None
        arm_row = None
        rig_row = None
        rig_status_label = None

        def _current_backend():
            if backend_combo is not None:
                return backend_combo.currentText()
            return self._window.simulation_backend_combo.currentText()

        def _current_engine():
            if engine_combo is not None:
                return engine_combo.currentText()
            return self._window.unity_engine_combo.currentText()

        if own_controller == "motor_driver":
            port_edit = QLineEdit(self.port_value)
            form.addRow("Port", port_edit)
        else:  # simulation
            if is_individual:
                # Only meaningful per-part in "개별 선택" -- outside it, backend/
                # engine are the window's own uniform combos, so this row has
                # nothing of its own to offer here beyond rig.json/부착 below.
                backend_combo = QComboBox()
                backend_combo.addItems(SIMULATION_BACKENDS)
                backend_combo.setCurrentText(self.sim_backend)
                form.addRow("시뮬레이션 백엔드", backend_combo)

                engine_row = QWidget()
                engine_layout = QHBoxLayout(engine_row)
                engine_layout.setContentsMargins(0, 0, 0, 0)
                engine_combo = QComboBox()
                engine_combo.addItems(UNITY_ENGINES)
                engine_combo.setCurrentText(self.unity_engine)
                engine_layout.addWidget(engine_combo)
                form.addRow("Unity 엔진", engine_row)

                if not has_mjcf:
                    engine_combo.setEnabled(False)
                    engine_combo.setToolTip(
                        f"{label}에는 번들된 MJCF가 없어 Unity 엔진을 선택할 수 없습니다."
                    )

            rig_button = QPushButton("rig.json 재생성")
            rig_status_label = QLabel()
            rig_row = QWidget()
            rig_layout = QHBoxLayout(rig_row)
            rig_layout.setContentsMargins(0, 0, 0, 0)
            rig_layout.addWidget(rig_status_label)
            rig_layout.addWidget(rig_button)
            form.addRow("rig.json", rig_row)

            if kind == "hand":
                arm_row = next(
                    (r for r in self._window.part_rows if r.kind_combo.currentText() == "arm"),
                    None,
                )
                attach_combo = QComboBox()
                form.addRow("부착 대상", attach_combo)

            def _arm_backend():
                if arm_row is None:
                    return None
                if is_individual:
                    return arm_row.sim_backend
                return self._window.simulation_backend_combo.currentText()

            def _attach_compatible():
                return (
                    arm_row is not None
                    and arm_row._own_controller() == "simulation"
                    and _arm_backend() == _current_backend()
                )

            def _refresh_attach_options():
                """Repopulates 부착 대상's own items (없음, and "arm" only while
                compatible) and reselects `self.attach_to` -- the *view* mirroring
                `self`'s current state, never the other direction (that's
                `_on_attach_changed()`'s job)."""
                if attach_combo is None:
                    return
                attach_combo.blockSignals(True)
                attach_combo.clear()
                attach_combo.addItem("없음")
                compatible = _attach_compatible()
                if compatible:
                    attach_combo.addItem("arm")
                attach_combo.setCurrentText(
                    "arm" if self.attach_to == "arm" and compatible else "없음"
                )
                attach_combo.blockSignals(False)

            def _refresh_rig_status():
                is_unity_native = (
                    _current_backend() == "Unity"
                    and _current_engine() == "Unity Native (PhysX)"
                    and has_mjcf
                )
                rig_row.setVisible(is_unity_native)
                if not is_unity_native:
                    return
                mjcf_path, attach, default_json_path = self._window._resolve_rig_target(self)
                if mjcf_path is None:
                    rig_status_label.setText("")
                    return
                status = rig_json_status(
                    default_json_path, mjcf_path, attach[0] if attach else None
                )
                rig_status_label.setText(_RIG_STATUS_TEXT[status])

            def _on_backend_or_engine_changed():
                self.sim_backend = backend_combo.currentText()
                self.unity_engine = engine_combo.currentText()
                _refresh_attach_options()
                _refresh_rig_status()

            def _on_attach_changed():
                choice = attach_combo.currentText()
                self.attach_to = choice if choice == "arm" else None
                _refresh_rig_status()

            if backend_combo is not None:
                backend_combo.currentTextChanged.connect(
                    lambda _: _on_backend_or_engine_changed()
                )
                engine_combo.currentTextChanged.connect(
                    lambda _: _on_backend_or_engine_changed()
                )
            if attach_combo is not None:
                attach_combo.currentTextChanged.connect(lambda _: _on_attach_changed())
            rig_button.clicked.connect(
                lambda: (
                    self._window.regenerate_rig_json(dialog, self),
                    _refresh_rig_status(),
                )
            )

            _refresh_attach_options()
            _refresh_rig_status()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if port_edit is not None:
                self.port_value = port_edit.text()
        else:
            self.sim_backend = original_sim_backend
            self.unity_engine = original_unity_engine
            self.attach_to = original_attach_to
        self._window.refresh_part_dependent_ui()


class _LogStream(QObject):
    """Redirects stdout+stderr to a log panel -- stdout carries `N2O.run()`'s own
    print() progress, stderr carries pooch/tqdm's dataset-download progress bar
    (`DatasetLoader.read()` downloads straight from `moabb`/`pooch`, which write
    there, not stdout). Without this, a slow/first-time dataset download looks like
    the UI hung on "추론 진행 중" with no sign anything is happening -- the real
    progress was only ever visible in the terminal `console.py` was launched from,
    never in the GUI's own log panel."""

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
    failed = Signal(object, str)  # (exception, formatted traceback)

    def __init__(self, n2o, controller):
        super().__init__()
        self.n2o = n2o
        self.controller = controller

    def run(self):
        try:
            self.n2o.run(controller=self.controller)
        except Exception as exc:  # noqa: BLE001 -- shown in the GUI log instead of crashing it
            self.failed.emit(exc, traceback.format_exc())
        finally:
            self.finished.emit()


class RunPanel(QWidget):
    """Small standalone window `ConsoleWindow` opens once its own "다음" button has
    already built `n2o` and called `n2o.prepare(controller)` -- for `"simulation"`
    that's the point the MuJoCo viewer window opened (Unity connects lazily on its
    own first `drive()` call instead -- see `n2o.robot.simulation.unity.
    UnitySimulator`). Nothing has run yet at that point; this panel's own "실행"
    button is what actually calls `n2o.run(controller)` (a no-op re-`prepare()`,
    then the real read -> decode -> translate -> route cycle loop).

    Positioned next to wherever `ConsoleWindow` was on screen (see
    `ConsoleWindow._position_run_panel()`), not next to the simulation window
    itself -- Qt has no cross-platform handle onto a MuJoCo GLFW window's on-screen
    geometry (mujoco's own viewer opens it directly, outside Qt), and a Unity
    backend's window is a separate, possibly-remote process entirely, so there's
    nothing local to dock beside there either.

    Applies to every controller, not just "simulation" -- a `motor_driver` run also
    stops here for an explicit "실행" click before touching real hardware, since a
    real robot with no confirmation step at all is the riskier default.

    "설정으로 돌아가기" (or the window's own close button -- `closeEvent()` routes
    both through the same path) closes this panel and restores `ConsoleWindow`;
    disabled while a run is actually in flight, since `N2O.run()`'s cycle loop has
    no cancellation hook to close down cleanly mid-run."""

    back_requested = Signal()

    def __init__(self, n2o, controller, config_lines, unity_parts_info):
        super().__init__()
        self.setWindowTitle("N2O 실행")
        self.setWindowFlag(Qt.WindowType.Window)
        self.n2o = n2o
        self.controller = controller
        self._config_lines = config_lines
        # (kind, model, unity_engine) for every part actually driven over a Unity
        # connection this run -- see ConsoleWindow._unity_parts_info(). Covers both
        # the uniform Controller/backend combo (every assigned part, one shared
        # engine) and "개별 선택" (only the parts whose own backend is Unity, each
        # with its own engine choice).
        self._unity_parts_info = unity_parts_info
        self.is_unity = bool(unity_parts_info)
        self._thread = None
        self._worker = None
        self._running = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        summary_box = QGroupBox("현재 설정")
        summary_box.setObjectName("summaryBox")
        summary_layout = QVBoxLayout(summary_box)
        summary_html = "<br>".join(html.escape(line) for line in self._config_lines)
        summary = QLabel(f"<div style='line-height:170%'>{summary_html}</div>")
        summary.setTextFormat(Qt.TextFormat.RichText)
        summary.setWordWrap(True)
        summary_layout.addWidget(summary)
        layout.addWidget(summary_box)

        if self.is_unity:
            layout.addWidget(self._build_unity_guidance_box())

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
        layout.addWidget(self.log, 1)

        self._log_stream = _LogStream()
        self._log_stream.text_written.connect(self._append_log, Qt.QueuedConnection)

        self.back_button = QPushButton("설정으로 돌아가기")
        self.back_button.clicked.connect(self.close)
        layout.addWidget(self.back_button)

        self.resize(400, 480)

    def _build_unity_guidance_box(self) -> QGroupBox:
        """Only added when `is_unity` -- holds one collapsible tip per Unity-backed
        part (`self._unity_parts_info` -- in "개별 선택" mode this can be more than
        one, each with its own engine choice; in uniform Unity-backend mode it's
        every assigned part sharing the one global engine choice) plus a final
        shared tip, all folded shut by default so they don't compete for space
        with the rest of `RunPanel` when the user already knows this and doesn't
        need them open:

        1. One tip per Unity part -- which engine-specific setup that part's run
           expects (see the companion `neural-to-output-unity` repo's own README
           for the actual scripts/steps named here).
        2. How to carry a Scene view's framing over onto the Camera driving the
           Game view (Unity has no built-in shortcut for this beyond
           `GameObject → Align With View`, easy to not know about).

        `QToolButton` (checkable, arrow indicator) is the toggle -- Qt has no
        built-in collapsible group box, and a checkable tool button is the usual
        way to build one by hand. Detail text stays in a `QPlainTextEdit` capped
        at a small `setMaximumHeight()` rather than a taller/uncapped widget when
        expanded -- keeps each section's on-screen footprint small without
        shrinking the font (which would hurt readability); it scrolls internally
        if needed instead."""
        box = QGroupBox("Unity 안내")
        box_layout = QVBoxLayout(box)
        for kind, model, engine in self._unity_parts_info:
            title, detail = self._engine_setup_tip(engine)
            label = model or kind
            box_layout.addWidget(self._build_collapsible_tip(f"{label} -- {title}", detail))
        box_layout.addWidget(
            self._build_collapsible_tip(
                "Scene 뷰를 Game 뷰에 저장하기",
                "- Scene 뷰를 원하는 위치/각도로 맞추세요.\n"
                "- Hierarchy에서 카메라를 선택하세요.\n"
                "- GameObject → Align With View (Ctrl+Shift+F, Mac은 Cmd+Shift+F)를"
                " 누르세요\n"
                "카메라가 방금 본 Scene 뷰의 위치/회전으로 이동해 Game 뷰도 같은"
                " 화면을 보여줍니다.",
            )
        )
        return box

    def _engine_setup_tip(self, engine: str) -> tuple[str, str]:
        """(title, detail text) for one part's collapsible section in
        `_build_unity_guidance_box()`, matching `engine` (one of `UNITY_ENGINES`)
        -- see the companion `neural-to-output-unity` repo's own README for the
        full steps these summarize (this repo ships no Unity project or C# source
        itself)."""
        if engine == "MuJoCo Plugin":
            detail = (
                "- 공식 MuJoCo Unity 플러그인이 설치되어 있어야 합니다"
                " (mujoco.readthedocs.io/en/stable/unity.html).\n"
                "- MJCF 파일(so101_new_calib.xml 또는 robot.xml)을 플러그인으로"
                " 직접 임포트하세요 -- 별도 변환 불필요.\n"
                "- Unity 메뉴에서 Tools → N2O → Add MuJoCo Plugin Bridge를 누르면"
                " GameObject 생성 + MujocoPluginBridge.cs 부착까지 자동으로"
                " 처리됩니다 (neural-to-output-unity 레포의 README 참고 -- 스크립트를"
                " 직접 씬에 끌어다 놓을 필요 없음)."
            )
            return "MuJoCo Plugin 설정 확인", detail
        detail = (
            "- '설정' 팝업의 \"rig.json 재생성\" 버튼으로 rig.json을 먼저 생성하세요"
            " (또는 `python -m n2o.robot.simulation.unity.solver <mjcf 경로> -o"
            " rig.json`).\n"
            "- rig.json과 해당 파츠의 .stl 파일들을 프로젝트에 함께 넣으세요.\n"
            "- Unity 메뉴에서 Tools → N2O → Add Rig Loader (Unity-native PhysX)를"
            " 누르면 방금 넣은 rig.json을 파일 선택창에서 고르는 것만으로 GameObject"
            " 생성 + RigLoader.cs 부착 + rigJsonPath/meshDirectory 지정까지 자동으로"
            " 처리됩니다 (neural-to-output-unity 레포의 README 참고 -- 스크립트를"
            " 직접 씬에 끌어다 놓거나 필드를 손으로 채울 필요 없음)."
        )
        return "Unity Native (PhysX) 설정 확인", detail

    def _build_collapsible_tip(self, title: str, detail_text: str) -> QWidget:
        """One folded-shut-by-default tip section: a checkable `QToolButton`
        toggle (Qt has no built-in collapsible group box) plus a capped-height
        `QPlainTextEdit` detail area -- shared by `_build_unity_guidance_box()`'s
        two sections so neither duplicates this toggle/reveal wiring."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        toggle = QToolButton()
        toggle.setText(title)
        toggle.setCheckable(True)
        toggle.setChecked(False)
        toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toggle.setArrowType(Qt.ArrowType.RightArrow)
        toggle.setStyleSheet("QToolButton { border: none; font-weight: bold; }")

        details = QPlainTextEdit(readOnly=True)
        details.setObjectName("unityGuideBox")
        details.setMaximumHeight(100)
        details.setPlainText(detail_text)
        details.setVisible(False)

        def _on_toggled(checked):
            details.setVisible(checked)
            toggle.setArrowType(
                Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
            )

        toggle.toggled.connect(_on_toggled)

        layout.addWidget(toggle)
        layout.addWidget(details)
        return container

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
        self.run_button.setEnabled(False)
        self.back_button.setEnabled(False)
        self._running = True
        self.log.clear()

        self._thread = QThread()
        self._worker = RunWorker(self.n2o, self.controller)
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

    def _on_run_finished(self):
        sys.stdout = self._restore_stdout
        sys.stderr = self._restore_stderr
        self.run_button.setEnabled(True)
        self.back_button.setEnabled(True)
        self._running = False

    def _on_run_failed(self, exc, tb_text):
        self._append_log(tb_text)
        if self.is_unity and isinstance(exc, ConnectionError):
            # A missed Play press is an expected, recoverable step in the manual
            # Unity workflow, not a bug -- Warning icon + plain retry guidance
            # instead of the generic Critical/traceback dialog (still reachable
            # via this same dialog's own "Show Details.../리포트 저장..." for
            # anything actually unexpected). `str(exc)` -- `UnitySimulator.
            # launch_viewer()`'s own message -- already names the exact host:port
            # it tried, so surfacing it here saves a trip back to the config
            # screen to check what was actually attempted (e.g. it may not match
            # the port a real Unity listener script actually binds to).
            show_error_dialog(
                self,
                "Unity 연결 오류",
                tb_text,
                self._config_lines,
                summary=(
                    f"{exc} Unity 창에서 Play가 눌려 있는지, 엔드포인트(host:port)"
                    " 설정이 이 주소와 실제 Unity 쪽 리스너 포트가 일치하는지"
                    " 확인한 뒤 \"실행\"을 다시 눌러 주세요."
                ),
                icon=QMessageBox.Icon.Warning,
            )
        else:
            show_error_dialog(self, "실행 오류", tb_text, self._config_lines)

    def closeEvent(self, event):
        if self._running:
            QMessageBox.warning(
                self, "실행 중", "실행이 끝난 뒤에 설정 화면으로 돌아갈 수 있습니다."
            )
            event.ignore()
            return
        event.accept()
        self.back_requested.emit()


class ConsoleWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("N2O Console")
        self._run_panel = None
        self._tray_icon = None
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
        title = QLabel("N2O Console")
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

        # Populated below by _build_parts_group()/_add_part_row() -- created here,
        # ahead of the Controller row's widgets, so refresh_part_dependent_ui()
        # (called once immediately after those widgets are wired up) has something
        # to iterate instead of hitting an AttributeError on an empty window.
        self.part_rows = []

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

        # A dropdown (not radio buttons) so this scales to more backends later
        # without the row growing wider -- it already gets the same scrollable popup
        # as every other combo here once the list outgrows the visible area (see
        # QScrollBar styling above).
        self.simulation_backend_combo = QComboBox()
        self.simulation_backend_combo.addItems(SIMULATION_BACKENDS)

        # A second, independent choice from simulation_backend_combo -- once Unity
        # is picked at all, this decides *how* the Unity side actually simulates:
        # the official MuJoCo Unity plugin (real MuJoCo physics in-process inside
        # Unity, loads either MJCF directly, no conversion) or our own
        # ArticulationBody-based rig (built from a JSON descriptor -- see
        # n2o.robot.simulation.unity.solver.ClosedLoopRigSolver). Doesn't change
        # anything UnitySimulator sends -- see _build_n2o()'s Unity branch, which
        # is identical either way -- purely which setup instructions RunPanel
        # shows (see _build_unity_guidance_box()).
        self.unity_engine_combo = QComboBox()
        self.unity_engine_combo.addItems(UNITY_ENGINES)

        # Only meaningful for the Unity backend (MuJoCo needs no address -- it's an
        # in-process physics model, not a separate listener) -- see _build_n2o()'s
        # UnitySimulator wiring.
        self.unity_endpoint_edit = QLineEdit(DEFAULT_UNITY_ENDPOINT)
        self.unity_endpoint_edit.setPlaceholderText("host:port")

        # See _check_unity_connection() -- matches the typed port against whatever
        # Unity actually has open (`ss -ltnp`), auto-correcting/asking when it
        # doesn't match, then does a real TCP connect to confirm. Also doubles as
        # the "recheck" button after pressing Play in Unity -- one button, click
        # again.
        self.unity_check_button = QPushButton("포트 확인")
        self.unity_check_button.clicked.connect(self._check_unity_connection)

        controller_row = QHBoxLayout()
        controller_row.addWidget(self.controller_combo)
        controller_row.addWidget(self.simulation_backend_combo)
        controller_row.addWidget(self.unity_engine_combo)
        controller_row.addWidget(self.unity_endpoint_edit)
        controller_row.addWidget(self.unity_check_button)
        form.addRow("Controller", controller_row)

        self.controller_combo.currentTextChanged.connect(
            lambda _: self.refresh_part_dependent_ui()
        )
        self.simulation_backend_combo.currentTextChanged.connect(
            self._update_simulation_backend_visibility
        )
        # Not refresh_part_dependent_ui() -- there are no part rows yet
        # (_build_parts_group() runs later below), so there's nothing
        # update_part_availability() could do here anyway. The signal
        # connection above covers every later change.
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
            self.unity_engine_combo,
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

        layout.addWidget(self._build_parts_group())

        self.next_button = QPushButton("다음")
        self.next_button.setObjectName("runButton")
        self.next_button.setMinimumHeight(36)
        self.next_button.setToolTip(
            "설정을 확인하고 시뮬레이션 창 + 실행 패널을 엽니다 -- 아직 파이프라인이"
            " 실행되지는 않습니다."
        )
        self.next_button.clicked.connect(self._on_next_clicked)
        layout.addWidget(self.next_button)

        # Absorbs the window's leftover vertical space -- without this, nothing
        # here has an expanding size policy (unlike before, when the log panel
        # lived in this same layout and soaked it up on its own), so Qt stretches
        # the header's title/subtitle QLabels themselves to fill the gap instead,
        # blowing their height out to 4-5x a single text line and visually
        # splitting logo/title/subtitle into three stacked rows.
        layout.addStretch()

    def _is_individual_mode(self) -> bool:
        return self.controller_combo.currentText() == "개별 선택"

    def _is_unity_backend(self) -> bool:
        """Single source of truth for "is the *uniform* Controller/backend selection
        Unity" -- shared by `_update_simulation_backend_visibility()` (which fields
        to show) and `_open_run_panel()` (whether `RunPanel` gets the Unity
        guidance section), so the two checks can't silently drift apart. Only
        meaningful outside "개별 선택" -- see `_any_individual_part_uses_unity()`
        for that mode's equivalent."""
        return (
            self.controller_combo.currentText() == "simulation"
            and self.simulation_backend_combo.currentText() == "Unity"
        )

    def _any_individual_part_uses_unity(self) -> bool:
        """"개별 선택" mode's equivalent of `_is_unity_backend()` -- true if any
        part row's own controller/backend combination resolves to Unity. Used to
        decide whether the shared Unity endpoint field should stay visible, since
        every Unity-backed part shares one `UnitySimulator` connection rather than
        getting its own (see `_build_n2o()`)."""
        return self._is_individual_mode() and any(
            row.controller_combo.currentText() == "simulation"
            and row.sim_backend == "Unity"
            for row in self.part_rows
        )

    def _update_simulation_backend_visibility(self):
        is_individual = self._is_individual_mode()
        is_simulation = self.controller_combo.currentText() == "simulation"
        is_unity = self._is_unity_backend()
        any_individual_unity = self._any_individual_part_uses_unity()

        self.simulation_backend_combo.setVisible(is_simulation)
        self.unity_engine_combo.setVisible(is_unity)
        self.unity_endpoint_edit.setVisible(is_unity or any_individual_unity)
        self.unity_check_button.setVisible(is_unity or any_individual_unity)

        for row in self.part_rows:
            row.controller_combo.setVisible(is_individual)

    def refresh_part_dependent_ui(self):
        """Recomputes every bit of UI whose correct state depends on both the
        window-level Controller and each part row's own settings -- the two are
        entangled enough ("개별 선택" reveals per-row combos, a row's own combo
        then feeds back into which shared fields the window shows) that keeping
        them in two separately-triggered methods drifted out of sync. Called
        whenever either side changes: the window's Controller, a part row's own
        controller/kind, or a part's settings dialog being accepted."""
        self._update_simulation_backend_visibility()
        self.update_part_availability()

    def _check_unity_connection(self):
        """Handler for "포트 확인": a real TCP connect to whatever's currently
        typed in the endpoint field. Success ends here. Failure asks whether Play
        was actually pressed (a "yes" here means the *port itself* is probably
        wrong, not that Unity isn't running yet, so the user gets an extra nudge
        to stop Unity before recovering the port; a "no" skips straight to
        recovery since there's nothing running to stop) and then, either way,
        hands off to `_offer_unity_port_recovery()` for the two ways to fix it."""
        try:
            parsed = self._parse_unity_endpoint()
        except ValueError as exc:
            QMessageBox.warning(self, "엔드포인트 오류", str(exc))
            return
        host, port = parsed["host"], parsed["port"]

        if _tcp_ping(host, port):
            QMessageBox.information(self, "연결 확인", f"{host}:{port}에 연결할 수 있습니다.")
            return

        reply = QMessageBox.question(
            self,
            "Play 확인",
            f"{host}:{port}에 연결하지 못했습니다.\n\nUnity 창에서 Play를 눌러"
            " 실행 중인가요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(
                self,
                "포트 재확인 필요",
                "Play를 눌렀는데도 연결에 실패했다면 포트 번호 자체가 다를 수"
                " 있습니다 -- Unity를 멈춘 뒤, 아래에서 포트를 다시 확인하세요.",
            )
        self._offer_unity_port_recovery(host)

    def _offer_unity_port_recovery(self, host: str):
        """Lets the user pick how to recover the real Unity listener port after
        `_check_unity_connection()` fails: run the guided auto-detect wizard, or
        skip straight to typing in a port they already know (e.g. from Unity's
        own console log, like a `"JointBridgeServer listening on port ..."`
        message)."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("포트 확인 방법")
        box.setText("포트를 어떻게 확인하시겠어요?")
        find_button = box.addButton("포트 찾기", QMessageBox.ButtonRole.ActionRole)
        manual_button = box.addButton("포트 직접 입력", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()

        clicked = box.clickedButton()
        if clicked is find_button:
            self._find_unity_port_wizard(host)
        elif clicked is manual_button:
            self._enter_unity_port_manually(host)

    def _find_unity_port_wizard(self, host: str):
        """Guided auto-detect for the real Unity listener port -- the same
        "unplug it, plug it back in, see what changed" trick USB-port detection
        uses, applied to TCP ports instead: snapshot whatever's listening while
        Unity is stopped, have the user start it, then whatever's newly listening
        afterward is the real port. Robust to Unity Editor's own internal ports
        (profiler, editor messaging, script debugger, ...) without hardcoding any
        of them -- those aren't fixed values across machines/OS/Unity versions,
        but they're already open in *both* snapshots, so they cancel out of the
        diff regardless of what their actual numbers happen to be."""
        reply = QMessageBox.question(
            self,
            "1/2 -- Unity 종료 확인",
            "Unity가 꺼져 있는지 확인한 뒤 계속하세요.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok,
        )
        if reply != QMessageBox.StandardButton.Ok:
            return
        before = set(_find_unity_listening_ports())

        reply = QMessageBox.question(
            self,
            "2/2 -- Unity 시작",
            "이제 Unity에서 프로젝트를 열고 Play를 누른 뒤 계속하세요.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok,
        )
        if reply != QMessageBox.StandardButton.Ok:
            return
        new_ports = [p for p in _find_unity_listening_ports() if p not in before]

        if len(new_ports) == 1:
            port = new_ports[0]
            self.unity_endpoint_edit.setText(f"{host}:{port}")
        elif len(new_ports) > 1:
            choice, ok = QInputDialog.getItem(
                self,
                "포트 선택",
                "Play 이후 새로 열린 포트가 여러 개입니다 -- 소켓 리스너 포트를"
                " 선택하세요:",
                [str(candidate) for candidate in new_ports],
                editable=False,
            )
            if not ok:
                return
            port = int(choice)
            self.unity_endpoint_edit.setText(f"{host}:{port}")
        else:
            QMessageBox.warning(
                self,
                "포트를 찾지 못함",
                "Play 이후 새로 열린 포트를 찾지 못했습니다 -- 리스너 스크립트가"
                " 실제로 시작됐는지 Unity 콘솔을 확인한 뒤 '포트 확인'부터 다시"
                " 시도하세요. (`ss` 명령이 없는 환경이라면 이 자동 확인 자체가"
                " 동작하지 않습니다.)",
            )
            return

        if _tcp_ping(host, port):
            QMessageBox.information(self, "연결 확인", f"{host}:{port}에 연결할 수 있습니다.")
        else:
            QMessageBox.warning(
                self, "연결 실패", f"포트 {port}를 찾았지만 {host}:{port}에 연결하지 못했습니다."
            )

    def _enter_unity_port_manually(self, host: str):
        """For a user who already knows the real port (e.g. saw it printed in
        Unity's own console log) -- skips the stop/start wizard entirely and just
        confirms whatever they type actually answers."""
        default_port = int(DEFAULT_UNITY_ENDPOINT.rsplit(":", 1)[-1])
        port, ok = QInputDialog.getInt(
            self,
            "포트 직접 입력",
            "Unity 리스너 포트 번호를 입력하세요:",
            default_port,
            1,
            65535,
        )
        if not ok:
            return
        self.unity_endpoint_edit.setText(f"{host}:{port}")

        if _tcp_ping(host, port):
            QMessageBox.information(self, "연결 확인", f"{host}:{port}에 연결할 수 있습니다.")
        else:
            QMessageBox.warning(
                self,
                "연결 실패",
                f"{host}:{port}에 연결하지 못했습니다 -- 포트 번호를 다시 확인하거나"
                " Unity 창에서 Play를 눌렀는지 확인하세요.",
            )

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

        return group

    def _add_part_row(self, kind=None):
        row = PartRow(self, kind or PART_KINDS[0])
        row.removed.connect(self._remove_part_row)
        self._parts_list_layout.addWidget(row)
        self.part_rows.append(row)
        self.refresh_part_dependent_ui()

    def _remove_part_row(self, row):
        self.part_rows.remove(row)
        self._parts_list_layout.removeWidget(row)
        row.deleteLater()
        self.refresh_part_dependent_ui()

    def update_part_availability(self):
        """Enables each row's "설정" button whenever it has something real to
        configure: a port (motor_driver), a 부착 대상/rig.json for a simulated
        hand, or (in "개별 선택") its own controller/backend/engine choice --
        see `PartRow._open_settings()` for exactly what each combination shows.
        A simulated arm under the uniform "simulation" Controller has nothing of
        its own to configure (backend/engine are the window's shared combos), so
        it stays disabled there -- unlike "개별 선택", where every row always has
        at least its own controller choice."""
        mode = self.controller_combo.currentText()
        is_individual = mode == "개별 선택"
        for row in self.part_rows:
            kind = row.kind_combo.currentText()
            has_settings = (
                is_individual
                or mode == "motor_driver"
                or (mode == "simulation" and kind == "hand")
            )
            row.settings_button.setEnabled(has_settings)

    def _has_amazing_hand(self) -> bool:
        return any(row.model_combo.currentText() == "AmazingHand" for row in self.part_rows)

    def _on_next_clicked(self):
        if not self.part_rows:
            QMessageBox.warning(
                self, "설정 필요", "파츠를 최소 하나는 추가해야 합니다."
            )
            return

        if (
            not self._is_individual_mode()
            and self._is_unity_backend()
            and self._has_amazing_hand()
        ):
            # AmazingHand's closed-loop (ball-joint) mechanism is bridged into
            # Unity-native PhysX via a technique that's only confirmed *possible*
            # from Unity's/Isaac Sim's own docs, not yet confirmed *stable* by
            # anyone actually running it -- see DECISIONS.md. A heads-up, not a
            # block: the user can still proceed once acknowledged.
            QMessageBox.warning(
                self,
                "폐쇄 루프 안정성 주의",
                "AmazingHand는 닫힌 링크(폐쇄 루프) 구조라 Unity 쪽 안정성이 아직"
                " 완전히 검증되지 않았습니다 (자세한 내용은 neural-to-output-unity"
                " 레포의 README 참고). Unity Native (PhysX) 엔진을 쓴다면 rig.json이"
                " 최신 상태인지도 확인하세요.",
            )

        try:
            n2o, controller = self._build_n2o()
            n2o.prepare(controller)
        except Exception:  # noqa: BLE001 -- shown in a dialog instead of crashing the GUI
            show_error_dialog(
                self, "설정 오류", traceback.format_exc(), self._config_summary_lines()
            )
            return

        self._open_run_panel(n2o, controller)

    def _build_n2o(self):
        n2o = N2O()
        n2o.signal = DatasetLoader(name=self.signal_combo.currentText())
        n2o.decoder = DECODERS[self.decoder_combo.currentText()]()
        n2o.command = COMMANDS[self.command_combo.currentText()]()
        # A hand row's own "부착 대상" (PartRow._open_settings()), not a
        # window-level checkbox -- only one hand row can ever exist (duplicate
        # kinds are rejected below), so "any" here just reads that one row's
        # choice without assuming which index it's at.
        n2o.robot.attach_hand_to_arm = any(
            row.kind_combo.currentText() == "hand" and row.attach_to == "arm"
            for row in self.part_rows
        )

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

        if self._is_individual_mode():
            controller = self._apply_individual_controllers(n2o)
        else:
            controller = self.controller_combo.currentText()
            if self._is_unity_backend():
                sim_parts = [
                    p for p in ("arm", "hand") if getattr(n2o.robot, p) is not None
                ]
                if sim_parts:
                    n2o.robot.simulator = UnitySimulator(
                        sim_parts,
                        attach_hand_to_arm=n2o.robot.attach_hand_to_arm,
                        **self._parse_unity_endpoint(),
                    )
        return n2o, controller

    def _apply_individual_controllers(self, n2o) -> str:
        """"개별 선택" mode's own build step -- writes `n2o.robot.part_controllers`
        for every part, then assigns one shared `Simulator` (for every part using
        the MuJoCo backend) and/or one shared `UnitySimulator` (for every part
        using Unity) into `n2o.robot.part_simulators` -- see `Robot.
        part_controllers`/`part_simulators`. A part's own controller/backend/engine
        selections are never mixed into one simulator across different backends --
        arm+hand both on Unity share one `UnitySimulator`; arm+hand on different
        backends each land in their own.

        Returns the fallback controller string for `n2o.prepare()`/`RunPanel`:
        `"simulation"` (so `prepare()`'s already-covered-parts check still runs
        and the MuJoCo branch's `launch_viewer()` fires for parts not already
        pre-assigned above) if any part simulates, else `"motor_driver"`."""
        mujoco_parts, unity_parts = [], []
        for row in self.part_rows:
            kind = row.kind_combo.currentText()
            own_controller = row.controller_combo.currentText()
            n2o.robot.part_controllers[kind] = ControllerType(own_controller)
            if own_controller == "simulation":
                (unity_parts if row.sim_backend == "Unity" else mujoco_parts).append(kind)

        if mujoco_parts:
            sim = Simulator(mujoco_parts, attach_hand_to_arm=n2o.robot.attach_hand_to_arm)
            for part in mujoco_parts:
                n2o.robot.part_simulators[part] = sim
            sim.launch_viewer()
        if unity_parts:
            usim = UnitySimulator(
                unity_parts,
                attach_hand_to_arm=n2o.robot.attach_hand_to_arm,
                **self._parse_unity_endpoint(),
            )
            for part in unity_parts:
                n2o.robot.part_simulators[part] = usim

        return "simulation" if (mujoco_parts or unity_parts) else "motor_driver"

    def _resolve_rig_target(self, row):
        """`(mjcf_path, attach, default_json_path)` for `row`'s current
        settings -- the single source of truth shared by `regenerate_rig_json()`
        (what to actually generate) and `PartRow._open_settings()`'s rig.json
        status label (what to check against), so the two can never disagree
        about what file a given row's button would produce.

        A hand row with `attach_to == "arm"` (and a compatible arm row actually
        present -- see `PartRow._open_settings()`'s own `_attach_compatible()`)
        resolves to the *arm's* MJCF as the base, with the hand merged onto it
        via `attach=` (see `ClosedLoopRigSolver.__init__`) -- one combined
        rig.json instead of two separate ones. Returns `(None, None, None)` if
        `row`'s model has no bundled MJCF at all (`model not in MJCF_PATHS`)."""
        model = row.model_combo.currentText()
        mjcf_path = MJCF_PATHS.get(model)
        if mjcf_path is None:
            return None, None, None

        attach = None
        if row.kind_combo.currentText() == "hand" and row.attach_to == "arm":
            arm_row = next(
                (r for r in self.part_rows if r.kind_combo.currentText() == "arm"), None
            )
            arm_model = arm_row.model_combo.currentText() if arm_row is not None else None
            arm_mjcf = MJCF_PATHS.get(arm_model)
            if arm_mjcf is not None:
                attach = (mjcf_path, ARM_GRIPPER_SITE, HAND_PREFIX)
                mjcf_path = arm_mjcf

        default_json_path = (
            mjcf_path.with_suffix(".json")
            if attach is None
            else mjcf_path.with_name(f"{mjcf_path.stem}_with_hand.json")
        )
        return mjcf_path, attach, default_json_path

    def regenerate_rig_json(self, parent, row):
        """Handler for a part settings dialog's "rig.json 재생성" button -- runs
        `ClosedLoopRigSolver` in-process (it already returns a plain JSON-
        serializable dict, see `solve()`) instead of shelling out to `python -m
        n2o.robot.simulation.unity.solver`, the CLI equivalent this replaces.
        Generates one *combined* arm+hand rig.json instead of a hand-only one
        when `row` (a hand row) is attached to a compatible arm row -- see
        `_resolve_rig_target()`."""
        mjcf_path, attach, default_json_path = self._resolve_rig_target(row)
        if mjcf_path is None:
            return
        save_path, _ = QFileDialog.getSaveFileName(
            parent, "rig.json 저장", str(default_json_path), "JSON files (*.json)"
        )
        if not save_path:
            return
        try:
            rig = ClosedLoopRigSolver(mjcf_path, attach=attach).solve()
            Path(save_path).write_text(json.dumps(rig, indent=2), encoding="utf-8")
        except Exception:  # noqa: BLE001 -- shown in a dialog instead of crashing the GUI
            show_error_dialog(
                parent,
                "rig.json 생성 오류",
                traceback.format_exc(),
                self._config_summary_lines(),
            )
            return
        QMessageBox.information(parent, "생성됨", f"{save_path}에 저장했습니다.")

    def _parse_unity_endpoint(self):
        endpoint = self.unity_endpoint_edit.text().strip()
        host, _, port = endpoint.rpartition(":")
        if not host or not port.isdigit():
            raise ValueError(
                f"Unity 엔드포인트 형식이 올바르지 않습니다: {endpoint!r} -- 'host:port' 형식으로 입력하세요."
            )
        return {"host": host, "port": int(port)}

    def _config_summary_lines(self):
        lines = [
            f"- Signal: {self.signal_combo.currentText()}",
            f"- Decoder: {self.decoder_combo.currentText()}",
            f"- Command: {self.command_combo.currentText()}",
            f"- Controller: {self.controller_combo.currentText()}",
        ]
        if self._is_individual_mode():
            for row in self.part_rows:
                kind = row.kind_combo.currentText()
                own = row.controller_combo.currentText()
                detail = own
                if own == "simulation":
                    detail += f" / {row.sim_backend}"
                    if row.sim_backend == "Unity":
                        detail += (
                            f" / {row.unity_engine} / {self.unity_endpoint_edit.text()}"
                        )
                lines.append(f"  - {kind}: {detail}")
        elif self.controller_combo.currentText() == "simulation":
            lines.append(
                f"- Simulation backend: {self.simulation_backend_combo.currentText()}"
            )
            if self.simulation_backend_combo.currentText() == "Unity":
                lines.append(f"- Unity engine: {self.unity_engine_combo.currentText()}")
                lines.append(f"- Unity endpoint: {self.unity_endpoint_edit.text()}")
        lines.append(
            "- Parts: "
            + (
                ", ".join(
                    f"{row.kind_combo.currentText()}/{row.model_combo.currentText() or '없음'}"
                    for row in self.part_rows
                )
                or "(없음)"
            )
        )
        return lines

    def _unity_parts_info(self):
        """`(kind, model, unity_engine)` for every part that will actually be
        driven over a Unity connection -- shared by `_open_run_panel()` (which
        parts' setup steps `RunPanel`'s guidance box should name) whether that
        came from the uniform Controller/backend combo or from "개별 선택"'s own
        per-row choices."""
        if self._is_individual_mode():
            return [
                (row.kind_combo.currentText(), row.model_combo.currentText(), row.unity_engine)
                for row in self.part_rows
                if row.controller_combo.currentText() == "simulation"
                and row.sim_backend == "Unity"
            ]
        if self._is_unity_backend():
            engine = self.unity_engine_combo.currentText()
            return [
                (row.kind_combo.currentText(), row.model_combo.currentText(), engine)
                for row in self.part_rows
            ]
        return []

    def _open_run_panel(self, n2o, controller):
        self._run_panel = RunPanel(
            n2o,
            controller,
            self._config_summary_lines(),
            self._unity_parts_info(),
        )
        self._run_panel.back_requested.connect(self._on_run_panel_closed)
        self._position_run_panel(self._run_panel)
        self._run_panel.show()
        self._enter_background_mode()

    def _position_run_panel(self, panel):
        """Best-effort "next to" placement -- see `RunPanel`'s own docstring for why
        this is next to where `ConsoleWindow` was, not next to the actual simulation
        window (Qt has no handle onto that window's geometry at all)."""
        console_geo = self.frameGeometry()
        x = console_geo.right() + 16
        y = console_geo.top()
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            x = min(x, available.right() - panel.width())
            y = max(available.top(), min(y, available.bottom() - panel.height()))
        panel.move(x, y)

    def _enter_background_mode(self):
        """Get `ConsoleWindow` out of the way once `RunPanel` is open -- a tray icon
        by default (single, stable icon regardless of how many simulation/Unity
        windows pile up on the taskbar), falling back to a plain taskbar-minimize
        wherever the desktop environment doesn't actually support a tray (e.g.
        GNOME without a tray extension -- `isSystemTrayAvailable()` catches that at
        runtime instead of assuming Linux desktops all behave the same)."""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._ensure_tray_icon()
            self._tray_icon.show()
            self.hide()
        else:
            self.showMinimized()

    def _ensure_tray_icon(self):
        if self._tray_icon is not None:
            return
        self._tray_icon = QSystemTrayIcon(QIcon(ICON_PATH), self)
        self._tray_icon.setToolTip("N2O Console")
        menu = QMenu()
        open_action = menu.addAction("설정 창 열기")
        open_action.triggered.connect(self._restore_from_background)
        quit_action = menu.addAction("종료")
        quit_action.triggered.connect(QApplication.instance().quit)
        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._restore_from_background()

    def _restore_from_background(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if self._tray_icon is not None:
            self._tray_icon.hide()

    def _on_run_panel_closed(self):
        self._run_panel = None
        self._restore_from_background()

    def closeEvent(self, event):
        """Closing the window's own titlebar/×  while a `RunPanel` session is still
        open must not fall through to Qt's default close -- that would destroy this
        `QMainWindow` outright (not just hide it), permanently orphaning the still-
        open `RunPanel` with no way to bring the config window back. Route back
        through `_enter_background_mode()` instead (tray icon or minimize,
        whichever this desktop supports), the same place restoring-then-closing
        again would otherwise dead-end.

        No `RunPanel` open -- e.g. before ever clicking "다음", or after "설정으로
        돌아가기" -- means × is the only remaining way to quit, and it's the exact
        same button that, moments earlier (while a `RunPanel` was open), just meant
        "go to background" instead. Asking for confirmation here is specifically
        to catch that muscle-memory click landing on the wrong meaning, not a
        general "are you sure" for every close."""
        if self._run_panel is not None:
            event.ignore()
            self._enter_background_mode()
            return

        reply = QMessageBox.question(
            self,
            "종료 확인",
            "N2O Console을 종료하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(ICON_PATH))
    app.setStyleSheet(_build_stylesheet(_DARK if _is_dark_mode() else _LIGHT))
    window = ConsoleWindow()
    window.resize(720, 720)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

# Apps

Desktop GUI applications built on top of `n2o` — kept separate from
[`demos/`](../demos/README.md)'s scripts so UI-only dependencies (PySide6) don't leak
into the plain-script dependency set.

- `quickstart_ui.py` — a PySide6 desktop UI over the same signal → decoder → command →
  robot wiring [`demos/quickstart.py`](../demos/quickstart.py) wires by hand: pick a
  dataset, decoder, and command from dropdowns, add robot parts, then run. Needs its own
  `app` dependency group (`uv sync --group app`) since it adds PySide6 on top of
  `demos`' own ML/robot stack. Run with:

  ```bash
  uv run --group app python apps/quickstart_ui.py
  ```

  `quickstart-ui.desktop` launches the same command from a Linux app menu — copy or
  symlink it into `~/.local/share/applications/` to add it there:

  ```bash
  ln -s "$(pwd)/apps/quickstart-ui.desktop" ~/.local/share/applications/n2o-quickstart-ui.desktop
  ```

  Robot parts are a dynamic list (the 파츠 group) rather than fixed arm/hand rows —
  "+ 파츠 추가" adds a row, each row picks a kind (`arm`/`hand`/`leg`) then a model
  (e.g. `AmazingHand` for kind `hand`) and can be removed again. Only `arm`/`hand` are
  actually backed by an `n2o.robot` class today (`SO101Arm`/`AmazingHand`); `leg` has no
  `n2o.robot.leg` package yet, so running with one selected shows a clear "not
  supported yet" message instead of silently doing nothing. A `leg` row also locks
  (kind/model/설정 all disabled, only × stays clickable) once Controller is
  `motor_driver` instead of falling back to another kind — a real leg controller needs
  torque control + sensor fusion for actual walking, not a lookup-table gesture like
  arm/hand's, so it's disabled rather than silently switched to something else out from
  under you; switching back to `simulation` unlocks it again, since MuJoCo already has
  a working leg model to simulate against (MyoSuite's myoOSL). A part row's "설정"
  button only enables once Controller is `motor_driver` (and the row isn't
  leg-locked) — port only matters against real hardware, not simulation — and opens a
  small dialog to set its port; that's the only setting it has for now.

  Controller `simulation` additionally shows a backend dropdown (MuJoCo/Unity) next to
  it — only MuJoCo is actually wired up (`n2o.robot.simulation`); Unity is a second
  backend still in progress, and running with it selected shows the same kind of "not
  supported yet" message instead of silently falling back to MuJoCo.

  Fields with an amber left border (Decoder, Command, the 파츠 group, ...) are
  required to run; Controller always has a safe default so it isn't marked.

  Any error dialog (설정 오류/실행 오류) has a "리포트 저장..." button that writes a
  `.txt` file bundling the traceback with what a developer would actually need to
  reproduce it — OS/Python/PySide6/neural-to-output versions and the current
  Signal/Decoder/Command/Controller/Parts selections — since "it errored!" alone isn't
  enough to fix anything.

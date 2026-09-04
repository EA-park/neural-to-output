# Apps

Desktop GUI applications built on top of `n2o` — kept separate from
[`demos/`](../demos/README.md)'s scripts so UI-only dependencies (PySide6) don't leak
into the plain-script dependency set.

- `console.py` — a PySide6 desktop console over the same signal → decoder → command →
  robot wiring [`demos/quickstart.py`](../demos/quickstart.py) wires by hand: pick a
  dataset, decoder, and command from dropdowns, add robot parts, then run. Needs its own
  `app` dependency group (`uv sync --group app`) since it adds PySide6 on top of
  `demos`' own ML/robot stack. Run with:

  ```bash
  uv run --group app python apps/console.py
  ```

  `console.desktop` launches the same command from a Linux app menu — copy or
  symlink it into `~/.local/share/applications/` to add it there:

  ```bash
  ln -s "$(pwd)/apps/console.desktop" ~/.local/share/applications/n2o-console.desktop
  ```

  Two windows, two steps — clicking "다음" doesn't run anything yet:

  1. **Configure** (`ConsoleWindow`) — pick Signal/Decoder/Command/Controller and add
     robot parts, same as before. Its "다음" button builds the `N2O` instance and calls
     `n2o.prepare(controller)` — for Controller `simulation` this is the point the
     MuJoCo viewer window actually opens (Unity has no local window to open here; it
     connects lazily on the first real move instead). Nothing has run yet — no signal
     has been read, nothing has moved.
  2. **Run** (`RunPanel`) — a small window that opens next to where the config window
     was (Qt has no way to query the MuJoCo/Unity window's own on-screen position, so
     this is the closest available approximation of "next to the simulation window").
     Its own "실행" button is what actually drives the pipeline (`n2o.run(controller)`);
     "설정으로 돌아가기" (or the window's own close button) goes back to the config
     window — disabled while a run is in flight, since there's no way to cancel one
     mid-cycle. This confirm-before-running step applies to `motor_driver` too, not
     just `simulation` — driving real hardware with no explicit "are you sure" click
     is the riskier default.

  Once `RunPanel` opens, `ConsoleWindow` gets out of the way — a system tray icon by
  default (click it, or its "설정 창 열기" menu entry, to bring the config window back;
  "종료" quits the whole app), falling back to a plain taskbar-minimize on a desktop
  that doesn't actually support a tray icon (checked at runtime via
  `QSystemTrayIcon.isSystemTrayAvailable()` — e.g. GNOME without a tray extension).

  Robot parts are a dynamic list (the 파츠 group) rather than fixed arm/hand rows —
  "+ 파츠 추가" adds a row, each row picks a kind (`arm`/`hand`) then a model (e.g.
  `AmazingHand` for kind `hand`) and can be removed again. A part row's "설정" button
  only enables once Controller is `motor_driver` — port only matters against real
  hardware, not simulation — and opens a small dialog to set its port; that's the
  only setting it has for now.

  Controller `simulation` additionally shows a backend dropdown (MuJoCo/Unity) next to
  it. MuJoCo is `n2o.run()`'s own default, needing no further config. Unity means the
  UI assigns an `n2o.robot.simulation.unity.UnitySimulator` onto
  `n2o.robot.simulator` itself before running (`n2o.run()`/`n2o.prepare()` only
  auto-build the MuJoCo one when nothing is already assigned there) — picking it
  reveals a "host:port" field (엔드포인트, default `127.0.0.1:9999`) for the separate
  Unity process expected to be listening there, plus a "포트 확인" button next to it.
  Unity is always a process you start and control yourself (no auto-launch option --
  open your Unity project and press Play before using either button here); `UnitySimulator`
  always uses its library default `connect_retries=0` (fail on the first connection
  refusal, no retry grace period).

  "포트 확인" does a real TCP connect to whatever's currently typed in 엔드포인트.
  Success ends there. On failure it asks whether Play is actually pressed: answering
  "예" means the *port itself* is probably wrong (not that Unity isn't running), so it
  adds a nudge to stop Unity first; answering "아니오" skips straight past that since
  there's nothing running yet to stop. Either way it lands on the same choice of two
  recovery buttons:

  - **"포트 찾기"** -- a guided auto-detect, the same "unplug it, plug it back in, see
    what changed" trick USB-port detection uses, applied to TCP ports: confirms Unity
    is stopped and snapshots whatever `ss -ltnp` sees as a baseline, then has you start
    Unity and press Play, then diffs a fresh scan against that baseline so only the
    port that's newly listening counts as a candidate — auto-filling it into 엔드포인트
    (or asking you to pick, if more than one new port shows up) and TCP-pinging it to
    confirm. This never hardcodes Unity Editor's own internal ports (profiler, editor
    messaging, script debugger, ...); they're already open in both snapshots and cancel
    out of the diff regardless of what their actual numbers are on your machine.
  - **"포트 직접 입력"** -- for when you already know the real port (e.g. you saw it
    printed in Unity's own console log, like a `"... listening on port ..."` message)
    — skips the wizard, just asks for the number, fills it into 엔드포인트, and
    TCP-pings it to confirm.

  `RunPanel` shows an extra "Unity 안내" box for Unity-backend runs: a short reminder
  to press Play in the Unity window before clicking "실행", plus a small scrollable
  tips panel on Unity's own Scene/Game view controls (orbit/pan/zoom, Scene vs Game)
  -- capped to a small on-screen height so it doesn't dominate the panel, without
  shrinking its font to do so.

  Unlike MuJoCo (a bundled reference model this repo ships and loads directly), the
  Unity side is a real Unity Editor project this repo doesn't ship at all -- building
  and wiring it (scene, `ProjectSettings/`, socket-listener script) is on whoever uses
  the Unity backend, following the wire protocol documented in
  `src/n2o/robot/simulation/unity/unity_simulator.py`'s own docstring. Each part's own
  3D model is still owned here as a local Unity package rather than a copy:
  `src/n2o/robot/arm/so101/unity_model/` and
  `src/n2o/robot/hand/amazing_hand_right/unity_model/`, the Unity-side counterparts to
  those same folders' `mjcf/` (mirrors `Simulator._build_model()` loading `mjcf/`
  directly instead of a copy under `simulation/`) -- see each folder's own `README.md`
  for exactly what's missing before either is a real, importable package. Neither is
  Python, so neither ships in the `n2o` PyPI package (`pyproject.toml`'s
  `[tool.uv.build-backend]` `source-exclude`/`wheel-exclude` keeps them out) — a
  `pip install`-only user still gets the plain-Python `UnitySimulator` client, just not
  a model to point a Unity project at. A real, working SO-101 bridge project
  (URDF-Importer + `ArticulationBody` joints, socket listener, headless build script)
  exists outside this repo as a validation of the wire protocol.

  Fields with an amber left border (Decoder, Command, the 파츠 group, ...) are
  required to run; Controller always has a safe default so it isn't marked.

  Any error dialog (설정 오류/실행 오류) has a "리포트 저장..." button that writes a
  `.txt` file bundling the traceback with what a developer would actually need to
  reproduce it — OS/Python/PySide6/neural-to-output versions and the current
  Signal/Decoder/Command/Controller/Parts selections — since "it errored!" alone isn't
  enough to fix anything. One exception: a Unity-backend run that fails to connect
  gets a friendlier Warning-icon dialog telling you to check Play and retry instead
  of the generic Critical one — the traceback and "리포트 저장..." are still there
  behind "Show Details...", just not front-and-center for what's usually a missed
  Play press rather than an actual bug.

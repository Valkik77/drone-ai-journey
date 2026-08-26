# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A 20-day self-directed learning project building a "vision perception → AI decision → physical reaction" drone control pipeline from scratch, documented day-by-day in `README.md`. Week 1 (Day1-7): OpenCV color tracking. Week 2 (Day8-14): YOLOv8 object detection. Week 3 (Day15-19): PyBullet physics simulation, closed-loop integration of YOLO detection driving simulated drone forces. Beyond the original 20-day scope, `day20_phone_control_server.py` + `drone_control_app/` add a Flutter phone app that manually joystick-controls the same PyBullet simulation over WebSocket, as a separate path from the YOLO auto-tracking pipeline.

## Python environments — there are two, and they are not interchangeable

- **`venv/`** (root, Python 3.12.9): has `opencv-python`, `ultralytics`/`torch`, `numpy`, `matplotlib`. Used for Day1-14 scripts (color tracking, motion detection, YOLO detection) — no `pybullet`, no `websockets`.
  - Activate: `.\venv\Scripts\Activate.ps1`
- **Miniconda env `drone_sim`** (`C:\Users\USER\miniconda3\envs\drone_sim`, Python 3.10.20): same stack plus `pybullet` and `websockets`. Required for any Day15+ script and `day20_phone_control_server.py`, because `pybullet` fails to build from source on this machine's Python 3.12 (see README Day15 notes).
  - Activate: `conda activate drone_sim`, or call the interpreter directly: `C:\Users\USER\miniconda3\envs\drone_sim\python.exe <script>.py`
- No `requirements.txt` — dependencies were installed ad hoc into whichever env a given day needed (`pip install opencv-python numpy`, etc.). Check which packages a script imports before assuming an env has them.
- Every PyBullet-using script sets `os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"` before importing cv2/pybullet to avoid an OpenMP library conflict between YOLO and PyBullet — keep this when editing those scripts.
- PyBullet must connect with `p.connect(p.DIRECT)`, not `p.GUI` — the GUI mode's realtime renderer is incompatible with this machine's Intel Iris Xe iGPU and silently kills the physics server thread. Simulation state is instead verified via matplotlib plots saved to PNG (see `dayN_*_result.png` outputs) or, for `day20_phone_control_server.py`, streamed out as telemetry.

## Running the Day-numbered scripts

Each `dayN_*.py` at the repo root is a standalone script (`python dayN_xxx.py`), not a library — see Architecture below. Scripts that read a webcam use `cv2.VideoCapture(0)` (default device index) and open a `cv2.imshow` window; quit with `q`. PyBullet scripts run headless and write plots/CSVs on completion (e.g. `day19_enhanced_search_v2.py` writes `day19_debug_log.csv`, `day19_enhanced_result.png`, `day19_raw_position_result.png`).

## Phone control app (day20_phone_control_server.py + drone_control_app/)

1. Start the server (needs the `drone_sim` env): `C:\Users\USER\miniconda3\envs\drone_sim\python.exe day20_phone_control_server.py` — prints the LAN IP to connect to, listens on port 8765.
2. Run the Flutter app from `drone_control_app/`:
   - `flutter pub get` — install dependencies
   - `flutter analyze` — static analysis
   - `flutter test` — widget tests (`test/widget_test.dart`)
   - `flutter run -d chrome` / `-d windows` / on a physical device — enter the server's IP:port in the app's connection field (phone and PC must be on the same Wi-Fi; the server's port may need a Windows Firewall inbound rule for real-device testing)
   - `flutter pub add <package>` to add a dependency (resolves the correct version instead of hand-editing `pubspec.yaml`)

## Architecture

### Day-numbered scripts are snapshots, not a shared library

Scripts do not import from each other. Logic (e.g. `get_direction()`, `direction_to_force()`, YOLO candidate selection) is copy-forwarded and evolved from one day's file into the next rather than refactored into a shared module. When fixing a bug or changing behavior, edit the specific `dayN_*.py` file actually being used/run — do not assume changing an earlier day's version affects a later one, and do not assume there is a common module to change once.

### Perception → decision → physics pipeline (Day17/Day19)

The core loop in `day19_enhanced_search_v2.py` (the most complete integration) is:
1. YOLO detects objects in the webcam frame → `detect_candidates()` filters by class/confidence, computes each candidate's pixel offset from frame center.
2. `select_target()` picks one candidate by `(CLASS_PRIORITY, distance_to_center)`.
3. Offsets are smoothed via a moving average (`deque`) before `get_direction()` turns them into direction commands (`UP`/`DOWN`/`LEFT`/`RIGHT`/`STAY`), using a pixel-distance deadzone/threshold.
4. `direction_to_force()` converts direction commands to `(fx, fy)`; when no target is found, `search_pattern()` generates a sinusoidal sweep instead.
5. `p.applyExternalForce(droneId, -1, [fx, fy, hover_force], ...)` + `p.stepSimulation()` applies it in PyBullet, where `hover_force = mass * 9.8` keeps the sphere aloft.
6. Position history and per-frame decision data are logged to CSV/plots for offline verification, since PyBullet runs in `DIRECT` mode with no live view.

### Manual phone-control path (parallel to, not integrated with, the pipeline above)

`day20_phone_control_server.py` runs its own PyBullet `DIRECT` simulation and an `asyncio`/`websockets` server; it does not touch the webcam or YOLO. Per-connection handling (`handle_client`) runs a receive loop and a telemetry-send loop concurrently via `asyncio.gather`. Protocol is plain JSON over WebSocket:
- Client → server: `{"x": -1..1, "y": -1..1}` (joystick vector), sent on a throttled timer from the app, not on every touch event.
- Server → client: `{"x", "y", "z", "fx", "fy"}` telemetry, sent on a fixed interval independent of the sim step rate.
- A failsafe (`FAILSAFE_TIMEOUT`) zeroes applied force if no control message arrives in time, so a dropped connection doesn't leave the drone drifting indefinitely.

`drone_control_app/lib/` structure: `main.dart` (entry/theme) → `screens/control_screen.dart` (owns connection state, the joystick-send `Timer.periodic`, and composes the other widgets) → `services/drone_socket_service.dart` (wraps `WebSocketChannel`, exposes `ConnectionStatus`/`Telemetry` via `ValueNotifier`) and `widgets/joystick.dart` + `widgets/position_radar.dart` (pure presentation; the radar's axis convention — up/positive-Y is "forward" — mirrors `direction_to_force()`'s UP handling in the Python pipeline, so the two stay visually consistent even though they don't share code).

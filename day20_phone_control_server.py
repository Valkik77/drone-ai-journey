import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # 跟day19一樣,避免YOLO跟PyBullet之間的OpenMP函式庫衝突

import asyncio
import base64
import json
import socket
import threading
import time

import cv2
import pybullet as p
import pybullet_data
import websockets
from ultralytics import YOLO

HOST = "0.0.0.0"
PORT = 8765
HORIZONTAL_FORCE = 45.0  # 提高一點,抵銷下面阻尼帶來的減速,實際移動幅度才感覺得出來
DRAG_COEFFICIENT = 30.0  # 水平方向阻尼(模擬空氣阻力/飛控主動煞車):放開搖桿後速度約1-2秒內衰減到接近0,不會無限漂移
FAILSAFE_TIMEOUT = 0.5  # 秒:超過這麼久沒收到搖桿訊息就歸零施力,避免斷線後持續漂移
SIM_DT = 1 / 50
TELEMETRY_INTERVAL = 1 / 15

CAMERA_INDEX = 0
CAMERA_FPS_TARGET = 8  # 攝影機執行緒的擷取+YOLO推論節奏,跟模擬迴圈分開,不會互相拖慢
FRAME_SEND_INTERVAL = 1 / 6  # 傳給手機的畫面更新頻率,比擷取頻率低一點,省頻寬
FRAME_RESIZE_WIDTH = 480
JPEG_QUALITY = 60

# 跟day19_enhanced_search_v2.py同一套篩選邏輯(這裡直接複製一份,不共用模組,
# 理由見CLAUDE.md「Day腳本是逐日快照」那段):只畫關心的類別,並用框面積/長寬比
# 濾掉太小或明顯不合理的偵測(例如手/局部肢體被誤判成person),畫面才不會太雜訊
TARGET_CLASSES = {"person", "bottle", "cell phone"}
CONFIDENCE_THRESHOLD = 0.4
MIN_BOX_AREA_RATIO = 0.01
PERSON_MIN_HEIGHT_WIDTH_RATIO = 0.5  # 原0.9太嚴:實測坐姿露出頭肩上半身的正常框h/w約0.76,會被誤濾掉

# ---------- 目前搖桿狀態(所有連線共用同一台模擬無人機) ----------
joystick_state = {"x": 0.0, "y": 0.0, "last_update": 0.0}

# ---------- 攝影機畫面(獨立執行緒更新,只是測試時的參考畫面,不會隨模擬位置移動) ----------
camera_state = {"jpeg_b64": None}


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def annotate_frame(frame, model):
    results = model(frame, imgsz=320, verbose=False)
    frame_h, frame_w = frame.shape[:2]
    frame_area = frame_w * frame_h
    annotated = frame.copy()

    for box in results[0].boxes:
        confidence = float(box.conf[0])
        if confidence < CONFIDENCE_THRESHOLD:
            continue
        class_name = model.names[int(box.cls[0])]
        if class_name not in TARGET_CLASSES:
            continue

        x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
        box_w, box_h = x2 - x1, y2 - y1
        if box_w <= 0 or box_h <= 0:
            continue
        if (box_w * box_h) / frame_area < MIN_BOX_AREA_RATIO:
            continue
        if class_name == "person" and (box_h / box_w) < PERSON_MIN_HEIGHT_WIDTH_RATIO:
            continue

        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            annotated, f"{class_name} {confidence:.2f}", (x1, max(0, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
        )

    return annotated


def camera_worker():
    """獨立執行緒:擷取webcam畫面+YOLO偵測,不佔用asyncio事件迴圈,
    避免拖慢PyBullet即時控制迴圈的節奏。純粹是測試參考畫面,
    鏡頭本身沒有裝在無人機上,不會隨模擬位置移動。"""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("找不到可用的攝影機,跳過影像串流(App裡就只會有telemetry,沒有畫面)", flush=True)
        return

    model = YOLO("yolov8s.pt")  # 從yolov8n升級,準確度較高但推論變慢,day20只需要8FPS左右,速度綽綽有餘
    print("攝影機串流已啟動", flush=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        annotated = annotate_frame(frame, model)

        h, w = annotated.shape[:2]
        if w > FRAME_RESIZE_WIDTH:
            scale = FRAME_RESIZE_WIDTH / w
            annotated = cv2.resize(annotated, (FRAME_RESIZE_WIDTH, int(h * scale)))

        cx, cy = annotated.shape[1] // 2, annotated.shape[0] // 2
        cv2.line(annotated, (cx - 15, cy), (cx + 15, cy), (255, 255, 255), 1)
        cv2.line(annotated, (cx, cy - 15), (cx, cy + 15), (255, 255, 255), 1)

        ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        if ok:
            camera_state["jpeg_b64"] = base64.b64encode(buf).decode("ascii")

        time.sleep(1 / CAMERA_FPS_TARGET)


def init_simulation():
    physics_client = p.connect(p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setTimeStep(SIM_DT)  # 沒設的話stepSimulation()預設固定用1/240s,跟迴圈的實際節奏(SIM_DT)對不上,模擬就會用「慢動作」在跑
    p.setGravity(0, 0, -9.8)
    p.loadURDF("plane.urdf")
    drone_id = p.loadURDF("sphere2.urdf", [0, 0, 1], p.getQuaternionFromEuler([0, 0, 0]))
    mass = p.getDynamicsInfo(drone_id, -1)[0]
    hover_force = mass * 9.8
    return physics_client, drone_id, hover_force


async def sim_loop(drone_id, hover_force, get_telemetry_ref):
    while True:
        now = time.time()
        if now - joystick_state["last_update"] > FAILSAFE_TIMEOUT:
            input_x, input_y = 0.0, 0.0
        else:
            input_x = joystick_state["x"]
            input_y = joystick_state["y"]

        (vx, vy, _), _ = p.getBaseVelocity(drone_id)
        fx = input_x * HORIZONTAL_FORCE - DRAG_COEFFICIENT * vx
        fy = input_y * HORIZONTAL_FORCE - DRAG_COEFFICIENT * vy

        p.applyExternalForce(drone_id, -1, [fx, fy, hover_force], [0, 0, 0], p.WORLD_FRAME)
        p.stepSimulation()

        pos, _ = p.getBasePositionAndOrientation(drone_id)
        get_telemetry_ref["x"] = pos[0]
        get_telemetry_ref["y"] = pos[1]
        get_telemetry_ref["z"] = pos[2]
        get_telemetry_ref["fx"] = fx
        get_telemetry_ref["fy"] = fy

        await asyncio.sleep(SIM_DT)


async def receive_control(websocket):
    async for message in websocket:
        try:
            data = json.loads(message)
            joystick_state["x"] = max(-1.0, min(1.0, float(data["x"])))
            joystick_state["y"] = max(-1.0, min(1.0, float(data["y"])))
            joystick_state["last_update"] = time.time()
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue


async def send_telemetry(websocket, telemetry):
    while True:
        await websocket.send(json.dumps(telemetry))
        await asyncio.sleep(TELEMETRY_INTERVAL)


async def send_camera_frames(websocket):
    while True:
        jpeg_b64 = camera_state["jpeg_b64"]
        if jpeg_b64 is not None:
            await websocket.send(json.dumps({"type": "frame", "jpeg": jpeg_b64}))
        await asyncio.sleep(FRAME_SEND_INTERVAL)


async def handle_client(websocket):
    print(f"手機已連線: {websocket.remote_address}", flush=True)
    try:
        await asyncio.gather(
            receive_control(websocket),
            send_telemetry(websocket, telemetry),
            send_camera_frames(websocket),
        )
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        joystick_state["x"] = 0.0
        joystick_state["y"] = 0.0
        print(f"手機已斷線: {websocket.remote_address}", flush=True)


async def main():
    _, drone_id, hover_force = init_simulation()
    asyncio.create_task(sim_loop(drone_id, hover_force, telemetry))
    threading.Thread(target=camera_worker, daemon=True).start()

    local_ip = get_local_ip()
    print(f"伺服器啟動,手機App請連線到: ws://{local_ip}:{PORT}", flush=True)
    print(f"同一台電腦測試可用: ws://127.0.0.1:{PORT}", flush=True)

    async with websockets.serve(handle_client, HOST, PORT):
        await asyncio.Future()  # 永久執行,直到Ctrl+C


telemetry = {"type": "telemetry", "x": 0.0, "y": 0.0, "z": 0.0, "fx": 0.0, "fy": 0.0}

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n伺服器已停止", flush=True)

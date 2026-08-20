import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import cv2
from ultralytics import YOLO
import time
import math
import numpy as np
import pybullet as p
import pybullet_data
from collections import deque

# ---------- 方向判斷與施力轉換 ----------
def get_direction(diff_x, diff_y, threshold=30):
    commands = []
    if abs(diff_x) > threshold:
        commands.append("RIGHT" if diff_x > 0 else "LEFT")
    if abs(diff_y) > threshold:
        commands.append("DOWN" if diff_y > 0 else "UP")
    if not commands:
        commands.append("STAY")
    return commands

def direction_to_force(direction_list, horizontal_force=5.0):
    fx, fy = 0, 0
    if "RIGHT" in direction_list:
        fx += horizontal_force
    if "LEFT" in direction_list:
        fx -= horizontal_force
    if "UP" in direction_list:
        fy += horizontal_force
    if "DOWN" in direction_list:
        fy -= horizontal_force
    return fx, fy

# ---------- 多類別搜索 + 優先度排序 ----------
TARGET_CLASSES = ["chair", "backpack", "bottle"]
CLASS_PRIORITY = {"chair": 2, "backpack": 2, "bottle": 1}
CONFIDENCE_THRESHOLD = 0.5

def detect_candidates(results, model, target_classes, confidence_threshold, frame_center_x, frame_center_y):
    candidates = []
    for box in results[0].boxes:
        confidence = float(box.conf[0])
        if confidence < confidence_threshold:
            continue
        cls_id = int(box.cls[0])
        class_name = model.names[cls_id]
        if class_name not in target_classes:
            continue
        x1, y1, x2, y2 = box.xyxy[0]
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        distance = ((center_x - frame_center_x) ** 2 + (center_y - frame_center_y) ** 2) ** 0.5
        candidates.append({
            "box": (x1, y1, x2, y2), "center": (center_x, center_y),
            "distance": distance, "class_name": class_name, "confidence": confidence
        })
    return candidates

def select_target(candidates):
    if not candidates:
        return None
    return min(candidates, key=lambda c: (CLASS_PRIORITY.get(c["class_name"], 99), c["distance"]))

# ---------- 持續搜索模式 ----------
def search_pattern(step_count, amplitude=3.0, speed=0.05):
    fx = amplitude * math.sin(step_count * speed)
    fy = amplitude * math.cos(step_count * speed)
    return fx, fy

# ---------- 信心分數趨勢追蹤 ----------
confidence_history = deque(maxlen=10)
LOCK_ON_THRESHOLD = 0.75
LOCK_ON_STREAK_REQUIRED = 5

def check_lock_on(confidence_history, lock_threshold=LOCK_ON_THRESHOLD, streak_required=LOCK_ON_STREAK_REQUIRED):
    if len(confidence_history) < streak_required:
        return False
    recent = list(confidence_history)[-streak_required:]
    return all(c >= lock_threshold for c in recent)

# ---------- 新增1:銳化濾鏡(可開關) ----------
ENABLE_SHARPEN = True
# 用意:開關控制是否對畫面做銳化處理,方便你之後對比開/關的效果差異
# 原理:只能增強已存在的邊緣對比度,無法補回真正缺失的細節,
#      如果鏡頭本身畫質太差或距離太遠,銳化的效果會很有限

def sharpen_frame(frame):
    kernel = np.array([[0, -1, 0],
                        [-1, 5, -1],
                        [0, -1, 0]])
    return cv2.filter2D(frame, -1, kernel)

# ---------- 新增2:掃描視覺效果(可開關,純視覺,不影響偵測邏輯) ----------
ENABLE_SCAN_EFFECT = True
scan_line_y = 0
SCAN_SPEED = 8

def draw_scan_effect(frame, scan_y):
    cv2.line(frame, (0, scan_y), (frame.shape[1], scan_y), (0, 255, 255), 2)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, max(0, scan_y-30)), (frame.shape[1], scan_y), (0, 255, 255), -1)
    cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
    return frame

# ---------- 新增3:分塊偵測(獨立函式,不放進即時主迴圈) ----------
def tiled_detection(frame, model, tile_size=320, overlap=50):
    # 用意:把畫面切成多小塊分別偵測,提升遠處小目標的偵測率
    # 原理:見前面說明——每格獨立做一次YOLO推論,運算量隨切塊數量倍增
    # 注意:這個函式故意不放進即時while迴圈,因為FPS會從約24掉到個位數,
    #      不適合即時webcam展示,是保留給「事後分析單張截圖」使用的獨立功能,
    #      例如：截下一張你覺得目標離很遠、看不清楚的畫面,呼叫這個函式
    #      單獨分析那一張,而不是每一格畫面都跑一次
    h, w = frame.shape[:2]
    all_boxes = []
    step = tile_size - overlap
    for y in range(0, h, step):
        for x in range(0, w, step):
            tile = frame[y:y+tile_size, x:x+tile_size]
            if tile.shape[0] < 50 or tile.shape[1] < 50:
                continue
            results = model(tile, imgsz=320, verbose=False)
            for box in results[0].boxes:
                bx1, by1, bx2, by2 = box.xyxy[0]
                all_boxes.append({
                    "box": (int(bx1)+x, int(by1)+y, int(bx2)+x, int(by2)+y),
                    "cls": int(box.cls[0]), "conf": float(box.conf[0])
                })
    return all_boxes

# ---------- 平滑處理 ----------
diff_x_history = deque(maxlen=5)
diff_y_history = deque(maxlen=5)

# ---------- PyBullet 初始化 ----------
physicsClient = p.connect(p.DIRECT)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.8)
planeId = p.loadURDF("plane.urdf")
droneId = p.loadURDF("sphere2.urdf", [0, 0, 1], p.getQuaternionFromEuler([0, 0, 0]))
mass = p.getDynamicsInfo(droneId, -1)[0]
hover_force = mass * 9.8
sim_x_positions, sim_y_positions, sim_z_positions = [], [], []

# ---------- YOLO/OpenCV 初始化 ----------
model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)
prev_time = time.time()

MAX_STEPS = 1500
step_count = 0
lock_on_triggered = False

while step_count < MAX_STEPS:
    curr_time = time.time()
    time_diff = curr_time - prev_time
    fps = 1 / time_diff if time_diff > 0 else 0
    prev_time = curr_time

    ret, frame = cap.read()

    if ENABLE_SHARPEN:
        frame = sharpen_frame(frame)
        # 用意:先對原始畫面做銳化,再拿去給YOLO偵測跟顯示,
        #      如果之後想比較開/關的效果差異,把ENABLE_SHARPEN改成False測試即可

    results = model(frame, imgsz=320)

    frame_center_x = frame.shape[1] // 2
    frame_center_y = frame.shape[0] // 2

    candidates = detect_candidates(results, model, TARGET_CLASSES, CONFIDENCE_THRESHOLD,
                                     frame_center_x, frame_center_y)
    target = select_target(candidates)

    if target:
        confidence_history.append(target["confidence"])
        center_x, center_y = target["center"]
        diff_x = center_x - frame_center_x
        diff_y = center_y - frame_center_y

        print(f"[原始] diff_x={diff_x}, diff_y={diff_y}", flush=True)

        diff_x_history.append(diff_x)
        diff_y_history.append(diff_y)
        smoothed_diff_x = sum(diff_x_history) / len(diff_x_history)
        smoothed_diff_y = sum(diff_y_history) / len(diff_y_history)

        direction = get_direction(smoothed_diff_x, smoothed_diff_y)
        fx, fy = direction_to_force(direction)

        if check_lock_on(confidence_history) and not lock_on_triggered:
            print(f"*** 鎖定確認:{target['class_name']} 連續{LOCK_ON_STREAK_REQUIRED}格信心分數穩定超過{LOCK_ON_THRESHOLD} ***", flush=True)
            lock_on_triggered = True
    else:
        direction = ["SEARCH"]
        fx, fy = search_pattern(step_count)
        lock_on_triggered = False

    p.applyExternalForce(droneId, -1, [fx, fy, hover_force], [0, 0, 0], p.WORLD_FRAME)
    p.stepSimulation()

    pos, orn = p.getBasePositionAndOrientation(droneId)
    sim_x_positions.append(pos[0])
    sim_y_positions.append(pos[1])
    sim_z_positions.append(pos[2])

    target_info = f"{target['class_name']}(conf={target['confidence']:.2f})" if target else "搜索中"
    print(f"目標:{target_info}, 指令:{direction}, 模擬位置:({pos[0]:.2f},{pos[1]:.2f},{pos[2]:.2f})", flush=True)

    if target:
        x1, y1, x2, y2 = target["box"]
        center_x, center_y = target["center"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
        # 補回中心點紅點

        label = f"{target['class_name']} {target['confidence']:.2f}"
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, str(direction), (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        for c in candidates:
            if c is not target:
                cx1, cy1, cx2, cy2 = c["box"]
                cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (0, 0, 255), 1)
    else:
        cv2.putText(frame, "SEARCHING...", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)

    if ENABLE_SCAN_EFFECT:
        scan_line_y = (scan_line_y + SCAN_SPEED) % frame.shape[0]
        frame = draw_scan_effect(frame, scan_line_y)

    cv2.line(frame, (frame_center_x-20, frame_center_y), (frame_center_x+20, frame_center_y), (255,255,255), 2)
    cv2.line(frame, (frame_center_x, frame_center_y-20), (frame_center_x, frame_center_y+20), (255,255,255), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Enhanced Search System", frame)

    key = cv2.waitKey(1) & 0xFF
    if key in [ord('q'), ord('Q')]:
        break
    elif key == ord('t'):
        # 用意:按't'鍵,對「當下這一格畫面」額外做一次分塊偵測分析,
        #      印出結果比較跟一般偵測的差異,不影響主迴圈的即時運作
        print("執行分塊偵測分析(需要幾秒鐘)...", flush=True)
        tiled_results = tiled_detection(frame, model)
        print(f"分塊偵測找到 {len(tiled_results)} 個物體:", flush=True)
        for r in tiled_results:
            print(f"  類別ID:{r['cls']}, 信心:{r['conf']:.2f}, 位置:{r['box']}", flush=True)

    step_count += 1

cap.release()
cv2.destroyAllWindows()
p.disconnect()

import matplotlib.pyplot as plt
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4))
ax1.plot(sim_x_positions); ax1.set_title("X Position"); ax1.set_xlabel("Step")
ax2.plot(sim_y_positions); ax2.set_title("Y Position"); ax2.set_xlabel("Step")
ax3.plot(sim_z_positions); ax3.set_title("Z Height"); ax3.set_xlabel("Step")
plt.tight_layout()
plt.savefig("day19_enhanced_result.png")
print("結果圖已存成 day19_enhanced_result.png", flush=True)
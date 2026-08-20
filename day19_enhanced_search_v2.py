import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import cv2
from ultralytics import YOLO
import time
import math
import numpy as np
import csv
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
TARGET_CLASSES = ["person", "bottle", "cell phone"]
CLASS_PRIORITY = {"person": 1, "bottle": 2, "cell phone": 2}
CONFIDENCE_THRESHOLD = 0.4
# 用意:降低門檻,減少bottle/cell phone因信心分數不足而被過濾掉、頻繁進入SEARCH的狀況

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

# ---------- 銳化濾鏡(可開關) ----------
ENABLE_SHARPEN = False

def sharpen_frame(frame):
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    return cv2.filter2D(frame, -1, kernel)

# ---------- 掃描視覺效果(可開關) ----------
ENABLE_SCAN_EFFECT = False
scan_line_y = 0
SCAN_SPEED = 8

def draw_scan_effect(frame, scan_y):
    cv2.line(frame, (0, scan_y), (frame.shape[1], scan_y), (0, 255, 255), 2)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, max(0, scan_y-30)), (frame.shape[1], scan_y), (0, 255, 255), -1)
    cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
    return frame

# ---------- 平滑處理 ----------
diff_x_history = deque(maxlen=5)
diff_y_history = deque(maxlen=5)

# ---------- 新增:CSV紀錄 ----------
log_file = open("day19_debug_log.csv", "w", newline="", encoding="utf-8")
log_writer = csv.writer(log_file)
log_writer.writerow(["step", "target_class", "confidence", "diff_x", "diff_y",
                       "smoothed_diff_x", "smoothed_diff_y", "direction",
                       "pos_x", "pos_y", "pos_z"])
# 用意:把每一格完整數據寫進CSV檔,不受終端機顯示長度限制,
#      之後可以用Excel打開查看任何一段時間的完整紀錄

# ---------- 新增:記錄原始diff_x, diff_y歷史(用來畫「實際位置起伏」圖) ----------
raw_diff_x_history = []
raw_diff_y_history = []
raw_diff_steps = []
# 用意:分開記錄「原始偏移量」跟「模擬位置」兩種不同的資料,
#      原始偏移量反映你在畫面裡的實際相對位置(不受物理慣性影響),
#      模擬位置反映施力累積後的球體移動軌跡(受慣性影響),兩者呈現的意義不同

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

    results = model(frame, imgsz=320, verbose=False)
    # 用意:加上verbose=False,關閉YOLO內建那些"0: 256x320 1 person..."的自動輸出,
    #      減少終端機被無關訊息塞滿的問題,你的[原始]debug資訊還是會照常print

    frame_center_x = frame.shape[1] // 2
    frame_center_y = frame.shape[0] // 2

    candidates = detect_candidates(results, model, TARGET_CLASSES, CONFIDENCE_THRESHOLD,
                                     frame_center_x, frame_center_y)
    target = select_target(candidates)

    diff_x, diff_y = None, None
    smoothed_diff_x, smoothed_diff_y = None, None

    if target:
        confidence_history.append(target["confidence"])
        center_x, center_y = target["center"]
        diff_x = center_x - frame_center_x
        diff_y = center_y - frame_center_y

        diff_x_history.append(diff_x)
        diff_y_history.append(diff_y)
        smoothed_diff_x = sum(diff_x_history) / len(diff_x_history)
        smoothed_diff_y = sum(diff_y_history) / len(diff_y_history)

        raw_diff_x_history.append(diff_x)
        raw_diff_y_history.append(diff_y)
        raw_diff_steps.append(step_count)
        # 用意:只在有偵測到目標時,記錄原始偏移量,SEARCH狀態不記錄(沒有意義的資料)

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

    if target:
        log_writer.writerow([step_count, target['class_name'], f"{target['confidence']:.2f}",
                              diff_x, diff_y, f"{smoothed_diff_x:.1f}", f"{smoothed_diff_y:.1f}",
                              str(direction), f"{pos[0]:.3f}", f"{pos[1]:.3f}", f"{pos[2]:.3f}"])
    else:
        log_writer.writerow([step_count, "None", "", "", "", "", "", str(direction),
                              f"{pos[0]:.3f}", f"{pos[1]:.3f}", f"{pos[2]:.3f}"])

    if target:
        x1, y1, x2, y2 = target["box"]
        center_x, center_y = target["center"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
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

    step_count += 1

cap.release()
cv2.destroyAllWindows()
p.disconnect()
log_file.close()
print(f"CSV紀錄已存成 day19_debug_log.csv,共{step_count}筆資料", flush=True)

# ---------- 圖表1:模擬位置(原本就有,呈現慣性累積效果) ----------
import matplotlib.pyplot as plt
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4))
ax1.plot(sim_x_positions); ax1.set_title("Simulated X Position (physics)"); ax1.set_xlabel("Step")
ax2.plot(sim_y_positions); ax2.set_title("Simulated Y Position (physics)"); ax2.set_xlabel("Step")
ax3.plot(sim_z_positions); ax3.set_title("Z Height"); ax3.set_xlabel("Step")
plt.tight_layout()
plt.savefig("day19_enhanced_result.png")
print("模擬位置圖已存成 day19_enhanced_result.png", flush=True)

# ---------- 新增圖表2:原始偏移量(直接反映你在畫面裡的實際起伏) ----------
if raw_diff_x_history:
    fig2, (bx1, bx2) = plt.subplots(1, 2, figsize=(12, 4))
    bx1.plot(raw_diff_steps, raw_diff_x_history)
    bx1.axhline(y=30, color='r', linestyle='--', alpha=0.5, label='threshold')
    bx1.axhline(y=-30, color='r', linestyle='--', alpha=0.5)
    bx1.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
    bx1.set_title("Raw diff_x (actual screen position)")
    bx1.set_xlabel("Step")
    bx1.set_ylabel("pixels (+ = right of center)")
    bx1.legend()

    bx2.plot(raw_diff_steps, raw_diff_y_history)
    bx2.axhline(y=30, color='r', linestyle='--', alpha=0.5, label='threshold')
    bx2.axhline(y=-30, color='r', linestyle='--', alpha=0.5)
    bx2.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
    bx2.set_title("Raw diff_y (actual screen position)")
    bx2.set_xlabel("Step")
    bx2.set_ylabel("pixels (+ = below center)")
    bx2.legend()

    plt.tight_layout()
    plt.savefig("day19_raw_position_result.png")
    print("原始位置圖已存成 day19_raw_position_result.png", flush=True)
    # 用意:這張圖不受物理慣性影響,直接呈現「你在畫面裡實際的相對位置隨時間變化」,
    #      紅色虛線標出threshold=30的邊界,超過紅線才會真正觸發方向指令,
    #      這樣你能清楚看到自己動作的起伏,而不是被慣性累積的曲線掩蓋掉
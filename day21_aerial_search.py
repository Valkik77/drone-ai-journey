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

# ============================================================================
# Day21:改用空拍視角的偵測模型
# ----------------------------------------------------------------------------
# 從 day19_enhanced_search_v2.py 複製過來演進(Day腳本是逐日快照,見CLAUDE.md)。
# 主要差異:
#   1. 模型換成 VisDrone(空拍資料集)微調過的 yolov8s_visdrone.pt,取代COCO預訓練的
#      yolov8s.pt——COCO幾乎都是地面平視角度,從空中往下看人會掉很兇。
#      權重來源:https://huggingface.co/dronefreak/visdrone-yolov8s (best.pt,AGPL-3.0)
#      下載:curl -L -o yolov8s_visdrone.pt \
#            "https://huggingface.co/dronefreak/visdrone-yolov8s/resolve/main/best.pt"
#   2. 輸入來源可切換:webcam(SOURCE=0)或空拍影片檔(SOURCE="xxx.mp4"),
#      方便直接拿真的空拍片段測,不用把筆電舉高對著天空。
#   3. 類別對應改成 VisDrone 的類別表(沒有 person,改用 pedestrian/people;
#      也沒有 bottle/backpack/suitcase 這些物品類別)。
#   4. 偏移量改成「正規化到 [-1,1]」再做判斷與施力,不再吃絕對像素——
#      這樣換不同解析度的影片(webcam 640 vs 空拍 1080p)行為才一致。
#   5. 拿掉 day19 那個 person 專用的「框高寬比 >= 0.5」過濾:那是為地面平視的
#      全身框設計的,空拍的人框又小又接近方形,套下去會被清光。
#      框面積門檻也大幅調低(空拍目標常常只佔畫面萬分之幾)。
# ============================================================================

# ---------- 輸入來源 ----------
SOURCE = 0            # 0/1... = webcam 編號;或改成影片路徑字串,例如 "aerial_test.mp4"
LOOP_VIDEO = True     # 影片放完後是否從頭再播(SOURCE 是 webcam 時無作用)
INFER_SIZE = 640      # 空拍目標小,imgsz 拉高比較抓得到(這台機器會比 320 慢不少)
DISPLAY_MAX_WIDTH = 960  # 只縮顯示視窗,不影響推論

# ---------- 模型 ----------
MODEL_PATH = "yolov8s_visdrone.pt"

# ---------- 多類別搜索 + 優先度排序(VisDrone 類別) ----------
# VisDrone 類別: pedestrian people bicycle car van truck tricycle awning-tricycle bus motor others
#   pedestrian = 站/走的人,people = 其他姿勢的人(坐、蹲、騎乘中)——搜救情境兩種都要
#   bicycle / motor 當作「可能有人」的弱訊號,優先度壓低
TARGET_CLASSES = ["pedestrian", "people", "bicycle", "motor"]
CLASS_PRIORITY = {"pedestrian": 1, "people": 1, "bicycle": 3, "motor": 3}
CONFIDENCE_THRESHOLD = 0.25
# 用意:VisDrone 的 people/pedestrian 本來信心分數就偏低(空拍小目標),門檻設太高會整片抓不到

MIN_BOX_AREA_RATIO = 0.00005  # 空拍目標很小,只濾掉幾乎是雜點的框(day19 用 0.01 對空拍太大)

# ---------- 方向判斷(改吃正規化偏移量 -1..1) ----------
DEADZONE_RATIO = 0.09  # 目標落在畫面中心 ±9% 內就當 STAY(對應 day19 的 threshold=30px / 半寬)

def get_direction(norm_x, norm_y, deadzone=DEADZONE_RATIO):
    commands = []
    if abs(norm_x) > deadzone:
        commands.append("RIGHT" if norm_x > 0 else "LEFT")
    if abs(norm_y) > deadzone:
        commands.append("DOWN" if norm_y > 0 else "UP")
    if not commands:
        commands.append("STAY")
    return commands

# ---------- 連續 PD 施力(沿用 day19,增益改成配合正規化誤差) ----------
KP_FORCE = 12.0   # 誤差為滿舵(±1)時的比例施力;day19 是 0.05/px * 320px 半寬 ≈ 16,取相近值
KD_DAMPING = 20.0  # 依目前速度施加阻尼,避免 diff 歸零後慣性讓球體無限漂移(理由同 day19)
PD_MAX_FORCE = 15.0

def pd_force(norm_x, norm_y, vx, vy):
    fx = KP_FORCE * norm_x - KD_DAMPING * vx
    fy = -KP_FORCE * norm_y - KD_DAMPING * vy
    fx = max(-PD_MAX_FORCE, min(PD_MAX_FORCE, fx))
    fy = max(-PD_MAX_FORCE, min(PD_MAX_FORCE, fy))
    return fx, fy

def detect_candidates(results, model, target_classes, confidence_threshold,
                      frame_center_x, frame_center_y):
    frame_area = (frame_center_x * 2) * (frame_center_y * 2)
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
        box_w, box_h = x2 - x1, y2 - y1
        if box_w <= 0 or box_h <= 0:
            continue
        if (box_w * box_h) / frame_area < MIN_BOX_AREA_RATIO:
            continue
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

# ---------- 持續搜索模式(沿用 day19) ----------
def search_pattern(step_count, amplitude=3.0, speed=0.05):
    fx = amplitude * math.sin(step_count * speed)
    fy = amplitude * math.cos(step_count * speed)
    return fx, fy

# ---------- 信心分數趨勢追蹤(沿用 day19) ----------
confidence_history = deque(maxlen=10)
LOCK_ON_THRESHOLD = 0.5   # 配合 VisDrone 偏低的信心分數,從 0.75 調降
LOCK_ON_STREAK_REQUIRED = 5

def check_lock_on(confidence_history, lock_threshold=LOCK_ON_THRESHOLD, streak_required=LOCK_ON_STREAK_REQUIRED):
    if len(confidence_history) < streak_required:
        return False
    recent = list(confidence_history)[-streak_required:]
    return all(c >= lock_threshold for c in recent)

# ---------- 平滑處理(沿用 day19,改存正規化偏移量) ----------
norm_x_history = deque(maxlen=5)
norm_y_history = deque(maxlen=5)

# ---------- CSV 紀錄 ----------
log_file = open("day21_debug_log.csv", "w", newline="", encoding="utf-8")
log_writer = csv.writer(log_file)
log_writer.writerow(["step", "target_class", "confidence", "norm_x", "norm_y",
                     "smoothed_norm_x", "smoothed_norm_y", "direction",
                     "pos_x", "pos_y", "pos_z"])

raw_norm_x_history = []
raw_norm_y_history = []
raw_norm_steps = []

# ---------- PyBullet 初始化(沿用 day19,一定要 DIRECT) ----------
physicsClient = p.connect(p.DIRECT)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.8)
planeId = p.loadURDF("plane.urdf")
droneId = p.loadURDF("sphere2.urdf", [0, 0, 1], p.getQuaternionFromEuler([0, 0, 0]))
mass = p.getDynamicsInfo(droneId, -1)[0]
hover_force = mass * 9.8
sim_x_positions, sim_y_positions, sim_z_positions = [], [], []

# ---------- YOLO / OpenCV 初始化 ----------
if not os.path.exists(MODEL_PATH):
    raise SystemExit(
        f"找不到 {MODEL_PATH}。請先下載 VisDrone 微調權重:\n"
        f'  curl -L -o {MODEL_PATH} '
        f'"https://huggingface.co/dronefreak/visdrone-yolov8s/resolve/main/best.pt"'
    )
model = YOLO(MODEL_PATH)
print(f"模型類別: {model.names}", flush=True)

cap = cv2.VideoCapture(SOURCE)
if not cap.isOpened():
    raise SystemExit(f"無法開啟輸入來源: {SOURCE!r}")
is_video_file = isinstance(SOURCE, str)
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
    if not ret:
        if is_video_file and LOOP_VIDEO:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        print("輸入來源結束", flush=True)
        break

    results = model(frame, imgsz=INFER_SIZE, verbose=False)

    frame_center_x = frame.shape[1] // 2
    frame_center_y = frame.shape[0] // 2

    candidates = detect_candidates(results, model, TARGET_CLASSES, CONFIDENCE_THRESHOLD,
                                   frame_center_x, frame_center_y)
    target = select_target(candidates)

    norm_x, norm_y = None, None
    smoothed_norm_x, smoothed_norm_y = None, None

    if target:
        confidence_history.append(target["confidence"])
        center_x, center_y = target["center"]
        norm_x = (center_x - frame_center_x) / frame_center_x  # -1..1,+ = 中心右側
        norm_y = (center_y - frame_center_y) / frame_center_y  # -1..1,+ = 中心下方

        norm_x_history.append(norm_x)
        norm_y_history.append(norm_y)
        smoothed_norm_x = sum(norm_x_history) / len(norm_x_history)
        smoothed_norm_y = sum(norm_y_history) / len(norm_y_history)

        raw_norm_x_history.append(norm_x)
        raw_norm_y_history.append(norm_y)
        raw_norm_steps.append(step_count)

        direction = get_direction(smoothed_norm_x, smoothed_norm_y)  # 只用來顯示/記錄
        (vx, vy, _), _ = p.getBaseVelocity(droneId)
        fx, fy = pd_force(smoothed_norm_x, smoothed_norm_y, vx, vy)

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
                             f"{norm_x:.3f}", f"{norm_y:.3f}",
                             f"{smoothed_norm_x:.3f}", f"{smoothed_norm_y:.3f}",
                             str(direction), f"{pos[0]:.3f}", f"{pos[1]:.3f}", f"{pos[2]:.3f}"])
    else:
        log_writer.writerow([step_count, "None", "", "", "", "", "", str(direction),
                             f"{pos[0]:.3f}", f"{pos[1]:.3f}", f"{pos[2]:.3f}"])

    # ---------- 畫面標註 ----------
    if target:
        x1, y1, x2, y2 = target["box"]
        cx, cy = target["center"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
        cv2.putText(frame, f"{target['class_name']} {target['confidence']:.2f}",
                    (x1, max(0, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, str(direction), (x1, y2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        for c in candidates:
            if c is not target:
                cx1, cy1, cx2, cy2 = c["box"]
                cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (0, 0, 255), 1)
    else:
        cv2.putText(frame, "SEARCHING...", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)

    cv2.line(frame, (frame_center_x - 20, frame_center_y), (frame_center_x + 20, frame_center_y), (255, 255, 255), 2)
    cv2.line(frame, (frame_center_x, frame_center_y - 20), (frame_center_x, frame_center_y + 20), (255, 255, 255), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    show = frame
    if frame.shape[1] > DISPLAY_MAX_WIDTH:
        scale = DISPLAY_MAX_WIDTH / frame.shape[1]
        show = cv2.resize(frame, (DISPLAY_MAX_WIDTH, int(frame.shape[0] * scale)))
    cv2.imshow("Day21 Aerial Search", show)

    if cv2.waitKey(1) & 0xFF in [ord('q'), ord('Q')]:
        break

    step_count += 1

cap.release()
cv2.destroyAllWindows()
p.disconnect()
log_file.close()
print(f"CSV紀錄已存成 day21_debug_log.csv,共{step_count}筆資料", flush=True)

# ---------- 圖表1:模擬物理位置(慣性累積效果) ----------
import matplotlib.pyplot as plt
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4))
ax1.plot(sim_x_positions); ax1.set_title("Simulated X Position (physics)"); ax1.set_xlabel("Step")
ax2.plot(sim_y_positions); ax2.set_title("Simulated Y Position (physics)"); ax2.set_xlabel("Step")
ax3.plot(sim_z_positions); ax3.set_title("Z Height"); ax3.set_xlabel("Step")
plt.tight_layout()
plt.savefig("day21_aerial_result.png")
print("模擬位置圖已存成 day21_aerial_result.png", flush=True)

# ---------- 圖表2:原始正規化偏移量(目標在畫面裡的實際相對位置) ----------
if raw_norm_x_history:
    fig2, (bx1, bx2) = plt.subplots(1, 2, figsize=(12, 4))
    for bx, series, title, ylab in (
        (bx1, raw_norm_x_history, "Raw norm_x (actual screen position)", "ratio (+ = right of center)"),
        (bx2, raw_norm_y_history, "Raw norm_y (actual screen position)", "ratio (+ = below center)"),
    ):
        bx.plot(raw_norm_steps, series)
        bx.axhline(y=DEADZONE_RATIO, color='r', linestyle='--', alpha=0.5, label='deadzone')
        bx.axhline(y=-DEADZONE_RATIO, color='r', linestyle='--', alpha=0.5)
        bx.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
        bx.set_ylim(-1, 1)
        bx.set_title(title); bx.set_xlabel("Step"); bx.set_ylabel(ylab); bx.legend()
    plt.tight_layout()
    plt.savefig("day21_raw_position_result.png")
    print("原始位置圖已存成 day21_raw_position_result.png", flush=True)

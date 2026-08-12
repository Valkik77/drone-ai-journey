import cv2
from ultralytics import YOLO
import time
import pybullet as p
import pybullet_data
import os
from collections import deque
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
# 用意:告訴系統允許多個OpenMP執行環境同時存在,強制繼續執行
# 原理:這是設定一個環境變數,在程式啟動的最開始就要設定好,
#      才能在後面import pybullet、ultralytics時生效,避免衝突直接讓程式崩潰
#      這是pybullet跟pytorch(ultralytics底層用到)版本衝突的已知問題,
#      官方建議的暫時解法就是設定這個環境變數放行

diff_x_history = deque(maxlen=5)
diff_y_history = deque(maxlen=5)
# 用意:記錄最近5格畫面的偏移量,取平均來平滑雜訊
# 原理:跟Day13處理過的邏輯相同,現在正式套用進即時整合版本


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

def detect_candidates(results, model, target_class, confidence_threshold, frame_center_x, frame_center_y):
    candidates = []
    for box in results[0].boxes:
        confidence = float(box.conf[0])
        if confidence < confidence_threshold:
            continue
        cls_id = int(box.cls[0])
        class_name = model.names[cls_id]
        if class_name != target_class:
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

def draw_results(frame, candidates, target, frame_center_x, frame_center_y, fps, current_direction):
    # 用意:這裡新增了 current_direction 這個參數,直接把主迴圈算好的方向指令傳進來顯示,
    #      不再由這個函式自己重複算一次diff_x/diff_y,避免邏輯重複、資料不同步
    if target:
        x1, y1, x2, y2 = target["box"]
        center_x, center_y = target["center"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
        label = f"{target['class_name']} {target['confidence']:.2f}"
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, str(current_direction), (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        for c in candidates:
            if c is not target:
                cx1, cy1, cx2, cy2 = c["box"]
                cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (0, 0, 255), 1)

    cv2.line(frame, (frame_center_x-20, frame_center_y), (frame_center_x+20, frame_center_y), (255,255,255), 2)
    cv2.line(frame, (frame_center_x, frame_center_y-20), (frame_center_x, frame_center_y+20), (255,255,255), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    return frame

# ---------- PyBullet 初始化(新增) ----------
physicsClient = p.connect(p.DIRECT)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.8)
planeId = p.loadURDF("plane.urdf")
droneId = p.loadURDF("sphere2.urdf", [0, 0, 1], p.getQuaternionFromEuler([0, 0, 0]))
mass = p.getDynamicsInfo(droneId, -1)[0]
hover_force = mass * 9.8
sim_x_positions, sim_y_positions, sim_z_positions = [], [], []
# 用意:一開始就把物理場景建好,主迴圈每一格畫面都會讓它多跑一步,
#      不用等YOLO那邊結束才開始跑模擬,兩者同步進行

# ---------- YOLO/OpenCV 初始化(原本就有的) ----------
model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)
TARGET_CLASS = "person"
CONFIDENCE_THRESHOLD = 0.6
prev_time = time.time()

MAX_STEPS = 1500
step_count = 0
# 用意:設定跑多少格畫面後自動結束,方便你錄demo時有明確的結束時間點,
#      不用手動按q(手動按也可以,這只是額外加一個保險機制)

while step_count < MAX_STEPS:
    curr_time = time.time()
    time_diff = curr_time - prev_time
    fps = 1 / time_diff if time_diff > 0 else 0
    prev_time = curr_time

    ret, frame = cap.read()
    results = model(frame, imgsz=320)

    frame_center_x = frame.shape[1] // 2
    frame_center_y = frame.shape[0] // 2

    candidates = detect_candidates(results, model, TARGET_CLASS, CONFIDENCE_THRESHOLD,
                                     frame_center_x, frame_center_y)
    target = min(candidates, key=lambda c: c["distance"]) if candidates else None

    # ---------- 這裡是新增的核心串接邏輯 ----------
    if target:
        center_x, center_y = target["center"]
        diff_x = center_x - frame_center_x
        diff_y = center_y - frame_center_y

        diff_x_history.append(diff_x)
        diff_y_history.append(diff_y)
        smoothed_diff_x = sum(diff_x_history) / len(diff_x_history)
        smoothed_diff_y = sum(diff_y_history) / len(diff_y_history)
        # 用意:用平滑後的偏移量做方向判斷,減少單一格畫面雜訊造成的誤判

        direction = get_direction(smoothed_diff_x, smoothed_diff_y)
    else:
        direction = ["STAY"]

    fx, fy = direction_to_force(direction)

    p.applyExternalForce(droneId, -1, [fx, fy, hover_force], [0, 0, 0], p.WORLD_FRAME)
    p.stepSimulation()
    # 用意:這是整個Day17最關鍵的兩行——
    #      把「這一格畫面算出的真實方向指令」直接餵給PyBullet施力,
    #      並讓物理模擬跟著推進一步,達成鏡頭畫面跟模擬器同步運作

    pos, orn = p.getBasePositionAndOrientation(droneId)
    sim_x_positions.append(pos[0])
    sim_y_positions.append(pos[1])
    sim_z_positions.append(pos[2])

    print(f"目標:{target['class_name'] if target else '無'}, 指令:{direction}, 模擬位置:({pos[0]:.2f},{pos[1]:.2f},{pos[2]:.2f})", flush=True)

    frame = draw_results(frame, candidates, target, frame_center_x, frame_center_y, fps, direction)
    cv2.imshow("YOLO + PyBullet Integration", frame)

    key = cv2.waitKey(1) & 0xFF
    if key in [ord('q'), ord('Q')]:
        break

    step_count += 1

cap.release()
cv2.destroyAllWindows()
p.disconnect()

# ---------- 收尾:畫出整段模擬軌跡 ----------
import matplotlib.pyplot as plt
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4))
ax1.plot(sim_x_positions); ax1.set_title("X Position"); ax1.set_xlabel("Step")
ax2.plot(sim_y_positions); ax2.set_title("Y Position"); ax2.set_xlabel("Step")
ax3.plot(sim_z_positions); ax3.set_title("Z Height"); ax3.set_xlabel("Step")
plt.tight_layout()
plt.savefig("day17_realtime_result.png")
print("即時整合結果圖已存成 day17_realtime_result.png", flush=True)
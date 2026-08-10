import cv2
from ultralytics import YOLO
import time
from collections import deque

diff_x_history = deque(maxlen=5)
diff_y_history = deque(maxlen=5)
# 用意:建立一個「最多存5筆」的佇列,自動只保留最近5格的偏移量紀錄
# 原理:deque(maxlen=5)是一種特殊的list,滿了之後新資料進來,
#      最舊的資料會自動被擠出去,不用自己手動刪除

def get_direction(diff_x, diff_y, threshold=30):
    # 跟之前完全相同,不變動
    commands = []
    if abs(diff_x) > threshold:
        commands.append("RIGHT" if diff_x > 0 else "LEFT")
    if abs(diff_y) > threshold:
        commands.append("DOWN" if diff_y > 0 else "UP")
    if not commands:
        commands.append("STAY")
    return commands

def detect_candidates(results, model, target_class, confidence_threshold, frame_center_x, frame_center_y):
    # 用意:把Day11、12裡「篩選信心分數、篩選類別、算距離、收集候選者」
    #      這一整段邏輯獨立成一個函式
    # 原理:這段邏輯原本佔了主迴圈裡快20行,現在主迴圈只要呼叫這一行函式就好,
    #      可讀性大幅提升,而且這個函式以後任何專案要做「YOLO+距離篩選」都能直接複用
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
            "box": (x1, y1, x2, y2),
            "center": (center_x, center_y),
            "distance": distance,
            "class_name": class_name,
            "confidence": confidence
        })
    return candidates


def draw_results(frame, candidates, target, frame_center_x, frame_center_y, fps):
    # 用意:把Day10-12裡「畫框、畫中心點、畫十字準心、顯示FPS、顯示指令文字」
    #      這些純粹畫面繪製的邏輯,獨立成一個函式
    # 原理:這個函式只負責「畫」,不負責任何判斷邏輯,職責單一、好維護,
    #      這是軟體工程常見的原則——一個函式只做一件事(單一職責原則)
    if target:
        x1, y1, x2, y2 = target["box"]
        center_x, center_y = target["center"]
        diff_x = center_x - frame_center_x
        diff_y = center_y - frame_center_y

        diff_x_history.append(diff_x)
        diff_y_history.append(diff_y)
        smoothed_diff_x = sum(diff_x_history) / len(diff_x_history)
        smoothed_diff_y = sum(diff_y_history) / len(diff_y_history)
        # 用意:把這一格的偏移量存進歷史紀錄,並計算最近5格的平均值
        # 原理:deque(maxlen=5)存最近5筆資料,平均後可以有效抵銷單一格畫面的雜訊跳動,
        #      只有真正持續往同一方向移動時,平均值才會明顯偏移

        direction = get_direction(smoothed_diff_x, smoothed_diff_y, threshold=60)
        # 用意:改用「平滑過的偏移量」來判斷方向,而不是原始的diff_x/diff_y

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
        label = f"{target['class_name']} {target['confidence']:.2f}"
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, str(direction), (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        print(f"鎖定目標:{target['class_name']}, 偏移:({diff_x},{diff_y}), 平滑後:({smoothed_diff_x:.1f},{smoothed_diff_y:.1f}), 指令:{direction}", flush=True)

        for c in candidates:
            if c is not target:
                cx1, cy1, cx2, cy2 = c["box"]
                cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (0, 0, 255), 1)

    cv2.line(frame, (frame_center_x-20, frame_center_y), (frame_center_x+20, frame_center_y), (255,255,255), 2)
    cv2.line(frame, (frame_center_x, frame_center_y-20), (frame_center_x, frame_center_y+20), (255,255,255), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    return frame


model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)

TARGET_CLASS = "bottle"
CONFIDENCE_THRESHOLD = 0.5
prev_time = time.time()

while True:
    curr_time = time.time()
    time_diff = curr_time - prev_time
    fps = 1 / time_diff if time_diff > 0 else 0
    # 用意:避免time_diff剛好是0時,程式因為除以零而崩潰
    # 原理:if time_diff > 0 else 0 是Python的條件表達式,
    #      意思是「如果時間差大於0就正常計算FPS,否則FPS直接設為0」
    #      FPS顯示為0只會在極少數畫面出現,不影響整體使用,但能避免程式崩潰
    prev_time = curr_time

    ret, frame = cap.read()
    results = model(frame, imgsz=320)

    frame_center_x = frame.shape[1] // 2
    frame_center_y = frame.shape[0] // 2

    candidates = detect_candidates(results, model, TARGET_CLASS, CONFIDENCE_THRESHOLD,
                                     frame_center_x, frame_center_y)
    target = min(candidates, key=lambda c: c["distance"]) if candidates else None
    # 用意:主迴圈現在只做「呼叫函式拿結果、挑目標、呼叫畫圖」三件事
    # 原理:對照你Day12的版本,主迴圈的行數大幅減少,一眼就能看懂整個流程:
    #      讀畫面→偵測→挑目標→畫出來,不用在一堆巢狀迴圈裡找邏輯

    frame = draw_results(frame, candidates, target, frame_center_x, frame_center_y, fps)
    cv2.imshow("YOLO Refactored", frame)

    key = cv2.waitKey(1) & 0xFF
    if key in [ord('q'), ord('Q')]:
        break

cap.release()
cv2.destroyAllWindows()
import cv2
from ultralytics import YOLO
import time

prev_time = time.time()
# 用意:記錄上一格處理完的時間點,搬到迴圈外面只需要初始化一次
# 原理:跟Day6做過的FPS計算完全相同邏輯,現在套用回YOLO版本上

def get_direction(diff_x, diff_y, threshold=30):
    commands = []
    if abs(diff_x) > threshold:
        commands.append("RIGHT" if diff_x > 0 else "LEFT")
    if abs(diff_y) > threshold:
        commands.append("DOWN" if diff_y > 0 else "UP")
    if not commands:
        commands.append("STAY")
    return commands

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)

TARGET_CLASS = "person"
CONFIDENCE_THRESHOLD = 0.6


while True:
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time
    ret, frame = cap.read()
    results = model(frame, imgsz=320)

    frame_center_x = frame.shape[1] // 2
    frame_center_y = frame.shape[0] // 2

    candidates = []
    # 用意:先建立一個空list,收集這一格畫面裡「所有符合條件」的目標
    # 原理:跟Day10不同,這次不在迴圈裡直接畫框、算方向,
    #      而是先把所有候選目標都蒐集起來,等迴圈跑完後再一次比較、挑出一個

    for box in results[0].boxes:
        confidence = float(box.conf[0])
        if confidence < CONFIDENCE_THRESHOLD:
            continue

        cls_id = int(box.cls[0])
        class_name = model.names[cls_id]
        if class_name != TARGET_CLASS:
            continue

        x1, y1, x2, y2 = box.xyxy[0]
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2

        distance = ((center_x - frame_center_x) ** 2 + (center_y - frame_center_y) ** 2) ** 0.5
        # 用意:算出這個目標的中心點,離畫面中心有多遠
        # 原理:這是你Day1練習3就寫過的「兩點距離公式」,現在拿來實際應用,
        #      沒有開根號直接比較平方也可以(比較快),但這裡資料量小,直接算距離比較好理解

        candidates.append({
            "box": (x1, y1, x2, y2),
            "center": (center_x, center_y),
            "distance": distance,
            "class_name": class_name,
            "confidence": confidence
        })
        # 用意:把這個目標的所有相關資訊,包成一個dict存進candidates清單
        # 原理:之後要挑選「距離最近的」時,可以直接從這個dict拿出box、center等資料,
        #      不用重新計算一次

    if candidates:
        target = min(candidates, key=lambda c: c["distance"])
        # 用意:從所有候選目標中,挑出distance(離中心距離)最小的那一個
        # 原理:min()搭配key參數,是Python內建找「清單中依某個條件最小值」的標準寫法,
        #      lambda c: c["distance"] 的意思是「用每個候選者的distance欄位來比較大小」

        x1, y1, x2, y2 = target["box"]
        center_x, center_y = target["center"]

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)

        diff_x = center_x - frame_center_x
        diff_y = center_y - frame_center_y
        direction = get_direction(diff_x, diff_y)

        label = f"{target['class_name']} {target['confidence']:.2f}"
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, str(direction), (x1, y2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        print(f"鎖定目標:{target['class_name']}, 偏移:({diff_x},{diff_y}), 指令:{direction}", flush=True)

        # 順便把其他沒被選中的候選者,用不同顏色標出來(方便你觀察、除錯)
        for c in candidates:
            if c is not target:
                cx1, cy1, cx2, cy2 = c["box"]
                cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (0, 0, 255), 1)
        # 用意:把「沒被選中」的其他人也用細細的紅框標出來(不是綠色)
        # 原理:這樣你能親眼看到「有兩個人同時入鏡時,程式確實只鎖定其中一個」,
        #      是驗證這個邏輯有沒有正確運作的好方法,而不是靠猜的

    cv2.line(frame, (frame_center_x-20, frame_center_y), (frame_center_x+20, frame_center_y), (255,255,255), 2)
    cv2.line(frame, (frame_center_x, frame_center_y-20), (frame_center_x, frame_center_y+20), (255,255,255), 2)

    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("YOLO Multi-Target", frame)

    key = cv2.waitKey(1) & 0xFF
    if key in [ord('q'), ord('Q')]:
        break

cap.release()
cv2.destroyAllWindows()
import cv2
from ultralytics import YOLO

def get_direction(diff_x, diff_y, threshold=30):
    # 用意:把偏移量轉換成方向指令(跟Day5相同,不變動)
    # 原理:threshold死區避免小幅晃動造成過度反應
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
# 用意:設定這次只想追蹤的目標類別名稱
# 原理:之後會拿YOLO判斷出來的class_name跟這個字串比對,
#      不符合的直接忽略,這樣即使畫面很多物體,也只處理你要的那一種

CONFIDENCE_THRESHOLD = 0.6

while True:
    ret, frame = cap.read()
    results = model(frame)

    frame_center_x = frame.shape[1] // 2
    frame_center_y = frame.shape[0] // 2
    # 用意:畫面中心點只需要算一次,搬到迴圈最上面

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
        cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)

        diff_x = center_x - frame_center_x
        diff_y = center_y - frame_center_y

        direction = get_direction(diff_x, diff_y)
        cv2.putText(frame, str(direction), (x1, y2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        print(f"目標:{class_name}, 偏移:({diff_x},{diff_y}), 指令:{direction}", flush=True)

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{class_name} {confidence:.2f}"
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # 迴圈結束後,只畫一次十字準心
    cv2.line(frame, (frame_center_x-20, frame_center_y), (frame_center_x+20, frame_center_y), (255,255,255), 2)
    cv2.line(frame, (frame_center_x, frame_center_y-20), (frame_center_x, frame_center_y+20), (255,255,255), 2)

    cv2.imshow("YOLO Class Filter", frame)

    key = cv2.waitKey(1) & 0xFF
    if key in [ord('q'), ord('Q')]:
        break

cap.release()
cv2.destroyAllWindows()
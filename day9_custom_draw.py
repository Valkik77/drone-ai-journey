import cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()

    results = model(frame)
    # 用意:對這一格畫面做推論
    # 原理:跟Day8相同,results[0]是這一格的偵測結果
    CONFIDENCE_THRESHOLD = 0.6
    # 用意:設定一個信心分數門檻,低於這個分數的偵測結果視為不可靠
    # 原理:這是一個「你自己決定」的數值,不是固定答案,
    #      數值越高,誤判會變少但可能漏掉真正的物體(太嚴格);
    #      數值越低,不容易漏掉物體但誤判會變多(太寬鬆),
    #      這是本週你要親自實驗、抓出一個平衡點的參數

    for box in results[0].boxes:
        confidence = float(box.conf[0])
        if confidence < CONFIDENCE_THRESHOLD:
            continue
        # 用意:信心分數不夠高的,直接跳過這次迴圈、不處理
        # 原理:continue會讓程式立刻跳到for迴圈的下一輪,
        #      這個box後面的畫框、標籤等程式碼都不會被執行,等於直接忽略它

        cls_id = int(box.cls[0])
        class_name = model.names[cls_id]
        x1, y1, x2, y2 = box.xyxy[0]
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{class_name} {confidence:.2f}"
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("YOLO Custom Draw", frame)

    key = cv2.waitKey(1) & 0xFF
    if key in [ord('q'), ord('Q')]:
        break

cap.release()
cv2.destroyAllWindows()
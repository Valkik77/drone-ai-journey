import cv2
import numpy as np
import time  
# 用意:匯入time模組,用來計算每一格畫面處理花了多少時間
# 原理:time.time()回傳目前時間戳記(從1970年至今的秒數),兩次時間相減就是經過的時間

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

def find_largest_objects(mask, min_area=300):
    # 用意:把Day3-5裡重複出現的「找輪廓、過濾雜訊、算出框座標」邏輯包成一個函式
    # 原理:重構(refactoring)的核心概念——重複超過一次的邏輯,就該抽出來變成獨立函式,
    #      好處是主程式變短好讀,而且這個函式以後在任何檔案都能直接呼叫,不用複製貼上
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in contours:
        if cv2.contourArea(c) > min_area:
            x, y, w, h = cv2.boundingRect(c)
            boxes.append((x, y, w, h))
    return boxes
    # 回傳一個list,裡面裝著每個物體的(x,y,w,h),讓主迴圈自己決定要怎麼處理這些框

def get_center(x, y, w, h):
    # 用意:把「算中心點座標」這個小邏輯也獨立出來
    # 原理:雖然只有一行運算,但獨立成函式後,如果之後想改成別的算法
    #      (例如改用質心moments而不是矩形中心),只要改這一個地方,不用到處找
    return x + w // 2, y + h // 2

cap = cv2.VideoCapture(0)
prev_time = time.time()  
# 用意:記錄「上一格」處理完的時間點,放在迴圈外面只需要初始化一次
# 原理:之後每一輪迴圈都要拿「現在時間」減去這個值,算出這一輪花了多久

while True:
    ret, frame = cap.read()

    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time
    # 用意:計算並更新FPS(每秒處理幾張畫面)
    # 原理:FPS = 1 / 處理一張畫面花的秒數。例如處理一張花0.05秒,FPS = 1/0.05 = 20
    #      這是效能監控的基本指標,之後如果加入更複雜的AI模型(如YOLO),
    #      FPS會明顯下降,這個數字能幫助你判斷「系統是否即時可用」

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower = np.array([35, 100, 100])
    upper = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    cv2.imshow("Mask", mask)

    boxes = find_largest_objects(mask, min_area=300)
    # 用意:呼叫剛才寫好的函式,取得所有符合條件的物體框
    # 原理:主迴圈現在只需要「呼叫」函式拿結果,不需要自己重寫一次找輪廓的邏輯,
    #      這就是重構帶來的好處——主程式的可讀性大幅提升

    frame_center_x = frame.shape[1] // 2
    frame_center_y = frame.shape[0] // 2

    for (x, y, w, h) in boxes:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        center_x, center_y = get_center(x, y, w, h)
        cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)

        diff_x = center_x - frame_center_x
        diff_y = center_y - frame_center_y

        direction = get_direction(diff_x, diff_y)
        cv2.putText(frame, str(direction), (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        # 用意:把方向指令直接顯示在該物體框的正上方,而不是固定畫面左上角
        # 原理:如果畫面裡有多個物體(Day3後半我們改成支援多框),
        #      指令跟著各自的框顯示,才不會混淆是哪個物體的指令

    cv2.line(frame, (frame_center_x-20, frame_center_y), (frame_center_x+20, frame_center_y), (255,255,255), 2)
    cv2.line(frame, (frame_center_x, frame_center_y-20), (frame_center_x, frame_center_y+20), (255,255,255), 2)

    cv2.putText(frame, f"FPS: {int(fps)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    # 用意:把FPS數字顯示在畫面固定位置(左上角),方便錄影展示時直接看到效能數據
    # 原理:cv2.putText單純把文字畫在指定座標上,int(fps)去掉小數點方便閱讀

    cv2.imshow("Camera", frame)

    key = cv2.waitKey(1) & 0xFF
    if key in [ord('q'), ord('Q')]:
        break

cap.release()
cv2.destroyAllWindows()
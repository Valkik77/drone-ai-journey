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


def get_center(x, y, w, h):
    # 用意:把「算中心點座標」這個小邏輯也獨立出來
    # 原理:雖然只有一行運算,但獨立成函式後,如果之後想改成別的算法
    #      (例如改用質心moments而不是矩形中心),只要改這一個地方,不用到處找
    return x + w // 2, y + h // 2

def find_largest_objects(mask, min_area=300):
    # 用意:找出mask裡「唯一」面積最大的物體框,而不是全部都框出來
    # 原理:即使做完形態學運算,還是可能有零星小碎片殘留,
    #      用max()只挑面積最大的當作主要追蹤目標,確保一個物體只對應一個框
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) > min_area:
        x, y, w, h = cv2.boundingRect(largest)
        return [(x, y, w, h)]
    return []

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
    '''
    lower = np.array([35, 100, 100])    # 顏色下限(綠色)
    upper = np.array([85, 255, 255])    # 顏色上限
    mask = cv2.inRange(hsv, lower, upper)

    '''
    lower = np.array([100, 100, 100])  # 顏色下限(藍色)
    upper = np.array([130, 255, 255])  # 顏色上限

    mask = cv2.inRange(hsv, lower, upper)
    # 用意:篩選出畫面中符合這個顏色範圍的區域
    # 原理:逐像素檢查HSV數值是否落在lower~upper之間,是的話該像素在mask上變白色,否則變黑色
    '''
    lower1 = np.array([0, 100, 100])    # 顏色下限[紅色(比較特殊,需要兩組範圍疊加)]
    upper1 = np.array([10, 255, 255])
    lower2 = np.array([170, 100, 100])
    upper2 = np.array([179, 255, 255])

    mask1 = cv2.inRange(hsv, lower1, upper1)q
    mask2 = cv2.inRange(hsv, lower2, upper2)
    mask = cv2.bitwise_or(mask1, mask2)  # 把兩組遮罩合併成一張
    '''

    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    # 用意:把mask上因反光造成的破碎小區塊「黏合」成一整塊,並清掉細小雜訊點
    # 原理:MORPH_CLOSE(閉運算)先膨脹再侵蝕,能填補區塊內部的小黑洞、
    #      把靠得很近的白色區塊連起來;MORPH_OPEN(開運算)先侵蝕再膨脹,
    #      能去除孤立的小白點雜訊。kernel是運算的「筆刷大小」,數字越大效果越強
    
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
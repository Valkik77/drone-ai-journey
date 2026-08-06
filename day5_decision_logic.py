import cv2
import numpy as np

cap = cv2.VideoCapture(0)  
# 用意:開啟系統預設鏡頭(編號0)
# 原理:VideoCapture會跟作業系統溝通,持續從硬體鏡頭抓取影像串流,之後靠 cap.read() 逐格讀取

def get_direction(diff_x, diff_y, threshold=30):
    # 用意:把「偏移量」數字轉換成「該往哪個方向動」的決策結果
    # 原理:threshold(死區)避免物體在中心附近小幅晃動時系統過度反應;
    # x軸、y軸分開獨立判斷,允許同時觸發兩個方向(例如左上角=LEFT+UP)
    # 放在迴圈外面定義,因為這是「規則」本身不會每次迴圈改變,只有丟進去的diff_x/diff_y數字會變
    commands = []
    if abs(diff_x) > threshold:
        commands.append("RIGHT" if diff_x > 0 else "LEFT")
    if abs(diff_y) > threshold:
        commands.append("DOWN" if diff_y > 0 else "UP")
    if not commands:
        commands.append("STAY")
    return commands

while True:
    ret, frame = cap.read()
    # 用意:從鏡頭抓「這一格」的畫面
    # 原理:ret是布林值代表讀取成功與否,frame是圖片資料(高度x寬度x顏色通道的陣列)

    # 練習1:轉HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # 用意:把原始BGR格式轉成HSV格式
    # 原理:HSV用「色相(Hue)」單一維度描述顏色種類,比BGR更容易用範圍篩選特定顏色
    #cv2.imshow("HSV", hsv)

    # 練習2:顏色遮罩
    #lower = np.array([35, 100, 100])   # 顏色下限(先用綠色當範例)
    #upper = np.array([85, 255, 255])   # 顏色上限
    '''
    lower = np.array([100, 100, 100])  # 顏色下限(先用藍色當範例)
    upper = np.array([130, 255, 255])  # 顏色上限

    mask = cv2.inRange(hsv, lower, upper)
    # 用意:篩選出畫面中符合這個顏色範圍的區域
    # 原理:逐像素檢查HSV數值是否落在lower~upper之間,是的話該像素在mask上變白色,否則變黑色
    '''
    lower1 = np.array([0, 100, 100])    # 顏色下限[紅色範例(比較特殊,需要兩組範圍疊加)]
    upper1 = np.array([10, 255, 255])
    lower2 = np.array([170, 100, 100])
    upper2 = np.array([179, 255, 255])

    mask1 = cv2.inRange(hsv, lower1, upper1)
    mask2 = cv2.inRange(hsv, lower2, upper2)
    mask = cv2.bitwise_or(mask1, mask2)  # 把兩組遮罩合併成一張

    cv2.imshow("Mask", mask)

    # 練習3:找輪廓、框出物體
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # 用意:從黑白遮罩圖中,找出所有連續白色區塊的邊界
    # 原理:RETR_EXTERNAL只抓最外層輪廓,CHAIN_APPROX_SIMPLE用精簡方式儲存座標點,省資源

    for c in contours:
        if cv2.contourArea(c) > 300:
            # 用意:過濾掉太小的雜訊點,只處理夠大的區塊
            # 原理:contourArea算出輪廓包圍的面積,面積太小通常代表雜訊而非真正物體
            x, y, w, h = cv2.boundingRect(c)
            # 用意:找出能包住這個輪廓的最小矩形
            # 原理:boundingRect回傳左上角座標(x,y)跟矩形的寬w、高h
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # 練習4:算出這個框的中心點
            center_x, center_y = x + w // 2, y + h // 2
            # 用意:算出這個框的正中央座標
            # 原理:矩形左上角座標加上寬高各自的一半,就是矩形中心點
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)

            # 畫面本身的中心點
            frame_center_x = frame.shape[1] // 2
            frame_center_y = frame.shape[0] // 2
            # 用意:算出整張畫面的正中央,當作參考基準點
            # 原理:frame.shape回傳(高,寬,通道數),[1]是寬、[0]是高

            # 計算偏移量
            diff_x = center_x - frame_center_x
            diff_y = center_y - frame_center_y
            # 用意:算出「物體中心」跟「畫面中心」的距離差
            # 原理:diff_x為正代表物體偏右、為負偏左;diff_y為正代表偏下、為負偏上
            # 這組數字是連接「偵測」與「決策」兩階段的關鍵資料
            print(f"物體中心偏移: x={diff_x}, y={diff_y}")

            #:呼叫 get_direction 並顯示指令 ↓↓↓
            direction = get_direction(diff_x, diff_y)
            print("指令:", direction)
            cv2.putText(frame, str(direction), (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    # 畫面中心的十字準心(迴圈外面畫一次就好,不用每個物體重複畫)
    frame_center_x = frame.shape[1] // 2
    frame_center_y = frame.shape[0] // 2
    cv2.line(frame, (frame_center_x-20, frame_center_y), (frame_center_x+20, frame_center_y), (255,255,255), 2)
    cv2.line(frame, (frame_center_x, frame_center_y-20), (frame_center_x, frame_center_y+20), (255,255,255), 2)
    # 用意:在畫面上視覺化標出中心基準點
    # 原理:單純畫兩條線組成十字,方便肉眼比對物體中心跟畫面中心的相對位置

    cv2.imshow("Camera", frame)
    # 用意:把最終處理完(含框、中心點、十字準心)的畫面顯示出來
    # 原理:cv2.imshow只顯示「呼叫當下」frame變數的內容,所以要放在所有畫框動作之後

    key = cv2.waitKey(1) & 0xFF
    if key in [ord('q'), ord('Q')]:
        break
    # 用意:偵測鍵盤輸入,按q或Q離開迴圈
    # 原理:waitKey(1)等待1毫秒讀取按鍵,& 0xFF是跨平台相容寫法避免按鍵碼判斷出錯

cap.release()
cv2.destroyAllWindows()
# 用意:程式結束前釋放鏡頭資源、關閉所有視窗
# 原理:不釋放的話鏡頭可能被其他程式視為「佔用中」,無法再次開啟
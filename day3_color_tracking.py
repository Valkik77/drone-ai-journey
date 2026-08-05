import cv2
import numpy as np

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    

    # 練習1、2、3、4 會依序加在這裡
    #1. 轉灰階
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    #cv2.imshow("HSV", hsv)
    #2.顏色遮罩
    lower = np.array([35, 100, 100])   # 顏色下限(先用綠色當範例)
    upper = np.array([85, 255, 255])   # 顏色上限
    mask = cv2.inRange(hsv, lower, upper)
    cv2.imshow("Mask", mask)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        if cv2.contourArea(c) > 300:
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # 練習4:算出這個框的中心點
            center_x, center_y = x + w // 2, y + h // 2
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)

            # 畫面本身的中心點
            frame_center_x = frame.shape[1] // 2
            frame_center_y = frame.shape[0] // 2

            # 計算偏移量
            diff_x = center_x - frame_center_x
            diff_y = center_y - frame_center_y
            print(f"物體中心偏移: x={diff_x}, y={diff_y}")

    # 畫面中心的十字準心(迴圈外面畫一次就好,不用每個物體重複畫)
    frame_center_x = frame.shape[1] // 2
    frame_center_y = frame.shape[0] // 2
    cv2.line(frame, (frame_center_x-20, frame_center_y), (frame_center_x+20, frame_center_y), (255,255,255), 2)
    cv2.line(frame, (frame_center_x, frame_center_y-20), (frame_center_x, frame_center_y+20), (255,255,255), 2)

    cv2.imshow("Camera", frame)


    cv2.imshow("Camera", frame)

    key = cv2.waitKey(1) & 0xFF
    if key in [ord('q'), ord('Q')]:
        break

cap.release()
cv2.destroyAllWindows()
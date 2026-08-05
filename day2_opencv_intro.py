import cv2                                          # 匯入 OpenCV 套件，提供影像處理與電腦視覺的核心 API（如控制攝影機、顯示視窗與儲存圖片）

cap = cv2.VideoCapture(0)                           # 建立影像擷取物件；傳入參數 0 代表開啟並讀取電腦預設的內建攝影機（1 則為外接鏡頭）
count = 0                                           # 初始化截圖計數器變數，紀錄目前已儲存的照片張數，以便自動產生編號檔名

while True:                                         # 建立無窮迴圈，不斷重複執行讀取與顯示畫面的動作，進而呈現出動態影片（視訊串流）效果
    ret, frame = cap.read()                         # 從鏡頭擷取一幀畫面；ret 為 True/False 紀錄讀取是否成功，frame 為該張畫面的影像矩陣資料
    cv2.imshow("Camera", frame)                     # 將讀取到的 frame 影像繪製到標題為 "Camera" 的 GUI 視窗中進行即時預覽

    # 練習3:轉灰階
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cv2.imshow("Gray", gray)

    # 練習4:模糊處理
    blur = cv2.GaussianBlur(frame, (15, 15), 0)
    cv2.imshow("Blur", blur)

    # 練習5:邊緣偵測(要先轉灰階才能做)
    edges = cv2.Canny(gray, 100, 200)
    cv2.imshow("Edges", edges)


    key = cv2.waitKey(1) & 0xFF                     # 暫停 1 毫秒等待鍵盤輸入並刷新視窗畫面；& 0xFF 用於擷取跨平台標準的 8-bit ASCII 按鍵碼
    if key in [ord('q'), ord('Q')]:                 # 檢查按鍵碼是否等於字元 'q' 的 ASCII 碼（即使用者是否按下了 Q 鍵）
        break                                       # 跳出 while 無窮迴圈，準備結束視訊串流並關閉程式
    elif key in [ord('s'), ord('S')]:               # 檢查使用者是否按下了 S 鍵（代表 Screenshot 截圖功能）
        count += 1                                  # 截圖數量加 1，用於更新下一張照片的檔案編號
        filename = f"screenshot_{count}.png"        # 使用 f-string 格式化字串動態建立影像檔名（如 screenshot_1.png）
        cv2.imwrite(filename, frame)                # 將當前這一幀的影像矩陣 (frame) 以指定檔名 (filename) 寫入硬碟儲存為 PNG 圖檔
        print(f"已儲存 {filename}")                 # 在主控台（Terminal/Console）印出成功訊息，即時反饋給使用者

cap.release()                                       # 釋放攝影機硬體資源，關閉鏡頭並將控制權還給作業系統（鏡頭指示燈會熄滅）
cv2.destroyAllWindows()                             # 關閉所有由 OpenCV 所建立的 GUI 畫面視窗，完成系統資源清理
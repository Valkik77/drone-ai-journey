# Drone AI Journey

## 專案動機
說明你為什麼想做這個題目,跟無人機/AI視覺的興趣連結

## 目前完成的功能(依照天數列出)
- Day1: Python基礎、開發環境建置
- Day2: OpenCV基礎影像處理(灰階、模糊、邊緣偵測)
- Day3: HSV顏色追蹤、多物體框選、中心偏移量計算
- Day4: 動態偵測(影格差異法、背景相減法MOG2)
- Day5: 方向判斷邏輯與死區(deadzone)設計
- Day6: 程式碼重構、FPS效能監控
- Day7: 影片連結:https://drive.google.com/file/d/1cBRawfx2x6OdJi6wnm-D6SROSOBmG-YY/view?usp=drive_link

## 第二週進度(Day8-14)
- Day8: YOLO環境安裝,首次即時物件偵測
- Day9: 自訂繪圖取代內建plot(),加入信心分數過濾
- Day10: 類別篩選(鎖定特定物體),接上方向判斷邏輯
- Day11: 多目標處理,選擇離畫面中心最近的目標
- Day12: 效能測試與優化(640→320解析度,FPS約12→24提升)
- Day13: 程式碼重構為函式,提升可維護性
第二週從「只會辨識固定顏色」進化到「使用YOLOv8n辨識80種常見物體」,
並實作了完整的AI感知→決策流程:


## 第二週進度(Day15-)
- Day15: 
  懸停測試中,程式使用 p.connect(p.GUI) 開啟一個3D視覺化視窗,原本預期球體會因為施加的向上力而穩定懸停在畫面中。但實際執行時,終端機出現這樣的錯誤:
  pybullet.error: Not connected to physics server.
  將終端機的完整輸出給AI看的時候,回答發現在程式理論上還在跑迴圈的中途,就出現了:
    numActiveThreads = 0
    stopping threads
    finished
  意思是PyBullet的物理伺服器執行緒自己終止了,不是程式邏輯錯誤和操作上按錯按鍵

  按照回答時給的指示
    先檢查是不是誤觸鍵盤中斷程式(KeyboardInterrupt)——結果還是一樣
    檢查一下終端機輸出的執行緒訊息(ExampleBrowserThreadFunc、MotionThreadFunc),和畫面的顯示卡資訊:
      Vendor = Intel
      Renderer = Intel(R) Iris(R) Xe Graphics

  判斷問題似乎是 PyBullet 的即時3D渲染引擎(GUI模式)與我的筆電的內顯(Intel Iris Xe)之間存在相容性問題,所以視窗渲染執行緒在運作過程中意外終止,連帶讓物理模擬的連線也一併斷開

  之後改用 DIRECT 模式來解決問題
    PyBullet提供兩種連線模式:

    GUI模式(p.GUI)
    DIRECT模式(p.DIRECT)

    改用 p.connect(p.DIRECT) 後,完全跳過了容易出問題的3D渲染這一步,只保留核心的物理運算(重力、施力、位置計算),這部分運算穩定不受顯示卡影響,問題因此解決。
    用圖表取代視覺化觀察
    用 p.getBasePositionAndOrientation() 取得球體當下的座標,把高度(z軸)數值逐一記錄進一個list,模擬跑完後用 matplotlib 把整個過程的高度變化畫成折線圖，方便觀察結果。



- 技術棧:YOLOv8n(Ultralytics)、信心分數過濾、類別篩選、多目標決策
- 效能:640解析度平均FPS約12-14,降至320解析度後提升至約20-25
- 觀察到的模型限制:對訓練資料中罕見角度物體辨識率下降、相似形狀物體
  容易誤判(已透過信心分數門檻0.6緩解)
- 遇到並解決的問題:cv2.imshow畫框順序問題、mask破碎需形態學運算處理、
  FPS計算除以零的邊界情況

## 使用技術
Python, OpenCV, NumPy

## 如何執行
1. 建立虛擬環境:`python -m venv venv`
2. 啟用虛擬環境:`.\venv\Scripts\Activate.ps1`
3. 安裝套件:`pip install opencv-python numpy`
4. 執行:`python day6_refactored.py`

## 開發過程中遇到的問題
(整理你這幾天debug過的經驗,例如cv2.imshow位置放錯的bug、
 venv沒正確啟用導致套件裝錯地方、HSV範圍調校...)
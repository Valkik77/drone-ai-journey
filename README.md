 # Drone AI Journey — 無人機AI視覺追蹤系統

## 專案動機
（你自己的話：為什麼想做這個題目，跟你CSE背景/興趣的連結）

## 系統概述
本專案從零開始，用20天時間，逐步建構一套「視覺感知 → AI決策 → 
物理反應」的無人機控制系統雛形。因應無實體硬體的限制，第三週改以
PyBullet物理引擎模擬無人機的施力與運動，驗證控制邏輯的正確性。

## 技術演進脈絡
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


## 第三週進度(Day15-)
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


## 第一週亮點:
- HSV顏色追蹤 + 多物體框選 + 方向判斷邏輯(Day1-7)

## 第二週亮點:
- YOLOv8n物件偵測 + 信心分數過濾 + 多目標決策(離中心最近)
- 效能分析:640→320解析度,FPS從約12提升到約24
- 觀察到的模型限制:相似形狀誤判、局部人體(手)誤判為person

## 第三週亮點:
- PyBullet物理模擬:懸停力學、水平移動施力
- 解決的技術挑戰:GUI顯示卡相容性問題(改用DIRECT模式)、
  OMP函式庫衝突(KMP_DUPLICATE_LIB_OK)、Windows PowerShell執行原則問題
- YOLO + PyBullet即時串接:視覺感知驅動物理模擬的完整閉環
- 平滑處理(deque移動平均)解決抖動問題
- 三項壓力測試驗證系統穩定性(目標消失/突然入鏡/多目標切換)
- 觀察到的物理現象:STAY狀態下的慣性漂移、方向切換時的S型轉折曲線

## 效能數據
（貼上你Day12整理的解析度對比表格）

## 已知限制與未來方向
- YOLOv8n對訓練資料中罕見角度物體辨識率下降
- 局部人體易誤判為person類別，可透過框面積或長寬比進一步過濾
- 目前施力控制為固定力，缺乏PID回饋機制，STAY狀態下仍有慣性漂移
- 未來可導入真實硬體(如DJI Tello EDU)驗證，或加入PID控制器提升穩定性

## Demo影片
[第一週：顏色追蹤展示](https://drive.google.com/file/d/1HHiVPZsytm1p4V_LugqAZVtY8-A6lJrS/view?usp=sharing)
[第二週：YOLO物件偵測展示](https://drive.google.com/file/d/1aFvg5TK8YyMEkwfbXb5qWWhHKYrPYITV/view?usp=sharing)
[第三週：即時整合最終展示](https://drive.google.com/file/d/16iHMEwoX0FAtpYZDc4s8OP_5PZmbttL2/view?usp=sharing
                        https://drive.google.com/file/d/1wlJZ50uZaNAIQQlGx2uDByH5-ySZy8v9/view?usp=sharing
                        https://drive.google.com/file/d/1WuBEx0zIUK1emY_hZdn68olpfNhRBgfg/view?usp=sharing)

## 開發過程中的技術挑戰與解決
（挑幾個你印象最深的debug故事，例如cv2.imshow位置錯誤、venv沒啟用、
 OMP衝突、GUI顯示卡問題——每個用2-3句話講清楚「問題→原因→解法」）

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
 # Drone AI Journey — 無人機AI視覺追蹤系統

## 專案動機
這三年台灣對無人機產值開始大幅的上升，隨著AI、自動化與國防需求快速發展，無人機早已從消費性產品走向國防偵蒐、基礎設施巡檢、農業、物流、公共安全等更多應用(具體例子:烏俄戰爭，烏克蘭使用無人機的攻勢讓原本預計3個月結束的戰爭到現在3年仍然沒有結果)，另外，無人機在救災與勘查場景中能有效降低第一線人員的風險，是我選擇這個題目的重要動機之一——希望透過學習AI視覺辨識與無人機控制的基礎邏輯，理解這類系統背後的技術原理。

## 系統概述
本專案從零開始，用20天時間，逐步建構一套「視覺感知 → AI決策 → 
物理反應」的無人機控制系統雛形。因應無實體硬體的限制，第三週改以
PyBullet物理引擎模擬無人機的施力與運動，驗證控制邏輯的正確性。

## 技術演進脈絡
## 目前完成的功能(依照天數列出)
- Day1: Python基礎、開發環境建置
- Day2: OpenCV基礎影像處理(灰階、模糊、邊緣偵測)
- Day3: HSV顏色追蹤、多物體框選、中心偏移量計算
- Day4: 動態偵測(背景相減法MOG2)
- Day5: 方向判斷邏輯與死區(deadzone)設計
- Day6: 程式碼重構、FPS效能監控
- Day7: 統整

## 第二週進度(Day8-14)
- Day8: YOLO環境安裝,首次即時物件偵測
- Day9: 自訂繪圖取代內建plot(),加入信心分數過濾
- Day10: 類別篩選(鎖定特定物體),接上方向判斷邏輯
- Day11: 多目標處理,選擇離畫面中心最近的目標
- Day12: 效能測試與優化(640→320解析度,FPS約12→24提升)
- Day13: 程式碼重構為函式,提升可維護性
- Day14: 第二週統整Demo(鎖定bottle類別,框選目標物並輸出方向指令)
第二週從「只會辨識固定顏色」進化到「使用YOLOv8n辨識80種常見物體」,
並實作了完整的AI感知→決策流程:

### 第三週進度：物理模擬與即時整合（Day15-19）
- PyBullet環境建置(遭遇Windows/Python 3.12編譯問題，改用Miniconda + Python 3.10解決)
- 懸停力學驗證(F=ma)、水平方向施力控制
- 解決GUI顯示卡相容性問題，改用DIRECT模式+資料視覺化驗證
- **核心成果**：YOLO即時偵測 + PyBullet模擬的完整閉環整合
- 平滑處理(移動平均)降低雜訊造成的方向誤判
- 三項壓力測試（目標消失/突然入鏡/多目標切換）驗證系統穩定性


#### Day15除錯紀錄：GUI模式與內顯的相容性問題
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


#### Day19延伸優化：搜救情境功能擴充與除錯機制改良

在核心整合完成後，進一步延伸出更貼近搜救應用情境的功能：

**功能擴充**
- 多類別搜索：同時搜索多種可能有搜救價值的目標，並依優先度排序
  （活人優先於物品）。初版(`day19_enhanced_search.py`)搜索person、
  backpack、bottle；v2(`day19_enhanced_search_v2.py`)改為person、
  bottle、cell phone
- 持續搜索模式：目標消失時，執行週期性擺動搜索，取代原本的
  完全靜止，更貼近真實搜救無人機的行為邏輯
- 信心分數趨勢追蹤：要求連續多格畫面穩定維持高信心分數，
  才觸發「鎖定確認」，避免單一格畫面的雜訊誤報

**除錯機制改良**
初版測試過程中，發現終端機輸出資料在長時間測試下會被截斷，
無法回溯完整測試過程進行分析；同時模擬位置圖表因物理慣性
累積效果，即使實際來回移動，圖表仍可能呈現單調的位移趨勢，
難以清楚反映目標在畫面中的真實起伏動作。

透過加入CSV完整記錄機制(`day19_debug_log.csv`)，保留每一格畫面
的完整偵測與決策數據，不受終端機顯示限制；並新增「原始偏移量
視覺化」圖表(`day19_raw_position_result.png`)，直接呈現目標在
畫面中的實際相對位置變化，搭配threshold邊界線，與原本的「模擬
物理位置」圖表互補，能同時驗證「AI偵測是否正確」與「物理反應
是否合理」兩個不同層面，改善了系統驗證的完整性與可追溯性。

**排查過程中的關鍵發現**
一度誤判方向邏輯有誤（Y軸方向偵測不到UP指令），經過原始數據
逐層排查後確認：並非程式邏輯錯誤，而是person類別在webcam
視角下，身體中心點難以移動到畫面上半部，屬於人體結構與取景
角度的物理限制。改用bottle等較小物體測試後，證實UP方向判斷
邏輯完全正常運作。此過程也觀察到YOLO對bottle等手持晃動物體的
信心分數普遍低於穩定站立的person，容易觸發搜索模式，透過調整
信心分數門檻與擴充目標類別清單(加入cell phone)緩解此問題。

**後續優化(v2)**
- 框面積/長寬比過濾：框面積需佔畫面1%以上，person類別的框高寬比需≥0.5，
  濾掉手或局部肢體被誤判成person的情況(門檻原本設0.9，實測坐姿上半身
  的正常框約0.76會被誤濾，因此放寬到0.5)
- 模型由yolov8n.pt換成yolov8s.pt：不用蒐集新資料，直接換較大的預訓練
  模型提升準確度，代價是推論變慢(這台機器約36FPS降到23FPS)
- 施力改為連續PD控制：原本依方向指令施加固定大小的力(bang-bang控制)，
  目標回到中心後施力歸零但慣性不消，球體會一直漂移。改成施力與像素誤差
  成正比(P項)，再加上與速度成正比的阻尼(D項)，同樣情境下速度約2秒內
  衰減到接近0

### 延伸：Day20 手機遙控App
- `day20_phone_control_server.py`：在PyBullet DIRECT模擬外包一層
  asyncio/websockets伺服器(port 8765)，接收手機搖桿向量、回傳位置telemetry，
  並另開執行緒把webcam + YOLO偵測畫面串流給手機當參考
- `drone_control_app/`：Flutter App，包含虛擬搖桿與X/Y位置雷達圖
- 加入速度阻尼讓放開搖桿後1-2秒內停下，以及failsafe機制：超過0.5秒沒收到
  控制訊息就把施力歸零，避免斷線後無人機一直漂走
- 這是手動控制路徑，跟YOLO自動追蹤流程彼此獨立

### 延伸：Day21 空拍視角偵測
- `day21_aerial_search.py`：COCO預訓練模型的資料大多是地面平視角度，
  改用VisDrone空拍資料集微調的yolov8s權重(來源：Hugging Face
  dronefreak/visdrone-yolov8s，AGPL-3.0)
- 輸入可切換webcam或空拍影片檔；類別改用VisDrone的pedestrian/people等
- 偏移量正規化到[-1,1]，不同解析度的影片行為才一致；拿掉針對平視全身框
  設計的長寬比過濾，並調低框面積門檻以適應空拍小目標


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

## 效能數據(大致測量的)
情境      	640解析度	         320解析度
無人        	11.3	          16.4-21.8
1人         	13.8	          21.0-30.4
2人	          13.4	          20.8-25.0

## 已知限制與未來方向
- COCO預訓練模型對訓練資料中罕見角度物體辨識率下降(空拍視角已在Day21改用VisDrone微調模型嘗試改善)
- 局部人體易誤判為person類別：Day19 v2已加入框面積/長寬比過濾緩解，但無法完全消除
- 施力控制已從固定力改為PD控制(Day19 v2)，尚未加入積分項(I)，參數也只是手動調整
- 手持物體（如bottle）因晃動導致信心分數不穩定，較穩定站立的person類別更容易觸發搜索模式，反映YOLO對動態小物體的辨識限制
- 目前全部在PyBullet模擬中驗證，未來可導入真實硬體(如DJI Tello EDU)測試
- 手機遙控App(Day20)目前只能手動控制模擬無人機，尚未跟YOLO自動追蹤流程整合

## Demo影片
[第一週：顏色追蹤展示](https://drive.google.com/file/d/1HHiVPZsytm1p4V_LugqAZVtY8-A6lJrS/view?usp=sharing)
[第二週：YOLO物件偵測展示](https://drive.google.com/file/d/1aFvg5TK8YyMEkwfbXb5qWWhHKYrPYITV/view?usp=sharing)
[第三週：即時整合最終展示](https://drive.google.com/file/d/16iHMEwoX0FAtpYZDc4s8OP_5PZmbttL2/view?usp=sharing
                        https://drive.google.com/file/d/1wlJZ50uZaNAIQQlGx2uDByH5-ySZy8v9/view?usp=sharing
                        https://drive.google.com/file/d/1WuBEx0zIUK1emY_hZdn68olpfNhRBgfg/view?usp=sharing)

## 第二週技術摘要

- 技術棧:YOLOv8n(Ultralytics)、信心分數過濾、類別篩選、多目標決策
- 效能:640解析度平均FPS約12-14,降至320解析度後提升至約20-25
- 觀察到的模型限制:對訓練資料中罕見角度物體辨識率下降、相似形狀物體
  容易誤判(已透過信心分數門檻0.6緩解)
- 遇到並解決的問題:cv2.imshow畫框順序問題、mask破碎需形態學運算處理、
  FPS計算除以零的邊界情況

## 使用技術
Python, OpenCV, NumPy, YOLOv8(Ultralytics), PyBullet, matplotlib, asyncio/websockets, Flutter

## 如何執行
**Day1-14(OpenCV/YOLO)**：使用根目錄的venv(Python 3.12)
1. 建立虛擬環境:`python -m venv venv`
2. 啟用虛擬環境:`.\venv\Scripts\Activate.ps1`
3. 安裝套件:`pip install opencv-python numpy ultralytics`
4. 執行:例如 `python day6_refactored.py`、`python day14_final_demo.py`

**Day15之後(PyBullet)**：PyBullet在Python 3.12上編譯不過，改用Miniconda的Python 3.10環境
1. `conda create -n drone_sim python=3.10`，`conda activate drone_sim`
2. `pip install pybullet opencv-python numpy ultralytics matplotlib websockets`
3. 執行:例如 `python day19_enhanced_search_v2.py`

**Day20手機遙控**：先在drone_sim環境執行 `python day20_phone_control_server.py`，
再到 `drone_control_app/` 執行 `flutter pub get` 與 `flutter run`，在App輸入伺服器顯示的IP:port
# CLAUDE.md

本檔案提供給Claude Code（claude.ai/code）在這個repo裡工作時參考的指引。

## 專案概述

這是一個為期20天的自主學習專案，從零開始建構一套「視覺感知 → AI決策 → 物理反應」的無人機控制流程，逐日記錄在 `README.md`。第一週（Day1-7）：OpenCV顏色追蹤。第二週（Day8-14）：YOLOv8物件偵測。第三週（Day15-19）：PyBullet物理模擬，把YOLO偵測結果串接進去驅動模擬無人機的施力，形成完整閉環。超出原本20天規劃之外，`day20_phone_control_server.py` + `drone_control_app/` 額外新增了一支Flutter手機App，透過WebSocket用搖桿手動控制同一套PyBullet模擬，是獨立於YOLO自動追蹤流程之外的另一條路徑。

## 兩套Python環境——不能混用

- **`venv/`**（根目錄，Python 3.12.9）：裝了 `opencv-python`、`ultralytics`/`torch`、`numpy`、`matplotlib`。用於Day1-14的腳本（顏色追蹤、動態偵測、YOLO偵測）——沒有 `pybullet`，也沒有 `websockets`。
  - 啟用方式：`.\venv\Scripts\Activate.ps1`
- **Miniconda環境 `drone_sim`**（`C:\Users\USER\miniconda3\envs\drone_sim`，Python 3.10.20）：同一套技術棧再加上 `pybullet` 和 `websockets`。任何Day15之後的腳本以及 `day20_phone_control_server.py` 都需要用這個環境，因為 `pybullet` 在這台機器的Python 3.12上編譯不過（詳見README的Day15段落）。
  - 啟用方式：`conda activate drone_sim`，或直接呼叫該環境的直譯器：`C:\Users\USER\miniconda3\envs\drone_sim\python.exe <script>.py`
- 沒有 `requirements.txt`——每個階段需要什麼套件就直接 `pip install` 進對應的環境（例如 `pip install opencv-python numpy`）。修改腳本前先確認它import了什麼套件，不要假設某個環境一定裝了什麼。
- 所有會用到PyBullet的腳本都在最前面設定 `os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"`，這是為了避免YOLO和PyBullet之間的OpenMP函式庫衝突——修改這些腳本時要保留這行。
- PyBullet一定要用 `p.connect(p.DIRECT)`，不能用 `p.GUI`——GUI模式的即時渲染器跟這台筆電的Intel Iris Xe內顯不相容，會讓物理伺服器執行緒無聲無息地終止。模擬結果改用matplotlib畫成PNG圖表驗證（見各個 `dayN_*_result.png`），`day20_phone_control_server.py` 則是即時把座標當telemetry傳出去。

## 執行Day腳本

根目錄底下每個 `dayN_*.py` 都是獨立執行的腳本（`python dayN_xxx.py`），不是共用函式庫——詳見下方架構說明。有讀取webcam的腳本用 `cv2.VideoCapture(0)`（預設攝影機編號0），並開啟 `cv2.imshow` 視窗，按 `q` 結束。PyBullet腳本是無頭（headless）執行，跑完會輸出圖表/CSV（例如 `day19_enhanced_search_v2.py` 會寫出 `day19_debug_log.csv`、`day19_enhanced_result.png`、`day19_raw_position_result.png`）。

## 手機搖控App（day20_phone_control_server.py + drone_control_app/）

1. 啟動伺服器（需要 `drone_sim` 環境）：`C:\Users\USER\miniconda3\envs\drone_sim\python.exe day20_phone_control_server.py` ——會印出可連線的區網IP，監聽8765 port。
2. 從 `drone_control_app/` 執行Flutter App：
   - `flutter pub get` —— 安裝依賴套件
   - `flutter analyze` —— 靜態分析
   - `flutter test` —— 執行widget測試（`test/widget_test.dart`）
   - `flutter run -d chrome` / `-d windows` / 接實機 —— 在App的連線欄輸入伺服器的IP:port（手機跟電腦要在同一個Wi-Fi；用實機測試時，該port可能需要在Windows防火牆開放對外連入的規則）
   - `flutter pub add <package>` 來新增依賴（讓pub自動解析正確版本，不要手動改 `pubspec.yaml` 猜版本號）

## 架構

### Day腳本是逐日快照，不是共用函式庫

腳本彼此之間不會互相import。邏輯（例如 `get_direction()`、`direction_to_force()`、YOLO候選目標篩選）是從前一天的檔案複製過來，逐步演進到下一天，而不是重構成共用模組。修bug或改行為時，要直接修改當下實際在用的那個 `dayN_*.py` 檔案——不要以為改了較早那天的版本會影響到後面幾天的版本，也不要假設有一個共用模組改一次就全部生效。

### 感知→決策→物理的決策迴圈（Day17/Day19）

`day19_enhanced_search_v2.py`（目前整合最完整的版本）的核心迴圈是：
1. YOLO在webcam畫面裡偵測物體 → `detect_candidates()` 依類別/信心分數過濾，算出每個候選目標與畫面中心的像素偏移量。
2. `select_target()` 依 `(CLASS_PRIORITY, 與中心的距離)` 選出一個目標。
3. 偏移量先用移動平均（`deque`）平滑處理，再透過 `get_direction()` 依像素距離的死區(deadzone)/門檻值轉成方向指令（`UP`/`DOWN`/`LEFT`/`RIGHT`/`STAY`）。
4. `direction_to_force()` 把方向指令轉成 `(fx, fy)`；找不到目標時改用 `search_pattern()` 產生正弦波擺動搜索。
5. 用 `p.applyExternalForce(droneId, -1, [fx, fy, hover_force], ...)` + `p.stepSimulation()` 把力施加到PyBullet裡，其中 `hover_force = mass * 9.8` 讓球體維持懸停。
6. 位置歷史與每一格的決策數據會記錄成CSV/圖表，供事後驗證——因為PyBullet是用 `DIRECT` 模式執行，沒有即時畫面可看。

### 手機手動控制路徑（跟上面的流程平行，沒有整合在一起）

`day20_phone_control_server.py` 自己跑一份PyBullet的 `DIRECT` 模擬，搭配一個 `asyncio`/`websockets` 伺服器；它完全不碰webcam或YOLO。每個連線的處理函式（`handle_client`）透過 `asyncio.gather` 同時跑一個接收迴圈和一個telemetry傳送迴圈。協定是純JSON over WebSocket：
- Client → 伺服器：`{"x": -1..1, "y": -1..1}`（搖桿向量），由App用節流計時器定期送出，而不是每次觸控事件都送。
- 伺服器 → Client：`{"x", "y", "z", "fx", "fy"}` telemetry，以固定頻率送出，跟模擬步進的頻率是分開的。
- 有一個failsafe機制（`FAILSAFE_TIMEOUT`）：如果太久沒收到控制訊息就把施力歸零，避免斷線後無人機一直往同方向漂走。

`drone_control_app/lib/` 的結構：`main.dart`（進入點/主題）→ `screens/control_screen.dart`（管理連線狀態、搖桿傳送用的 `Timer.periodic`，並組合其他元件）→ `services/drone_socket_service.dart`（包裝 `WebSocketChannel`，透過 `ValueNotifier` 曝露 `ConnectionStatus`/`Telemetry`）以及 `widgets/joystick.dart` + `widgets/position_radar.dart`（純顯示用元件；雷達圖的座標軸定義——往上/Y正值代表「前」——刻意跟Python那邊 `direction_to_force()` 對UP指令的處理方式保持一致，即使兩邊完全沒有共用程式碼）。

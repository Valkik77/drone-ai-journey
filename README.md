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

## 第二週進度(Day8-13)
- Day8: YOLO環境安裝,首次即時物件偵測
- Day9: 自訂繪圖取代內建plot(),加入信心分數過濾
- Day10: 類別篩選(鎖定特定物體),接上方向判斷邏輯
- Day11: 多目標處理,選擇離畫面中心最近的目標
- Day12: 效能測試與優化(640→320解析度,FPS約12→24提升)
- Day13: 程式碼重構為函式,提升可維護性
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
import cv2
import numpy as np

img = np.zeros((400, 400, 3), dtype="uint8")
cv2.rectangle(img, (50, 50), (200, 200), (0, 255, 0), 2)
cv2.circle(img, (300, 300), 50, (255, 0, 0), -1)
cv2.putText(img, "Hello", (100, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
cv2.imshow("Draw", img)
cv2.waitKey(0)
cv2.destroyAllWindows()  # 建議補這行,讓視窗確實關閉乾淨
import cv2

cap = cv2.VideoCapture(0)
backSub = cv2.createBackgroundSubtractorMOG2()

while True:
    ret, frame = cap.read()
    fg_mask = backSub.apply(frame)
    cv2.imshow("Foreground Mask", fg_mask)

    contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        if cv2.contourArea(c) > 500:
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

    cv2.imshow("Camera", frame)

    key = cv2.waitKey(1) & 0xFF
    if key in [ord('q'), ord('Q')]:
        break

cap.release()
cv2.destroyAllWindows()
import cv2

vid = cv2.VideoCapture('pen_video.mov')
detector = cv2.createBackgroundSubtractorMOG2()

while True:
    ret, frame = vid.read()
    if ret is False:
        break

    mask = detector.apply(frame)
    _, mask = cv2.threshold(mask, 254, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        if cv2.contourArea(c) > 100:
            # cv2.drawContours(frame, [c], -1, (0, 255, 0), 2)
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)

    cv2.imshow('Frame', frame)
    cv2.imshow('Mask', mask)
    mask = detector.apply(frame)

    key = cv2.waitKey(30)
    if key == ord('q'):
        break

vid.release()
cv2.destroyAllWindows()

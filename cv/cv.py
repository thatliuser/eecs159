import cv2
import numpy as np

vid = cv2.VideoCapture('pen_video.mov')
tracker = None

#for skip in range(5):
#    _, _ = vid.read()

while True:
    ret, frame = vid.read()
    if ret is False:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Create a binary mask where the black areas are white
    # Here we define "black" as pixels with intensity < 50 (you can adjust this threshold)
    _, mask = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY_INV)
    bg = np.zeros_like(frame)
    cv2.imshow('Filtered', mask)

    if tracker is None:
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(frame, contours, -1, (255, 0, 0), 3)
        max_c = None
        max_area = 0
        for c in contours:
            area = cv2.contourArea(c)
            if area > max_area:
                max_area = area
                max_c = c

        if max_c is None:
            continue
        else:
            box = cv2.boundingRect(max_c)
            print('Init', box)
            x, y, w, h = [int(v) for v in box]
            tracker = cv2.TrackerKCF_create()
            tracker.init(frame, box)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
    else:
        success, box = tracker.update(frame)
        if success:
            print(box)
            x, y, w, h = [int(v) for v in box]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
        else:
            print('Failed: ', box)
            tracker = None

    cv2.imshow('objs', frame)

    key = cv2.waitKey(0)
    if key == ord('q'):
        break

vid.release()
cv2.destroyAllWindows()

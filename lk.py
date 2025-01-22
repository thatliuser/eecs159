import cv2
import numpy as np

def lucas_kanade_method(video_path, skip_frames):
    # Read the video 
    cap = cv2.VideoCapture(video_path)

    for _ in range(skip_frames):
        ret, _ = cap.read()  # Read and discard `skip_frames` number of frames
 
    # Parameters for ShiTomasi corner detection
    feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)
 
    # Parameters for Lucas Kanade optical flow
    lk_params = dict(
        winSize=(15, 15),
        maxLevel=2,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03),
    )
 
    # Create random colors
    color = np.random.randint(0, 255, (100, 3))
 
    # Take first frame and find corners in it
    ret, old_frame = cap.read()
    old_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)
    p0 = cv2.goodFeaturesToTrack(old_gray, mask=None, **feature_params)
 
    # Create a mask image for drawing purposes
    mask = np.zeros_like(old_frame)

    # Highlight the good features to track
    for i in range(len(p0)):
        x, y = p0[i].ravel().astype(int)  # Get the coordinates of each corner
        cv2.circle(old_frame, (x, y), 5, (0, 255, 0), -1)  # Draw a circle on each good feature
    
    # Display the initial frame with highlighted feature points
    cv2.imshow("Good Features to Track", old_frame)
    cv2.waitKey(0)  # Wait until a key is pressed before closing the window

    while True:
        # Read new frame
        ret, frame = cap.read()
        if not ret:
            break
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
     
        # Calculate Optical Flow
        p1, st, err = cv2.calcOpticalFlowPyrLK(
            old_gray, frame_gray, p0, None, **lk_params
        )

        if p1 is not None and st is not None:
            good_new = p1[st == 1]
            good_old = p0[st == 1]
    
            # Draw the tracks
            for i, (new, old) in enumerate(zip(good_new, good_old)):
                a, b = new.ravel().astype(int)  # Convert to integers
                c, d = old.ravel().astype(int)  # Convert to integers
                mask = cv2.line(mask, (a, b), (c, d), color[i].tolist(), 2)
                frame = cv2.circle(frame, (a, b), 5, color[i].tolist(), -1)
        else:
            print("Optical flow tracking failed for this frame.")
     
        # Display the demo
        img = cv2.add(frame, mask)
        cv2.imshow("frame", img)
        k = cv2.waitKey(25) & 0xFF
        if k == 27:
            break
     
        # Update the previous frame and previous points
        old_gray = frame_gray.copy()
        p0 = good_new.reshape(-1, 1, 2)

lucas_kanade_method('pen_video.mov', 50)

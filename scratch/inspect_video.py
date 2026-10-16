import cv2

cap = cv2.VideoCapture('scratch/test_download.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Resolution: {width}x{height}")
print(f"FPS: {fps}")
print(f"Total frames: {total_frames}")
print(f"Duration: {duration:.2f} seconds")

# Extract frames at 1.0s, 3.0s, 5.0s, 7.0s
for sec in [1.0, 3.0, 5.0, 7.0]:
    frame_idx = int(sec * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(f'scratch/frame_{int(sec)}s.jpg', frame)
        print(f"Saved frame at {sec}s")

cap.release()

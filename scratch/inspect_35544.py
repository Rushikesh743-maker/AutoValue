import cv2

cap = cv2.VideoCapture('scratch/dark_suv_35544.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Resolution: {width}x{height}")
print(f"FPS: {fps}")
print(f"Total frames: {total_frames}")
print(f"Duration: {duration:.2f} seconds")

# Extract 5 frames throughout the video
checkpoints = [0.1, duration * 0.25, duration * 0.5, duration * 0.75, duration - 0.2]
for i, sec in enumerate(checkpoints):
    frame_idx = int(sec * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(f'scratch/suv_35544_f{i}.jpg', frame)
        print(f"Saved frame {i} at {sec:.2f}s")

cap.release()

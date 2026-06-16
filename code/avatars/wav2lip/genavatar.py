from os import listdir, path
import numpy as np
import scipy, cv2, os, sys, argparse
import json, subprocess, random, string
from tqdm import tqdm
from glob import glob
import torch
import pickle
from avatars.wav2lip import face_detection


device = 'cuda' if torch.cuda.is_available() else 'cpu'
print('Using {} for inference.'.format(device))

def osmakedirs(path_list):
    for path in path_list:
        os.makedirs(path) if not os.path.exists(path) else None

def video2imgs(vid_path, save_path, ext='.png', cut_frame=10000000, max_side=1280):
    cap = cv2.VideoCapture(vid_path)
    count = 0
    while True:
        if count > cut_frame:
            break
        ret, frame = cap.read()
        if ret:
            h, w = frame.shape[:2]
            if max(h, w) > max_side:
                scale = max_side / max(h, w)
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
            cv2.putText(frame, "LiveTalking", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (128, 128, 128), 1)
            cv2.imwrite(f"{save_path}/{count:08d}.png", frame)
            count += 1
        else:
            break

def read_imgs(img_list):
    frames = []
    print('reading images...')
    for img_path in tqdm(img_list):
        frame = cv2.imread(img_path)
        frames.append(frame)
    return frames

def get_smoothened_boxes(boxes, T):
    for i in range(len(boxes)):
        if i + T > len(boxes):
            window = boxes[len(boxes) - T:]
        else:
            window = boxes[i: i + T]
        boxes[i] = np.mean(window, axis=0)
    return boxes


def generate_avatar(video_path, avatar_id, save_path='./data/avatars', img_size=96,
                    pads=[0, 10, 0, 0], nosmooth=False, face_det_batch_size=16, progress_callback=None):
    """
    Generate avatar data from video.
    - full_imgs saved at original resolution
    - face detection uses per-frame downscaled thumbnails (avoids 4K OOM)
    - face crops taken from original full-size frames
    - reads frames one-at-a-time to avoid 6GB RAM usage
    """
    avatar_path = os.path.join(save_path, avatar_id)
    full_imgs_path = os.path.join(avatar_path, "full_imgs")
    face_imgs_path = os.path.join(avatar_path, "face_imgs")
    coords_path = os.path.join(avatar_path, "coords.pkl")

    osmakedirs([avatar_path, full_imgs_path, face_imgs_path])
    if progress_callback: progress_callback(5)

    print(f"Processing video: {video_path}")
    video2imgs(video_path, full_imgs_path, ext='png')
    if progress_callback: progress_callback(20)

    input_img_list = sorted(glob(os.path.join(full_imgs_path, '*.[jpJP][pnPN]*[gG]')))
    num_frames = len(input_img_list)

    # --- Determine scaling ---
    sample = cv2.imread(input_img_list[0])
    orig_h, orig_w = sample.shape[:2]
    del sample
    DETECT_MAX = 1280
    scale = min(DETECT_MAX / orig_w, DETECT_MAX / orig_h)
    if scale < 1.0:
        detect_w, detect_h = int(orig_w * scale), int(orig_h * scale)
        print(f"Original {orig_w}x{orig_h}, detection thumbnails: {detect_w}x{detect_h}")
    else:
        detect_w, detect_h = orig_w, orig_h
        scale = 1.0
        print(f"Resolution {orig_w}x{orig_h}, no downscale needed")

    inv_scale = 1.0 / scale if scale < 1.0 else 1.0
    if progress_callback: progress_callback(40)

    # --- PASS 1: face detection on thumbnails (one-at-a-time) ---
    print('Detecting faces (on thumbnails)...')
    detector = face_detection.FaceAlignment(face_detection.LandmarksType._2D,
                                            flip_input=False, device=device)

    batch_size = face_det_batch_size
    predictions = []

    while True:
        predictions = []
        detect_batch = []
        try:
            for i, img_path in enumerate(input_img_list):
                raw = cv2.imread(img_path)
                if scale < 1.0:
                    df = cv2.resize(raw, (detect_w, detect_h))
                else:
                    df = raw
                del raw
                detect_batch.append(df)

                if len(detect_batch) >= batch_size:
                    preds = detector.get_detections_for_batch(np.array(detect_batch))
                    predictions.extend(preds)
                    detect_batch = []
                    if progress_callback:
                        p = 40 + int(i / num_frames * 40)
                        progress_callback(min(p, 80))

            if detect_batch:
                preds = detector.get_detections_for_batch(np.array(detect_batch))
                predictions.extend(preds)

            if progress_callback: progress_callback(80)
            break

        except RuntimeError:
            if batch_size == 1:
                raise RuntimeError('Image too big to run face detection on GPU.')
            batch_size //= 2
            print(f'Recovering from OOM error; New batch size: {batch_size}')
            continue

    # --- Compute boxes (thumbnail coords -> original coords) ---
    pady1, pady2, padx1, padx2 = pads
    results = []
    for rect, img_path in zip(predictions, input_img_list):
        raw = cv2.imread(img_path)
        if rect is None:
            rect = [0, 0, raw.shape[1], raw.shape[0]]

        y1 = max(0, rect[1] * inv_scale - pady1)
        y2 = min(raw.shape[0], rect[3] * inv_scale + pady2)
        x1 = max(0, rect[0] * inv_scale - padx1)
        x2 = min(raw.shape[1], rect[2] * inv_scale + padx2)
        results.append([x1, y1, x2, y2])
        del raw

    boxes = np.array(results)
    if not nosmooth:
        boxes = get_smoothened_boxes(boxes, T=5)

    if progress_callback: progress_callback(85)

    # --- PASS 2: crop faces from full-size frames ---
    coord_list = []
    print("Saving face images and coordinates...")
    for idx, (rect, img_path) in enumerate(zip(boxes, input_img_list)):
        raw = cv2.imread(img_path)
        face_frame = raw[int(rect[1]):int(rect[3]), int(rect[0]):int(rect[2])]
        resized_crop_frame = cv2.resize(face_frame, (img_size, img_size))
        cv2.imwrite(f"{face_imgs_path}/{idx:08d}.png", resized_crop_frame)
        coord_list.append((int(rect[1]), int(rect[3]), int(rect[0]), int(rect[2])))
        del raw

        if progress_callback:
            progress = 85 + int((idx + 1) / len(boxes) * 15)
            progress_callback(progress)

    print(f"Writing coordinates to: {coords_path}")
    with open(coords_path, 'wb') as f:
        pickle.dump(coord_list, f)

    del detector
    if progress_callback: progress_callback(100)
    print("Avatar generation complete!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate avatar data from video')
    parser.add_argument('--img_size', default=96, type=int)
    parser.add_argument('--avatar_id', default='wav2lip_avatar1', type=str)
    parser.add_argument('--save_path', default='data/avatars', type=str)
    parser.add_argument('--video_path', default='', type=str)
    parser.add_argument('--nosmooth', default=False, action='store_true',
                        help='Prevent smoothing face detections over a short temporal window')
    parser.add_argument('--pads', nargs='+', type=int, default=[0, 10, 0, 0],
                        help='Padding (top, bottom, left, right). Please adjust to include chin at least')
    parser.add_argument('--face_det_batch_size', type=int,
                        help='Batch size for face detection', default=16)
    args = parser.parse_args()

    generate_avatar(
        video_path=args.video_path,
        avatar_id=args.avatar_id,
        save_path=args.save_path,
        img_size=args.img_size,
        pads=args.pads,
        nosmooth=args.nosmooth,
        face_det_batch_size=args.face_det_batch_size
    )

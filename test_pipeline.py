import cv2
import json
import os
import time
from ultralytics import YOLO

# =========================================================
# SETTINGS — change these
# =========================================================

# MODEL_1_PATH = r"Model 2 - Gloves,Goggles -best.pt"   # detects: gloves, goggles
MODEL_1_PATH = r"Gloves, Goggles best new.pt"
MODEL_2_PATH = r"Fine-Tuned Model\best (1).pt"         # detects: person, helmet, vest, boots

VIDEO_PATH = r"SafeVisionAI - Airport\Videos\Airport Video (1).mp4"


OUTPUT_DIR = r"SafeVisionAI-detections\output"
SCREENSHOTS_DIR = os.path.join(OUTPUT_DIR, "screenshots")
LOG_FILE = os.path.join(OUTPUT_DIR, "detections.json")

REQUIRED_FRAMES = 30          # frames needed in a row to confirm a status
CONF_THRESHOLD = 0.5        # lower this (e.g. 0.3) if nothing is detecting
EQUIPMENT_TYPES = ["helmet", "vest", "boots", "goggles", "gloves"]

# ROI margin as a PERCENTAGE of the video's actual width/height, not fixed
# pixels. This way the green box always sits inside the frame and stays
# centered, no matter what resolution the video is.
ROI_MARGIN_PERCENT = 0.04     # 4% inset from each edge — increase to shrink the box

SHOW_WINDOW = True
DEVICE = 0                    # change to "cpu" if you don't have a GPU

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


# =========================================================
# SMALL HELPER FUNCTIONS
# =========================================================

def normalize(name):
    return name.lower().replace("-", " ").replace("_", " ").strip()


def classify_class(raw_name):
    """Turns a raw model class name into (equipment, is_present) or ('person', None)."""
    n = normalize(raw_name)
    if n == "person":
        return ("person", None)
    for eq in EQUIPMENT_TYPES:
        if eq in n:
            is_present = "no" not in n
            return (eq, is_present)
    return None  # class we don't care about


def is_inside(item_box, person_box):
    ix1, iy1, ix2, iy2 = item_box
    px1, py1, px2, py2 = person_box
    cx, cy = (ix1 + ix2) / 2, (iy1 + iy2) / 2
    return px1 <= cx <= px2 and py1 <= cy <= py2



print("Loading models...")
model_1 = YOLO(MODEL_1_PATH)
model_2 = YOLO(MODEL_2_PATH)
print("Model 1 (gloves/goggles) classes:", model_1.names)
print("Model 2 (helmet/vest/boots) classes:", model_2.names)
MODELS = [model_1, model_2]


true_counts = {}    # {person_id: {equipment: count}}
false_counts = {}   # {person_id: {equipment: count}}
status = {}          # {person_id: {equipment: True/False/None}}

log_data = {"people": {}, "violations": []}


def save_log():
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=2)



cap = cv2.VideoCapture(VIDEO_PATH)

# ---- figure out the ROI from the video's real dimensions ----
video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

margin_x = int(video_width * ROI_MARGIN_PERCENT)
margin_y = int(video_height * ROI_MARGIN_PERCENT)

ROI_X1, ROI_Y1 = margin_x, margin_y
ROI_X2, ROI_Y2 = video_width - margin_x, video_height - margin_y

print(f"Video resolution: {video_width}x{video_height}")
print(f"ROI box: ({ROI_X1},{ROI_Y1}) to ({ROI_X2},{ROI_Y2})")

if SHOW_WINDOW:
    cv2.namedWindow("SafeVisionAI Test", cv2.WINDOW_NORMAL)

frame_number = 0

while True:
    success, frame = cap.read()
    if not success:
        break

    roi_frame = frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]

    persons = []
    present_boxes = {}   # {equipment: [box, ...]}
    absent_boxes = {}
    # Start with the plain ROI image; each model draws its boxes ON TOP
    # of whatever the previous model already drew, so both models' boxes
    # show up together instead of the last one overwriting the first.
    combined_annotated = roi_frame.copy()

    # ---- run BOTH models on the same ROI ----
    for model in MODELS:
        # Both models run through .track() (confirmed working for Model 1
        # too). The important fix is below: we no longer require a track
        # ID for EQUIPMENT boxes (gloves/goggles/helmet/vest/boots) — only
        # the "person" class needs a persistent ID, since that's what the
        # streak counters are keyed on. Equipment boxes are used the
        # moment they're detected, ID or not.
        result = model.track(
            source=roi_frame,
            conf=CONF_THRESHOLD,
            tracker=r"SafeVisionAI - Airport\botsort_reid.yaml",
            persist=True,
            save=False,
            verbose=False,
            device=DEVICE,
        )[0]

        # Draw this model's boxes on top of the combined frame so far,
        # instead of replacing it — this way both models' boxes are
        # visible together in the display window.
        combined_annotated = result.plot(img=combined_annotated)

        boxes = result.boxes
        has_ids = boxes.id is not None
        track_ids = boxes.id.tolist() if has_ids else [None] * len(boxes.cls)

        for cls, track_id, box in zip(boxes.cls, track_ids, boxes.xyxy):
            raw_name = model.names[int(cls)]
            classified = classify_class(raw_name)
            if classified is None:
                continue
            eq, is_present = classified
            box = box.tolist()

            if eq == "person":
                # person MUST have a track_id — without it we can't build
                # streak counters across frames, so skip this box.
                if track_id is None:
                    continue
                persons.append((int(track_id), box))
            elif is_present:
                present_boxes.setdefault(eq, []).append(box)
            else:
                absent_boxes.setdefault(eq, []).append(box)

    # ---- update each detected person's streaks/status ----
    for person_id, person_box in persons:
        if person_id not in status:
            true_counts[person_id] = {eq: 0 for eq in EQUIPMENT_TYPES}
            false_counts[person_id] = {eq: 0 for eq in EQUIPMENT_TYPES}
            status[person_id] = {eq: None for eq in EQUIPMENT_TYPES}

        prev_status = dict(status[person_id])

        for eq in EQUIPMENT_TYPES:
            seen_present = any(is_inside(b, person_box) for b in present_boxes.get(eq, []))
            seen_absent = any(is_inside(b, person_box) for b in absent_boxes.get(eq, []))

            if seen_present:
                true_counts[person_id][eq] += 1
                false_counts[person_id][eq] = 0
            elif seen_absent:
                false_counts[person_id][eq] += 1
                true_counts[person_id][eq] = 0

            if true_counts[person_id][eq] >= REQUIRED_FRAMES:
                status[person_id][eq] = True
            if false_counts[person_id][eq] >= REQUIRED_FRAMES:
                status[person_id][eq] = False

        is_violating = any(v is False for v in status[person_id].values())

        log_data["people"][str(person_id)] = {
            **status[person_id],
            "violating": is_violating,
            "last_seen_frame": frame_number,
            "last_updated": time.time(),
        }

        # ---- log a violation + screenshot only on a CONFIRMED change ----
        if prev_status != status[person_id] and is_violating:
            missing = [eq for eq, v in status[person_id].items() if v is False]

            timestamp = time.time()
            filename = f"person{person_id}_frame{frame_number}_{int(timestamp)}.jpg"
            filepath = os.path.join(SCREENSHOTS_DIR, filename)

            x1, y1, x2, y2 = [int(v) for v in person_box]
            x1, y1 = x1 + ROI_X1, y1 + ROI_Y1
            x2, y2 = x2 + ROI_X1, y2 + ROI_Y1
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1 - 20), max(0, y1 - 20)
            x2, y2 = min(w, x2 + 20), min(h, y2 + 20)
            crop = frame[y1:y2, x1:x2]
            cv2.imwrite(filepath, crop if crop.size > 0 else frame)

            log_data["violations"].append({
                "person_id": person_id,
                "frame": frame_number,
                "missing": missing,
                "timestamp": timestamp,
                "screenshot": filepath.replace("\\", "/"),
            })
            print(f"VIOLATION -> person {person_id} missing {missing} at frame {frame_number}")

    save_log()

    # ---- display ----
    if SHOW_WINDOW:
        display_frame = frame.copy()
        display_frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2] = combined_annotated
        cv2.rectangle(display_frame, (ROI_X1, ROI_Y1), (ROI_X2, ROI_Y2), (0, 255, 0), 2)
        cv2.imshow("SafeVisionAI Test", display_frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    frame_number += 1

cap.release()
cv2.destroyAllWindows()

print(f"\nDone. {len(log_data['people'])} people tracked, {len(log_data['violations'])} violations logged.")
print(f"Log: {LOG_FILE}")
print(f"Screenshots: {SCREENSHOTS_DIR}")
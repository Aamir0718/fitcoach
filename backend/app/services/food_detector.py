from ultralytics import YOLO

model = YOLO("models/best.pt")

def detect_foods(image_path):
    results = model.predict(
        source=image_path,
        conf=0.25,
        verbose=False
    )

    detected = []

    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            detected.append(model.names[cls])

    return list(set(detected))
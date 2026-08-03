from ultralytics import YOLO

model = YOLO("models/best.pt")

results = model.predict(
    source="uploads/test.jpg",   # put any food image here
    conf=0.25,
    save=True
)

for r in results:
    for box in r.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        print(model.names[cls], round(conf, 2))
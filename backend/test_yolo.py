from ultralytics import YOLO

model = YOLO("models/best.pt")

print("Classes in the model:")
print(model.names)
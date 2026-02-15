from ultralytics import YOLO

# Load a model
model = YOLO("./models/Pose/yolo11x-pose.pt")  # load an official model

# Predict with the model
results = model("./data/images", save=True)  # predict on an image

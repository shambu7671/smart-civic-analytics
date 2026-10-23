"""Train a YOLO model after placing a compatible road-damage dataset locally."""
from pathlib import Path
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'ai' / 'training' / 'rdd2022.yaml'
BASE_MODEL = 'yolo11n.pt'  # Replace with a locally available compatible base/checkpoint.

model = YOLO(BASE_MODEL)
model.train(data=str(DATA), epochs=50, imgsz=640, project=str(ROOT / 'ai' / 'models'), name='rdd2022-road-damage')

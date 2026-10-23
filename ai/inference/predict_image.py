"""Minimal standalone inference example for a locally supplied YOLO checkpoint."""
import argparse
from pathlib import Path
from ultralytics import YOLO

parser=argparse.ArgumentParser()
parser.add_argument('--model', required=True)
parser.add_argument('--image', required=True)
parser.add_argument('--conf', type=float, default=0.55)
args=parser.parse_args()

model=YOLO(args.model)
results=model.predict(source=args.image, conf=args.conf, verbose=False)
for result in results:
    print(result.summary())

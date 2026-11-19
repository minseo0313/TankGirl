#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Raspberry Pi 4 dual NCNN object-detection latency benchmark (no GPIO/motors)."""
import argparse
import csv
import json
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path


def parse_args():
    yolo_dir = Path(__file__).resolve().parents[1]  # 저장소의 yolo/ 폴더
    p = argparse.ArgumentParser(description="Benchmark Person/Animal NCNN models on Raspberry Pi (no actuation).")
    p.add_argument('--person-model', type=Path, default=yolo_dir/'models/person_yolo26n_ncnn')
    p.add_argument('--animal-model', type=Path, default=yolo_dir/'models/animal_yolo26n_ncnn')
    p.add_argument('--source', choices=['camera', 'video', 'images'], default='camera')
    p.add_argument('--camera', type=int, default=0, help='OpenCV video capture index (USB/V4L2 camera)')
    p.add_argument('--video', type=Path, help='Video path if --source video')
    p.add_argument('--images', type=Path, help='Image folder if --source images')
    p.add_argument('--width', type=int, default=640)
    p.add_argument('--height', type=int, default=480)
    p.add_argument('--frames', type=int, default=40, help='Measured frames per benchmark mode')
    p.add_argument('--warmup', type=int, default=3, help='Unmeasured frames per benchmark mode')
    p.add_argument('--person-imgsz', type=int, default=416)
    p.add_argument('--animal-imgsz', type=int, default=640)
    p.add_argument('--conf', type=float, default=0.25)
    p.add_argument('--threads', type=int, default=2, help='CPU threads for PyTorch/OpenCV (NCNN may manage its own threads)')
    p.add_argument('--output', type=Path, default=yolo_dir/'benchmark/results')
    p.add_argument('--mode', choices=['all','person','animal','dual'], default='all')
    return p.parse_args()


def read_temp_c():
    path = Path('/sys/class/thermal/thermal_zone0/temp')
    try:
        return round(int(path.read_text().strip())/1000, 1)
    except (OSError, ValueError):
        return None


def percentile(values, pct):
    if not values:
        return None
    xs = sorted(values)
    i = (len(xs)-1)*pct/100
    lo = int(i)
    hi = min(lo+1, len(xs)-1)
    return xs[lo] + (xs[hi]-xs[lo])*(i-lo)


def report(values):
    return {
        'count': len(values),
        'mean_ms': round(statistics.mean(values), 2) if values else None,
        'median_ms': round(statistics.median(values), 2) if values else None,
        'p95_ms': round(percentile(values, 95), 2) if values else None,
    }


def main():
    args = parse_args()
    if args.frames < 1 or args.warmup < 0:
        raise SystemExit('--frames must be >=1 and --warmup >=0')
    if args.source == 'video' and not args.video:
        raise SystemExit('Video mode requires --video /path/to/video.mp4')
    if args.source == 'images' and not args.images:
        raise SystemExit('Images mode requires --images /path/to/folder')

    try:
        import cv2
        import numpy as np
        import torch
        from ultralytics import YOLO
    except ImportError as e:
        raise SystemExit(f'Missing dependency: {e}. Install ultralytics, opencv-python, numpy, torch in your Pi environment.')
    try:
        torch.set_num_threads(args.threads)
    except RuntimeError:
        pass
    cv2.setNumThreads(args.threads)

    for model_path in (args.person_model, args.animal_model):
        if not model_path.is_dir():
            raise SystemExit(f'Model directory not found: {model_path}')
        if not list(model_path.glob('*.param')) or not list(model_path.glob('*.bin')):
            raise SystemExit(f'NCNN .param/.bin not found in {model_path}. Copy complete export folder.')

    print('Loading NCNN models...')
    person_model = YOLO(str(args.person_model), task='detect')
    animal_model = YOLO(str(args.animal_model), task='detect')
    person_names = {int(k): str(v) for k, v in person_model.names.items()}
    animal_names = {int(k): str(v) for k, v in animal_model.names.items()}
    person_ids = [k for k,v in person_names.items() if v.strip().lower() == 'person']
    animal_ids = [k for k,v in animal_names.items() if v.strip().lower() in ('roe_deer','wild_boar')]
    if not person_ids or set(animal_names.values()).isdisjoint({'roe_deer','wild_boar'}):
        raise SystemExit(f'Unexpected model classes. person={person_names}; animal={animal_names}')
    print('Person classes:', person_ids, 'Animal classes:', animal_ids)

    cap = None
    image_files = None
    image_index = 0
    if args.source in ('camera','video'):
        camera_source = args.camera if args.source == 'camera' else str(args.video)
        cap = cv2.VideoCapture(camera_source)
        if not cap.isOpened():
            raise SystemExit(f'Cannot open {args.source} source: {camera_source}. For CSI/Picamera2, record a video and use --source video.')
        if args.source == 'camera':
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    else:
        if not args.images.is_dir():
            raise SystemExit(f'Image folder not found: {args.images}')
        image_files = sorted(x for x in args.images.iterdir() if x.suffix.lower() in {'.jpg','.jpeg','.png','.bmp','.webp'})
        if not image_files:
            raise SystemExit('No supported images in folder')

    def next_frame():
        nonlocal image_index
        if args.source == 'images':
            for _ in range(len(image_files)):
                fp = image_files[image_index % len(image_files)]
                image_index += 1
                im = cv2.imread(str(fp))
                if im is not None:
                    return im
            return None
        ok, frame = cap.read()
        if not ok and args.source == 'video':
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
        return frame if ok else None

    args.output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    details_path = args.output / f'dual_ncnn_frames_{stamp}.csv'
    summary_path = args.output / f'dual_ncnn_summary_{stamp}.json'
    stages = ['person','animal','dual'] if args.mode == 'all' else [args.mode]
    detailed = []
    summaries = {}

    def infer(model, frame, ids, imgsz):
        t0 = time.perf_counter()
        result = model.predict(source=frame, classes=ids, conf=args.conf,
                               imgsz=imgsz, device='cpu', verbose=False)[0]
        ms = (time.perf_counter() - t0) * 1000
        counts = {}
        names = model.names
        for box in result.boxes:
            cls = int(box.cls.item())
            name = str(names[cls])
            counts[name] = counts.get(name, 0) + 1
        return ms, counts

    try:
        for stage in stages:
            print(f'\n== {stage.upper()} | warmup={args.warmup}, measured={args.frames} ==', flush=True)
            person_ms_list, animal_ms_list, elapsed_ms_list, acquire_ms_list = [], [], [], []
            stage_start = time.perf_counter()
            samples_done = 0
            for i in range(args.warmup + args.frames):
                capture_start = time.perf_counter()
                frame = next_frame()
                acq_ms = (time.perf_counter()-capture_start)*1000
                if frame is None:
                    raise RuntimeError(f'Frame read failed during {stage} at index {i}.')
                infer_start = time.perf_counter()
                p_ms, a_ms = None, None
                p_counts, a_counts = {}, {}
                if stage in ('person','dual'):
                    p_ms, p_counts = infer(person_model, frame, person_ids, args.person_imgsz)
                if stage in ('animal','dual'):
                    a_ms, a_counts = infer(animal_model, frame, animal_ids, args.animal_imgsz)
                infer_ms = (time.perf_counter()-infer_start)*1000
                if i < args.warmup:
                    continue
                idx = i-args.warmup+1
                samples_done += 1
                if p_ms is not None: person_ms_list.append(p_ms)
                if a_ms is not None: animal_ms_list.append(a_ms)
                elapsed_ms_list.append(infer_ms)
                acquire_ms_list.append(acq_ms)
                detailed.append({
                    'mode': stage, 'frame': idx, 'capture_ms': round(acq_ms,2),
                    'person_ms': round(p_ms,2) if p_ms is not None else '',
                    'animal_ms': round(a_ms,2) if a_ms is not None else '',
                    'total_infer_ms': round(infer_ms,2),
                    'person_count': p_counts.get('person',0),
                    'roe_deer_count': a_counts.get('roe_deer',0),
                    'wild_boar_count': a_counts.get('wild_boar',0),
                    'temp_c': read_temp_c(),
                })
                if idx % 10 == 0 or idx == args.frames:
                    print(f'  {idx}/{args.frames}: total inference {infer_ms:.1f} ms; '
                          f'person={p_counts.get("person",0)}, '
                          f'roe_deer={a_counts.get("roe_deer",0)}, '
                          f'wild_boar={a_counts.get("wild_boar",0)}', flush=True)
            stage_wall = time.perf_counter()-stage_start
            # Mean inference-only throughput is distinct from end-to-end throughput.
            mean_infer_ms = statistics.mean(elapsed_ms_list)
            summaries[stage] = {
                'inference_total': report(elapsed_ms_list),
                'capture': report(acquire_ms_list),
                'person': report(person_ms_list),
                'animal': report(animal_ms_list),
                'inference_only_estimated_fps': round(1000/mean_infer_ms,2),
                # Includes all acquisition, warmups and bookkeeping, so not direct infer FPS.
                'mode_wall_seconds_including_warmup': round(stage_wall,2),
                'temperature_last_c': read_temp_c(),
                'frames_measured': samples_done,
            }
            print(f'  mean={mean_infer_ms:.1f} ms, p95={percentile(elapsed_ms_list,95):.1f} ms, '
                  f'inference-only estimated FPS={1000/mean_infer_ms:.2f}', flush=True)
    finally:
        if cap is not None:
            cap.release()

    with details_path.open('w', newline='', encoding='utf-8') as f:
        columns = ['mode','frame','capture_ms','person_ms','animal_ms','total_infer_ms',
                   'person_count','roe_deer_count','wild_boar_count','temp_c']
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(detailed)
    summary = {
        'timestamp': stamp, 'device': platform.platform(),
        'python': sys.version.split()[0], 'source': args.source,
        'person_model': str(args.person_model), 'animal_model': str(args.animal_model),
        'imgsz': {'person': args.person_imgsz, 'animal': args.animal_imgsz},
        'conf': args.conf, 'frames': args.frames, 'warmup': args.warmup,
        'mode_results': summaries,
        'notes': 'No GPIO or motor control. Latencies are wall-clock model.predict calls; camera capture is separate. FPS excludes driving CNN, display and actuator load.'
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print('\nCSV:', details_path)
    print('JSON:', summary_path)
    print('Done. This is a model-only benchmark, NOT full robot FPS or safety validation.')

if __name__ == '__main__':
    main()

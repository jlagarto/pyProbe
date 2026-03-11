# CLAUDE.md — pyProbe

## Project Overview
pyProbe is a PyQt5 desktop application for autofluorescence lifetime imaging (FLIM). It integrates multiple hardware instruments via a Model-View-Controller architecture.

## Running the App
```bash
venv\Scripts\activate
python main.py
```
Requires Python 3.10 (Spinnaker SDK wheel is built for cp310).

## Architecture

| Layer | Location | Responsibility |
|---|---|---|
| View | `views/MainWindow.py` + `MainWindow.ui` | PyQt5 GUI, loaded dynamically with `uic.loadUi` |
| Controllers | `controllers/` | Hardware abstraction (Harp, TimeTagger, Camera) |
| Instruments | `instruments/` | Low-level device drivers |
| Workers | `workers/` | QThread workers for non-blocking I/O |
| Utils | `utils/` | DataSaver (HDF5, video, log), ProcessingMode, config loader |

## Key Files
- `config.yaml` — all hardware parameters (channels, delays, trigger levels, COM ports, camera ROI)
- `utils/helpers.py` — `load_config()` reads config.yaml with PyYAML
- `views/MainWindow.py` — central orchestrator; initialises all hardware and workers on startup
- `workers/DataWorker.py` — polls TimeTagger histograms, emits signal per measurement
- `workers/FLIMWorker.py` — processes raw histogram data, emits processed results
- `workers/CameraWorker.py` — streams camera frames, runs spot tracking
- `utils/DataSaver.py` — `HistogramSaver`, `LogSaver`, `VideoSaver`, `ImageSaver`

## Hardware & Dependencies
| Device | Library | Notes |
|---|---|---|
| TimeTagger Ultra (Swabian) | `timetagger` (pip) | Channels: laser sync=1, det1=2, det2=3, ext=4 |
| Harp / Laser (B&H) | `harp-protocol`, `harp-serial`, `harp.laserdrivercontroller` | Serial, default COM5 |
| FLIR Camera | `PySpin` (Spinnaker wheel) | Bundled `.whl` for Python 3.10 |
| NeoPixel LED | `QSerialPort` (PyQt5) | Arduino on COM6 (override via `arduino_port` in config) |
| SPAD detectors (Hamamatsu) | via Harp | ON/OFF control |

## Acquisition Flow
1. `start_measurement()` → optional holdout countdown → `_start_actual_measurement()`
2. `DataWorker` runs in a QThread, polls histogram data, emits `signal` per measurement
3. `FLIMWorker` receives signal, processes data, emits `processed` to `update_measurement()`
4. `CameraWorker` streams frames independently; `measurement_index_changed` signal synchronises frame/measurement indices
5. `stop_measurement()` stops threads, records metadata, enables save button

## Data Saving
Folder name format: `YYYYMMDD_HHMMSS_<type>.<label>/`
- `ch1.h5` / `ch2.h5` — FLIM histograms (HDF5 via h5py)
- log file — histogram indices + timestamps
- `video.avi` + video log — frames with spot tracking data

## Acquisition Modes
- **solution** — 200 measurements, no image processing, holdout=0
- **in vivo / ex vivo** — 15000 measurements, image processing enabled, holdout from config

## Push Log

| Date | Commit | Description |
|---|---|---|
| 2026-03-10 | f664a96 | Update README and add CLAUDE.md |
| 2026-03-10 | e694527 | Optimise acquisition and image processing pipeline (branch: acq-opt) |
| 2026-03-11 | d30397a | Fix background subtraction display regression (branch: acq-opt) |
| 2026-03-11 | 60fb80c | Fix Arduino LED serial reliability — DTR pulse, flush, readAll (branch: acq-opt) |
| 2026-03-11 | 4bda87b | Turn off LED and close serial port on exit (branch: acq-opt) |
| 2026-03-11 | 9191f4f | Fix Arduino LED serial reliability and camera pixel format init (branch: acq-opt) |

## Config Notes
- `time_tagger.acquisition.integration_time` is in **milliseconds** in YAML but converted to picoseconds internally (`× 1e9`)
- `time_tagger.acquisition.sync_delay` and channel delays are in **picoseconds**
- Camera trigger mode: `"hardware"` or `"software"`

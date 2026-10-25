# UAV Camera & Sensor Simulator

Synthetic dataset generator for UAV (drone) navigation research. Given a
georeferenced satellite/aerial image (GeoTIFF), it simulates a drone flying
over the scene and produces a matched, time-synchronized dataset of:

- **Camera frames** — perspective-correct renders of the ground as seen from
  a moving, rotating camera (via homography warping of the GeoTIFF).
- **Flight trajectory** — GPS, UTM, and pixel-space position/velocity/attitude
  for every frame.
- **IMU data** — simulated accelerometer + gyroscope readings, both clean
  (ground truth) and with realistic noise/bias-drift.
- **Magnetometer data** — simulated 3-axis magnetometer readings derived from
  the WMM (World Magnetic Model) at the drone's real-world position.

This is useful for testing/validating visual-inertial odometry, sensor
fusion, and navigation algorithms without needing real flight hardware.

### Coordinate & sensor conventions

- **World frame:** local **ENU** (East-North-Up). Attitude (roll/pitch/yaw)
  and velocity are expressed with X = East, Y = North, Z = Up, and yaw = 0
  means heading East, positive = counter-clockwise (see `path_generation.py`).
- **Camera → body/IMU frame:** the camera looks down its own −Z axis; to
  express that in the body/IMU frame (Z = Up) the sensor rig applies a 180°
  rotation about X:

  ```python
  R_cb = Rot.from_euler('x', 180, degrees=True).as_matrix()
  # R_cb =
  # [[ 1,  0,  0],
  #  [ 0, -1,  0],
  #  [ 0,  0, -1]]
  ```

  i.e. `v_body = R_cb @ v_camera`.
- **Sample rate:** IMU/magnetometer samples are generated at the full sensor
  frequency (`freq`/`fps` from the GUI), but camera frames are only rendered
  every 10th sample — so **image frequency = sensor frequency / 10**
  (`for i in range(0, num_points, 10)` in `src/simulation.py`). If you need a
  different ratio, change the step value there.

### Reading `Path_IMU.xlsx` / `trajectory_full_data.csv`

- `roll`, `pitch`, `yaw` (and `roll_rad`/`pitch_rad`/`yaw_rad`) are the
  **ground-truth attitude angles** — the actual orientation at that instant,
  not a sensor measurement.
- `Wx`, `Wy`, `Wz` are the simulated **gyroscope** readings (angular rate, rad/s)
  — this is the noisy sensor measurement, derived from the rate of change of
  the ground-truth angles above.

## Project structure

```
.
├── src/                    # Core simulation pipeline
│   ├── simulation.py       # Main entry point — run this to generate a dataset
│   ├── parameter_input.py  # GUI (Tkinter) for entering flight parameters
│   ├── path_generation.py  # 3D flight trajectory generation (GPS/UTM/attitude)
│   ├── frame_count.py      # Auto-calculates number of frames from speed/distance
│   ├── sensor_data.py      # IMU + magnetometer data synthesis
│   ├── trajectory_io.py    # Saves trajectory data to CSV/Excel + summary report
│   └── geo_transform.py    # Shared WGS-84 <-> UTM coordinate conversion
│
├── tools/                  # Standalone scripts, run independently as needed
│   ├── convert_to_video.py       # Stitch rendered frames into an .mp4
│   ├── inspect_geotiff.py        # Print pixel size / CRS info for a GeoTIFF
│   ├── plot_trajectory_3d.py     # 3D + top-down trajectory plots from Path_IMU.xlsx
│   ├── plot_flight_csv.py        # Dashboard-style plots from trajectory_full_data.csv
│   ├── validate_imu.py           # Sanity-check IMU data by re-integrating position
│   └── validate_magnetometer.py  # Correlate magnetometer heading against ground-truth yaw
│
├── legacy/
│   └── simHomo3Speed.py    # Older/earlier version of src/simulation.py.
│                            # Kept as-is for reference — not part of the active
│                            # pipeline. Its imports (GenSensorData, genPath, etc.)
│                            # refer to the old flat file layout and will need
│                            # updating to the new src/ module names if reused.
│
├── config/
│   ├── config_notes.txt         # Original scene/camera/IMU parameters used for
│   │                             # the "Urban(Tehran)" dataset
│   └── pixel_size_reference.txt # Ground sample distance reference table
│
├── requirements.txt
└── .gitignore
```

## Installation

```bash
pip install -r requirements.txt
```

> `tools/inspect_geotiff.py` can optionally use GDAL for reading GeoTIFF
> metadata; if GDAL isn't installed it automatically falls back to `rasterio`
> (already in `requirements.txt`), so GDAL is not required.

## Usage

### 1. Generate a dataset

```bash
python src/simulation.py
```

This opens a small GUI (`parameter_input.py`) asking for:

- FOV, image size, sensor frequency
- Path to the input GeoTIFF and an output folder
- Start position (in pixels), altitude, speed (x/y/z)
- Roll/pitch/yaw amplitude and total flight time

> **Flight time = 0:** if you leave/set flight time to `0`, the simulator
> does **not** fly for zero seconds — it automatically flies in a straight
> line to the edge of the GeoTIFF, and estimates the required flight time
> itself from the distance to the edge and the given X speed
> (`total_distance / speed_x`, see `frame_count.calculate_auto_num_points`).
> Give a positive number of seconds only if you want a specific, shorter/longer
> flight duration instead.

**Choosing the right GeoTIFF zoom level:** the ground sample distance (real-world
size of one pixel) depends on altitude, FOV, and image size — computed by
`calculate_pixel_size(fov, image_size, altitude)` in `src/simulation.py`.
Before running a simulation, compute the pixel size for your chosen altitude/FOV/image
size, then look it up in `docs/pixel_size_reference.txt` to find (and download) the
matching zoom-level GeoTIFF — using a mismatched zoom level will make the
rendered frames look too blurry (zoomed-out source) or over-cropped
(zoomed-in source) relative to the requested altitude.

It then generates, inside the chosen output folder:

| File | Contents |
|---|---|
| `frame_#####.png` | Rendered camera frames |
| `Path_IMU.xlsx` | Per-sample IMU + magnetometer data |
| `trajectory_full_data.csv` | Per-frame GPS/UTM/pixel position, velocity, attitude |
| `trajectory_info.txt` | Human-readable flight summary |

### 2. Turn the frames into a video

```bash
python tools/convert_to_video.py -input_folder <output_folder> -o output.mp4 -fps 30
```

### 3. Inspect / validate the generated data

```bash
python tools/plot_trajectory_3d.py       # 3D + top-down flight path plots
python tools/plot_flight_csv.py <output_folder>/trajectory_full_data.csv
python tools/validate_imu.py             # Re-integrate IMU data, compare to ground truth
python tools/validate_magnetometer.py    # Check magnetometer heading vs. true yaw
```

> These scripts currently point at example filenames inside their own
> `main()`/`__main__` blocks — edit the path at the top of each script (or the
> CLI argument, where supported) to point at your own output folder.

## Notes

- `src/geo_transform.py` holds the shared WGS-84 ↔ UTM conversion math. It was
  previously duplicated across `Simulation.py`, `genPath.py`, and
  `simHomo3Speed.py` — it's now centralized in one place so fixes only need
  to happen once.
- The `src/` modules use simple flat imports between each other (e.g.
  `import frame_count`) rather than a Python package layout, matching how the
  project already worked. Run scripts directly from the repo root
  (`python src/simulation.py`) rather than importing `src` as a package.
- **Bugfix:** originally, `flight_duration_seconds` only auto-estimated when
  it was Python `None` — but the GUI always sends a float (`0.0` when you type
  `0`), so entering `0` used to produce `num_points = 0` (no frames) instead of
  the intended "fly to the edge of the GeoTIFF" behavior. `src/simulation.py`
  now converts `0`/empty time to `None` before calling
  `frame_count.calculate_auto_num_points`, so the `time = 0` behavior described
  above actually works.
#   U A V - C a m e r a - S i m u l a t o r  
 
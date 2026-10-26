# UAV Camera & Sensor Simulator

Synthetic dataset generator for UAV (drone) navigation research.

Given a georeferenced satellite/aerial image (`GeoTIFF`), this project simulates a drone flying over the scene and produces a matched, time-synchronized dataset containing:

- **Camera frames** — perspective-correct renders of the ground as seen from a moving, rotating camera, using homography warping of the GeoTIFF.
- **Flight trajectory** — GPS, UTM, and pixel-space position, velocity, and attitude for every frame.
- **IMU data** — simulated accelerometer and gyroscope readings, both clean (ground truth) and with realistic noise and bias drift.
- **Magnetometer data** — simulated 3-axis readings derived from the World Magnetic Model (WMM) at the drone's real-world position.

This is useful for testing and validating visual-inertial odometry, sensor fusion, and navigation algorithms without requiring real flight hardware.

## Coordinate and Sensor Conventions

### World frame

The simulator uses a local **ENU (East-North-Up)** world frame:

- **X** = East
- **Y** = North
- **Z** = Up
- **Yaw = 0°** means heading East.
- Positive yaw is counter-clockwise.

See `path_generation.py` for the yaw convention.

### Camera-to-body/IMU frame

The camera looks down its own **−Z axis**. To express this orientation in the body/IMU frame (**Z = Up**), the sensor rig applies a 180° rotation around the X axis:

```python
R_cb = Rot.from_euler("x", 180, degrees=True).as_matrix()

# R_cb =
# [[ 1,  0,  0],
#  [ 0, -1,  0],
#  [ 0,  0, -1]]
```

The coordinate conversion is:

```python
v_body = R_cb @ v_camera
```

### Sample rates

IMU and magnetometer samples are generated at the full sensor frequency (`freq`/`fps` from the GUI). Camera frames are rendered every 10th sample:

```python
for i in range(0, num_points, 10):
```

Therefore:

**Image frequency = sensor frequency / 10**

To change this ratio, modify the step value in `src/simulation.py`.

## Understanding the Output Data

In `Path_IMU.xlsx` and `trajectory_full_data.csv`:

- `roll`, `pitch`, `yaw` and `roll_rad`, `pitch_rad`, `yaw_rad` are **ground-truth attitude angles**. They represent the actual orientation at that instant, not sensor measurements.
- `Wx`, `Wy`, `Wz` are simulated **gyroscope readings** in rad/s. These are noisy angular-rate measurements derived from the rate of change of the ground-truth angles.

## Project Structure

```text
.
├── src/                         # Core simulation pipeline
│   ├── simulation.py            # Main entry point; generates a dataset
│   ├── parameter_input.py       # Tkinter GUI for flight parameters
│   ├── path_generation.py       # 3D trajectory generation (GPS/UTM/attitude)
│   ├── frame_count.py            # Calculates the number of frames
│   ├── sensor_data.py            # IMU and magnetometer data synthesis
│   ├── trajectory_io.py          # Exports trajectory data to CSV/Excel
│   └── geo_transform.py          # WGS-84 ↔ UTM coordinate conversion
│
├── tools/                        # Standalone utility scripts
│   ├── convert_to_video.py       # Combines frames into an MP4
│   ├── inspect_geotiff.py        # Prints GeoTIFF pixel-size/CRS information
│   ├── plot_trajectory_3d.py     # 3D and top-down trajectory plots
│   ├── plot_flight_csv.py        # Dashboard plots from trajectory CSV
│   ├── validate_imu.py           # Validates IMU data by re-integrating position
│   └── validate_magnetometer.py  # Compares magnetometer heading with true yaw
│
├── legacy/
│   └── simHomo3Speed.py          # Older implementation kept for reference
│
├── config/
│   ├── config_notes.txt          # Original Urban (Tehran) dataset parameters
│   └── pixel_size_reference.txt  # Ground-sample-distance reference table
│
├── requirements.txt
└── .gitignore
```

## Installation

Install the required Python packages:

```bash
pip install -r requirements.txt
```

`tools/inspect_geotiff.py` can optionally use GDAL to read GeoTIFF metadata. If GDAL is unavailable, it automatically falls back to `rasterio`, which is listed in `requirements.txt`. **GDAL is not required.**

## Usage

### 1. Generate a Dataset

Run the simulator from the repository root:

```bash
python src/simulation.py
```

A small Tkinter GUI opens and asks for the following parameters:

- Field of view (FOV), image size, and sensor frequency
- Input GeoTIFF path and output folder
- Starting position in pixels
- Altitude
- X/Y/Z speed
- Roll, pitch, and yaw amplitudes
- Total flight time

#### Automatic flight duration

If flight time is set to `0`, the simulator does **not** fly for zero seconds. Instead, it automatically flies in a straight line to the edge of the GeoTIFF and estimates the required duration from the distance to the edge and the X speed:

```text
flight duration = total distance / speed_x
```

Enter a positive number of seconds only when you want to specify a particular flight duration.

#### Choosing the right GeoTIFF zoom level

The ground sample distance (real-world size of one pixel) depends on altitude, FOV, and image size. It is calculated by `calculate_pixel_size(fov, image_size, altitude)` in `src/simulation.py`.

Before running a simulation:

1. Calculate the pixel size for your selected altitude, FOV, and image size.
2. Find the matching value in `config/pixel_size_reference.txt`.
3. Download a GeoTIFF with the corresponding zoom level.

Using the wrong zoom level may make rendered frames too blurry (source image too zoomed out) or too tightly cropped (source image too zoomed in) for the requested altitude.

### Generated Files

The selected output folder contains:

| File | Description |
| --- | --- |
| `frame_#####.png` | Rendered camera frames |
| `Path_IMU.xlsx` | Per-sample IMU and magnetometer data |
| `trajectory_full_data.csv` | Per-frame GPS/UTM/pixel position, velocity, and attitude |
| `trajectory_info.txt` | Human-readable flight summary |

### 2. Convert Frames into a Video

After generating a dataset, combine the frames into an MP4 video:

```bash
python tools/convert_to_video.py -input_folder <output_folder> -o output.mp4 -fps 30
```

Replace `<output_folder>` with the path to your generated dataset.

### 3. Inspect and Validate the Data

Run the relevant tools from the repository root:

```bash
# Plot the 3D and top-down flight trajectory
python tools/plot_trajectory_3d.py

# Plot data from a specific trajectory CSV
python tools/plot_flight_csv.py <output_folder>/trajectory_full_data.csv

# Validate IMU data
python tools/validate_imu.py

# Validate magnetometer heading against ground-truth yaw
python tools/validate_magnetometer.py
```

Some utility scripts currently use example filenames in their `main()` or `if __name__ == "__main__"` blocks. Update the paths near the top of those scripts to match your output folder, unless the script supports a command-line path argument.

## Implementation Notes

- `src/geo_transform.py` contains the shared WGS-84 ↔ UTM coordinate-conversion logic. This was previously duplicated across `Simulation.py`, `genPath.py`, and `simHomo3Speed.py`; it is now centralized so fixes only need to be made in one place.
- Modules in `src/` use flat imports (for example, `import frame_count`) rather than a Python package layout. Run scripts directly from the repository root, such as `python src/simulation.py`, rather than importing `src` as a package.
- **Flight-time bug fix:** Previously, `flight_duration_seconds` was automatically estimated only when its value was Python `None`. The GUI sends a float (`0.0`) when the user enters `0`, which could result in `num_points = 0` and no frames. The simulator now converts zero/empty flight time to `None` before calling `frame_count.calculate_auto_num_points`, enabling the intended “fly to the edge of the GeoTIFF” behavior.

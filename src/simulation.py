"""
simulation.py - نقطه‌ی ورود اصلی شبیه‌سازی دوربین UAV روی تصویر GeoTIFF.

این ماژول شامل:
  - UAVCameraSimulator: کلاس اصلی رندر تصاویر دوربین از روی نقشه‌ی GeoTIFF
  - calculate_pixel_size: محاسبه‌ی اندازه‌ی هر پیکسل تصویر بر حسب متر
  - بلوک __main__: اجرای کامل پایپ‌لاین (پارامترها -> مسیر -> سنسور -> فریم‌ها)
"""

import math
import os
import time

import cv2
import numpy as np
import rasterio
from rasterio.warp import transform
from rasterio.windows import Window
from scipy.spatial.transform import Rotation as Rot

import frame_count
import geo_transform
import parameter_input
import path_generation
import sensor_data
import trajectory_io


def calculate_pixel_size(fov_degrees, image_size_pixels, altitude_meters):
    """
    محاسبه اندازه هر پیکسل تصویر بر حسب متر

    پارامترها:
    fov_degrees: میدان دید دوربین بر حسب درجه (مربعی فرض شده)
    image_size_pixels: اندازه تصویر بر حسب پیکسل (مربعی)
    altitude_meters: ارتفاع پرواز پهباد بر حسب متر

    بازگشت:
    اندازه هر پیکسل بر حسب متر
    """
    fov_radians = math.radians(fov_degrees)
    fov_meters = 2 * altitude_meters * math.tan(fov_radians / 2)
    pixel_size_meters = fov_meters / image_size_pixels
    return pixel_size_meters


# =========================================================
# UAVCameraSimulator
# =========================================================

class UAVCameraSimulator:

    def __init__(self, geotiff_path):
        self.geotiff_path = geotiff_path
        with rasterio.open(geotiff_path) as src:
            self.H = src.height
            self.W = src.width
            self.count = src.count
            self.transform = src.transform
            self.crs = src.crs

            raw_pixel_size = abs(self.transform.a)
            if self.crs.is_geographic:
                center_row = src.height / 2
                center_col = src.width / 2
                center_x, center_y = src.transform * (center_col, center_row)
                self.pixel_size = raw_pixel_size * 111320 * math.cos(math.radians(center_y))
                print(f"pixel_size: {raw_pixel_size:.8f} deg → {self.pixel_size:.4f} m/pixel")
            else:
                self.pixel_size = raw_pixel_size
                print(f"pixel_size: {self.pixel_size:.4f} m/pixel")

            print("Number of bands:", src.count)
            print("Map shape:", (self.H, self.W, self.count if self.count >= 3 else 3))
            print(f"Memory if loaded: {self.H * self.W * 3 / (1024**3):.1f} GB (uint8)")

            if self.count >= 3:
                self.band_mins = []
                self.band_maxs = []
                for band in [1, 2, 3]:
                    stats = src.statistics(band)
                    self.band_mins.append(stats.min)
                    self.band_maxs.append(stats.max)
            else:
                stats = src.statistics(1)
                self.band_mins = [stats.min]
                self.band_maxs = [stats.max]

        # تشخیص zone و hemisphere از مرکز نقشه
        center_lat, center_lon = self.pixel_to_gps(self.H / 2, self.W / 2)
        self._utm_zone = geo_transform.utm_zone_from_lon(center_lon)
        self._utm_hemisphere = 'north' if center_lat >= 0 else 'south'

        epsg_utm = (32600 if self._utm_hemisphere == 'north' else 32700) + self._utm_zone
        print(f"UTM zone: {self._utm_zone} ({self._utm_hemisphere}), EPSG:{epsg_utm}")

    # ------------------------------------------------------------------
    # تبدیل مختصات
    # ------------------------------------------------------------------
    def get_ground_distance_between_pixels(self, row1, col1, row2, col2):
        lat1, lon1 = self.pixel_to_gps(row1, col1)
        lat2, lon2 = self.pixel_to_gps(row2, col2)

        R = 6371000
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat / 2) ** 2
             + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def calculate_trajectory_length(self, start_row, start_col, end_row, end_col):
        return self.get_ground_distance_between_pixels(start_row, start_col, end_row, end_col)

    def pixel_to_gps(self, row, col):
        with rasterio.open(self.geotiff_path) as src:
            x, y = src.transform * (col, row)
            lon, lat = transform(src.crs, 'EPSG:4326', [x], [y])
            return float(lat[0]), float(lon[0])

    def gps_to_pixel(self, lat, lon):
        with rasterio.open(self.geotiff_path) as src:
            x, y = transform('EPSG:4326', src.crs, [lon], [lat])
            col, row = ~src.transform * (x[0], y[0])
            return row, col

    def gps_to_utm(self, lat, lon):
        """GPS (درجه) → UTM (متر) — بدون pyproj"""
        easting, northing, _, _ = geo_transform.gps_to_utm(lat, lon)
        return easting, northing   # x=easting, y=northing

    def utm_to_gps(self, x_utm, y_utm):
        """UTM (متر) → GPS (درجه) — بدون pyproj"""
        lat, lon = geo_transform.utm_to_gps(x_utm, y_utm, self._utm_zone, self._utm_hemisphere)
        return lat, lon

    
    # ------------------------------------------------------------------
    # خواندن patch از GeoTIFF
    # ------------------------------------------------------------------

    def read_patch(self, x_min, y_min, x_max, y_max):
        with rasterio.open(self.geotiff_path) as src:
            x_min = max(0, min(x_min, self.W - 1))
            x_max = max(x_min + 1, min(x_max, self.W))
            y_min = max(0, min(y_min, self.H - 1))
            y_max = max(y_min + 1, min(y_max, self.H))

            width = x_max - x_min
            height = y_max - y_min
            if width <= 0 or height <= 0:
                return None

            window = Window(x_min, y_min, width, height)

            if self.count >= 3:
                patch = src.read([1, 2, 3], window=window)
                patch = np.transpose(patch, (1, 2, 0))
            else:
                gray = src.read(1, window=window)
                patch = np.stack([gray, gray, gray], axis=2)

            for c in range(patch.shape[2]):
                mn = self.band_mins[c] if c < len(self.band_mins) else 0
                mx = self.band_maxs[c] if c < len(self.band_maxs) else 255
                if mx > mn:
                    patch[:, :, c] = (patch[:, :, c] - mn) * 255.0 / (mx - mn)

            return np.clip(patch, 0, 255).astype(np.uint8)

    # ------------------------------------------------------------------
    # دوربین
    # ------------------------------------------------------------------

    def create_camera_matrix(self, width, height, fov_deg):
        f = width / (2 * np.tan(np.radians(fov_deg) / 2))
        return np.array([
            [f, 0, width / 2],
            [0, f, height / 2],
            [0, 0, 1]
        ])

    def get_four_corners_on_ground(self, position_gps, orientation, width, height, fov):
        K = self.create_camera_matrix(width, height, fov)
        R = Rot.from_euler('zyx', orientation).as_matrix()

        position_utm = position_gps

        corners_pixel = []
        for u, v in [(0, 0), (width, 0), (width, height), (0, height)]:
            ray_cam = np.array([
                (u - width / 2) / K[0, 0],
                (v - height / 2) / K[1, 1],
                1.0
            ])
            ray_cam /= np.linalg.norm(ray_cam)
            R_cb = Rot.from_euler('x', 180, degrees=True).as_matrix() 
            ray_world = R @ R_cb @ ray_cam
            

            if ray_world[2] >= 0:
                return None

            t = -position_utm[2] / ray_world[2]
            gp_utm = position_utm + t * ray_world

            corner_lat, corner_lon = self.utm_to_gps(gp_utm[0], gp_utm[1])
            corner_row, corner_col = self.gps_to_pixel(corner_lat, corner_lon)
            corners_pixel.append([corner_col, corner_row])

        return np.array(corners_pixel, dtype=np.float32)

    def render_fast(self, position_gps, orientation, width=512, height=512, fov=90):
        SCALE = 1
        corners_ground = self.get_four_corners_on_ground(
            position_gps, orientation, width, height, fov
        )

        if corners_ground is None:
            print("Camera looking upward!")
            return np.zeros((height, width, 3), dtype=np.uint8)

        min_x = np.min(corners_ground[:, 0])
        max_x = np.max(corners_ground[:, 0])
        min_y = np.min(corners_ground[:, 1])
        max_y = np.max(corners_ground[:, 1])

        margin = max(50, int(0.1 * max(max_x - min_x, max_y - min_y)))
        min_x = max(0, min_x - margin)
        max_x = min(self.W, max_x + margin)
        min_y = max(0, min_y - margin)
        max_y = min(self.H, max_y + margin)

        if min_x >= max_x or min_y >= max_y:
            print("Camera view is outside the map")
            return np.zeros((height, width, 3), dtype=np.uint8)

        map_patch = self.read_patch(
            int(np.floor(min_x)), int(np.floor(min_y)),
            int(np.ceil(max_x)), int(np.ceil(max_y))
        )
        if map_patch is None:
            return np.zeros((height, width, 3), dtype=np.uint8)

        corners_rel = corners_ground - [min_x, min_y]
        corners_out = np.array(
            [[0, 0], [width, 0], [width, height], [0, height]],
            dtype=np.float32
        )

        H_mat, _ = cv2.findHomography(corners_rel, corners_out)
        if H_mat is None:
            return np.zeros((height, width, 3), dtype=np.uint8)

        S = np.array([
            [SCALE, 0, 0],
            [0, SCALE, 0],
            [0, 0, 1]
        ], dtype=np.float64)

        H_large = H_mat  # همان محتوا، در فضای 1024
        try:
            output_large = cv2.warpPerspective(
                map_patch, H_large, (width * SCALE, height * SCALE),
                flags=cv2.INTER_LANCZOS4,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0)
            )
            return output_large
        except Exception as e:
            print(f"Warp perspective failed: {e}")
            return np.zeros((height, width, 3), dtype=np.uint8)

    def render(self, position_gps, orientation, width=512, height=512, fov=90):
        return self.render_fast(position_gps, orientation, width, height, fov)

    def render_with_motion_blur(self, position_gps, orientation,
                                 velocity, angular_velocity,
                                 exposure_time, num_samples=8,
                                 width=512, height=512, fov=90):

        x_utm, y_utm, alt = position_gps
        accumulated = np.zeros((height, width, 3), dtype=np.float32)

        for i in range(num_samples):
            t = (i / (num_samples - 1) - 0.5) * exposure_time

            x_t = x_utm + velocity[0] * t
            y_t = y_utm + velocity[1] * t
            alt_t = alt + velocity[2] * t

            lat_t, lon_t = self.utm_to_gps(x_t, y_t)
            pos_utm_t = [x_t, y_t, alt_t]
            ori_t = orientation + angular_velocity * t

            frame = self.render_fast(pos_utm_t, ori_t, width, height, fov)
            accumulated += frame.astype(np.float32)

        return np.clip(accumulated / num_samples, 0, 255).astype(np.uint8)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    params = parameter_input.main()

    fov = params['fov']
    image_size = params['image_size']  # پیکسل (تصویر مربعی)

    sim = UAVCameraSimulator(params['input_dir'])
    output_dir = params['output_dir']
    os.makedirs(output_dir, exist_ok=True)

    start_row_pixel = params['start_row']
    start_col_pixel = params['start_col']
    fps = params['freq']

    flight_height_meters = params['altitude']

    base_speed_x = params['speed_x']
    base_speed_y = params['speed_y']
    base_speed_z = params['speed_z']

    pixel_size = calculate_pixel_size(fov, image_size, flight_height_meters)

    print("\n" + "=" * 70)
    print("🛸 INITIAL POSITION CALCULATION")
    print("=" * 70)
    
    num_points, flight_duration, start_lat, start_lon = frame_count.calculate_auto_num_points(
        sim,
        start_col_pixel, start_row_pixel,
        base_speed_x, base_speed_y, base_speed_z, fps,
        flight_duration_seconds=params['time']
    )

    gps_trajectory, utm_trajectory, roll_rad, pitch_rad, yaw_rad, speed_x_mps, speed_y_mps, speed_z_mps, t = path_generation.genPath(
        params['roll'], params['pitch'], params['yaw'],
        flight_duration, num_points,
        base_speed_x, base_speed_y, base_speed_z,
        start_lat, start_lon, flight_height_meters
    )

    sensor_data.main(gps_trajectory, np.column_stack([roll_rad, pitch_rad, yaw_rad]), 1 / fps, output_dir, t)
    alt_array = np.array([p[2] for p in gps_trajectory])

    print(f"✅ Generated {len(gps_trajectory)} GPS points")
    print(f"  Altitude range: [{alt_array.min():.1f}, {alt_array.max():.1f}] m")
    print("\n🔄 Converting GPS trajectory to pixel coordinates...")

    pixel_trajectory = []
    last_row, last_col = 0.0, 0.0

    for i, gps_pos in enumerate(gps_trajectory):
        if i % 100 == 0:
            last_row, last_col = sim.gps_to_pixel(gps_pos[0], gps_pos[1])
        pixel_trajectory.append((float(last_row), float(last_col)))

    trajectory_io.saveTrajectory(num_points, utm_trajectory, gps_trajectory,
                                  pixel_trajectory,
                                  speed_x_mps, speed_y_mps, speed_z_mps,
                                  roll_rad, pitch_rad, yaw_rad,
                                  t, output_dir, flight_duration,
                                  base_speed_x, base_speed_y, base_speed_z,
                                  flight_height_meters, alt_array)

    print("\n🎬 Starting frame generation...")
    print("=" * 70)

    start_time_total = time.time()

    for i in range(0, num_points, 10):
        gps_pos = utm_trajectory[i]
        ori = np.array([yaw_rad[i], pitch_rad[i], roll_rad[i]])

        if i % max(1, num_points // 20) == 0:
            progress = (i / num_points) * 100
            print(f"\n📸 Frame: {i:05d}/{num_points} ({progress:.1f}%)")
            print(f"  GPS Position: ({gps_pos[0]:.8f}, {gps_pos[1]:.8f}, {gps_pos[2]:.1f}m)")
            
        start_time = time.time()

        img = sim.render_fast(
            position_gps=gps_pos,
            orientation=ori,
            width=image_size, height=image_size, fov=fov
        )

        elapsed_time = time.time() - start_time

        filename = os.path.join(output_dir, f"frame_{i:06d}.png")
        cv2.imwrite(filename, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

        if i % max(1, num_points // 20) == 0:
            print(f"  Render time: {elapsed_time:.3f}s  ->  Saved: {filename}")

    total_time = time.time() - start_time_total

    print("\n" + "=" * 70)
    print("✅ ALL FRAMES GENERATED SUCCESSFULLY!")
    print("=" * 70)
    print(f"📁 Output directory: {output_dir}")
    print(f"📊 Total frames: {int(num_points / 10)}")
    print(f"📊 Sensors Freq: {int(num_points)}")
    print(f"⏱️  Total render time: {total_time:.2f}s")
    print(f"⏱️  Average time per frame: {(total_time/num_points)*10:.3f}s")
    print(f"\n📍 Start GPS: ({gps_trajectory[0][0]:.8f}, {gps_trajectory[0][1]:.8f}, {gps_trajectory[0][2]:.1f}m)")
    print(f"📍 End GPS:   ({gps_trajectory[-1][0]:.8f}, {gps_trajectory[-1][1]:.8f}, {gps_trajectory[-1][2]:.1f}m)")
    print(f"\n📊 Full trajectory data saved to:")
    print(f"   CSV:   {os.path.join(output_dir, 'trajectory_full_data.csv')}")

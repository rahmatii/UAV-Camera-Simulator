"""
path_generation.py - تولید مسیر پرواز سه‌بعدی UAV (GPS + UTM + جهت‌گیری + سرعت)
"""

import numpy as np

from geo_transform import gps_to_utm


def genPath(base_roll, base_pitch, base_yaw,
            flight_duration, num_points,
            base_speed_x, base_speed_y, base_speed_z,
            start_lat, start_lon, flight_height_meters):

    # =========================================================
    # GENERATE TIME ARRAY AND ORIENTATIONS
    # =========================================================
    t = np.linspace(0, flight_duration, num_points)

    roll_deg = base_roll * np.sin(t)
    pitch_deg = base_pitch * np.sin(t)
    yaw_deg = base_yaw * np.sin(t)

    roll_rad = np.radians(roll_deg)
    pitch_rad = np.radians(pitch_deg)
    yaw_rad = np.radians(yaw_deg)

    print(f"\n🎯 CAMERA ORIENTATION (initial frame):")
    print(f"  Roll:  {roll_deg[0]:.3f}°")
    print(f"  Pitch: {pitch_deg[0]:.3f}°")
    print(f"  Yaw:   {yaw_deg[0]:.3f}°")

    # =========================================================
    # سرعت لحظه‌ای در سه راستا
    # =========================================================
    speed_x_mps = base_speed_x + ((2 * base_speed_x) / 100 + 0.5) * np.sin(t)
    speed_y_mps = base_speed_y + ((2 * base_speed_y) / 100 + 0.5) * np.sin(t)
    speed_z_mps = base_speed_z + ((2 * base_speed_z) / 100 + 0.5) * np.sin(t)

    print(f"\n📊 SPEED RANGES (with sinusoidal variation):")
    print(f"  X: [{speed_x_mps.min():.2f}, {speed_x_mps.max():.2f}] m/s")
    print(f"  Y: [{speed_y_mps.min():.2f}, {speed_y_mps.max():.2f}] m/s")
    print(f"  Z: [{speed_z_mps.min():.2f}, {speed_z_mps.max():.2f}] m/s")

    # =========================================================
    # GENERATE TRAJECTORY — با UTM دقیق
    # =========================================================
    print("\n🔄 Generating 3D trajectory in GPS space (via UTM)...")

    # zone و hemisphere را از نقطه شروع یک‌بار تعیین می‌کنیم
    x_utm, y_utm, utm_zone, utm_hemisphere = gps_to_utm(start_lat, start_lon)
    alt = float(flight_height_meters)

    gps_trajectory = [np.array([start_lat, start_lon, alt])]
    utm_trajectory = [np.array([x_utm, y_utm, alt])]
    a = 6378137.0
    e2 = 0.00669437999014

    lat_deg = start_lat
    lon_deg = start_lon

    for i in range(1, num_points):
        dt = t[i] - t[i - 1]

        r = roll_rad[i]
        p = pitch_rad[i]
        y = yaw_rad[i]

        # ماتریس دوران Body → ENU
        # در ENU: X=East, Y=North, Z=Up
        # Yaw صفر = رو به شرق، مثبت = پادساعتگرد

        Rz = np.array([[np.cos(y), -np.sin(y), 0],   # yaw (دور Z=Up)
                        [np.sin(y), np.cos(y), 0],
                        [0, 0, 1]])

        Ry = np.array([[np.cos(p), 0, np.sin(p)],   # pitch (دور Y=North)
                        [0, 1, 0],
                        [-np.sin(p), 0, np.cos(p)]])

        Rx = np.array([[1, 0, 0],    # roll (دور X=East)
                        [0, np.cos(r), -np.sin(r)],
                        [0, np.sin(r), np.cos(r)]])

        R_body_to_ENU = Rz @ Ry @ Rx

        # سرعت در دستگاه بدنه پهباد
        # در ENU بدنه: جلو=East، راست=North، بالا=Up
        v_body = np.array([speed_x_mps[i],    # جلو (Forward)
                            speed_y_mps[i],    # راست (Right)
                            speed_z_mps[i]])   # بالا (Up)

        # تبدیل به ENU جهانی
        v_enu = R_body_to_ENU @ v_body

        lat_r = np.radians(lat_deg)

        # شعاع انحنا در جهت شمال
        M = a * (1 - e2) / (1 - e2 * np.sin(lat_r)**2) ** 1.5

        # شعاع انحنا در جهت شرق
        N = a / np.sqrt(1 - e2 * np.sin(lat_r)**2)

        # تغییر مختصات
        dlat = np.degrees(v_enu[1] * dt / (M + flight_height_meters))  # vy_mps
        dlon = np.degrees(v_enu[0] * dt / ((N + flight_height_meters) * np.cos(lat_r)))  # vx_mps
        dalt = v_enu[2] * dt
        lat_deg = lat_deg + dlat
        lon_deg = lon_deg + dlon

        alt = float(np.clip(alt + dalt, flight_height_meters - 10, flight_height_meters + 10))

        x_utm, y_utm, _, _ = gps_to_utm(lat_deg, lon_deg)

        utm_trajectory.append(np.array([x_utm, y_utm, alt]))
        gps_trajectory.append(np.array([lat_deg, lon_deg, alt]))

    return (gps_trajectory, utm_trajectory,
            roll_rad, pitch_rad, yaw_rad,
            speed_x_mps, speed_y_mps, speed_z_mps,
            t)

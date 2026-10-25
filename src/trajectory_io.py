import math
import os
import pandas as pd

def saveTrajectory(num_points, utm_trajectory, gps_trajectory,
                   pixel_trajectory,              
                   speed_x_mps, speed_y_mps, speed_z_mps,
                   roll_rad, pitch_rad, yaw_rad,
                   t, output_dir, flight_duration,
                   base_speed_x, base_speed_y, base_speed_z,
                   flight_height_meters, alt_array):
    trajectory_data = []

    for i in range(num_points):
    # موقعیت پیکسلی
        row_px = pixel_trajectory[i][0]
        col_px = pixel_trajectory[i][1]

        # سرعت پیکسلی لحظه‌ای
        if i > 0:
            prev_row = pixel_trajectory[i-1][0]
            prev_col = pixel_trajectory[i-1][1]
            dt_px = t[i] - t[i-1]
            vrow_pixel = (row_px - prev_row) / dt_px
            vcol_pixel = (col_px - prev_col) / dt_px
        else:
            vrow_pixel = vcol_pixel = 0.0

        pos_pixel = utm_trajectory[i]
        gps_pos   = gps_trajectory[i]

        vx = float(speed_x_mps[i])
        vy = float(speed_y_mps[i])
        vz = float(speed_z_mps[i])
        speed_total = math.sqrt(vx**2 + vy**2 + vz**2)

        roll_deg  = float(math.degrees(roll_rad[i]))
        pitch_deg = float(math.degrees(pitch_rad[i]))
        yaw_deg   = float(math.degrees(yaw_rad[i]))

        # سرعت لحظه‌ای پیکسل بر ثانیه
        if i > 0:
            prev_pixel = utm_trajectory[i - 1]
            dt = t[i] - t[i - 1]
            vx_pixel = (pos_pixel[0] - prev_pixel[0]) / dt
            vy_pixel = (pos_pixel[1] - prev_pixel[1]) / dt
            vz_pixel = (pos_pixel[2] - prev_pixel[2]) / dt  # متر بر ثانیه (ارتفاع)
        else:
            vx_pixel = vy_pixel = vz_pixel = 0.0

        trajectory_data.append({
            'frame_number':           int(i/10),
            'timestamp_seconds':      float(t[i]),

            # موقعیت در پیکسل
            'x_utm':            float(pos_pixel[0]),
            'y_utm':            float(pos_pixel[1]),
            'altitude_meters':        float(pos_pixel[2]),

            # موقعیت در GPS
            'latitude':               float(gps_pos[0]),
            'longitude':              float(gps_pos[1]),

            # سرعت در سه راستا (متر بر ثانیه)
            'speed_x_mps':            vx,
            'speed_y_mps':            vy,
            'speed_z_mps':            vz,
            'speed_total_mps':        speed_total,
            'speed_total_kmh':        speed_total * 3.6,

            # سرعت در فضای پیکسل
            'velocity_x_utm_per_sec': vx_pixel,
            'velocity_y_utm_per_sec': vy_pixel,
            'velocity_z_m_per_sec':     vz_pixel,


            # موقعیت پیکسلی
            'pixel_x_col':              row_px,
            'pixel_y_row':              col_px,

            # سرعت پیکسلی (پیکسل بر ثانیه)
            'velocity_row_px_per_sec': vrow_pixel,
            'velocity_col_px_per_sec': vcol_pixel,

            # زوایا (درجه)
            'roll_deg_gt':   roll_deg,
            'pitch_deg_gt':  pitch_deg,
            'yaw_deg_gt':    yaw_deg,

            # زوایا (رادیان)
            'roll_rad_gt':   roll_rad[i],
            'pitch_rad_gt':  pitch_rad[i],
            'yaw_rad_gt':    yaw_rad[i],
        })

    df_trajectory = pd.DataFrame(trajectory_data)

    csv_file = os.path.join(output_dir, "trajectory_full_data.csv")
    df_trajectory.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"✅ CSV file saved: {csv_file}")
    
    print(f"📊 Data shape: {df_trajectory.shape[0]} rows × {df_trajectory.shape[1]} columns")

    print("\n📊 Statistical Summary:")
    print("=" * 80)
    print(f"  Time range:       {df_trajectory['timestamp_seconds'].min():.2f}s - {df_trajectory['timestamp_seconds'].max():.2f}s")
    print(f"  Latitude range:   {df_trajectory['latitude'].min():.8f}° - {df_trajectory['latitude'].max():.8f}°")
    print(f"  Longitude range:  {df_trajectory['longitude'].min():.8f}° - {df_trajectory['longitude'].max():.8f}°")
    print(f"  Altitude range:   {df_trajectory['altitude_meters'].min():.1f}m - {df_trajectory['altitude_meters'].max():.1f}m")
    print(f"  Speed X range:    {df_trajectory['speed_x_mps'].min():.2f} - {df_trajectory['speed_x_mps'].max():.2f} m/s")
    print(f"  Speed Y range:    {df_trajectory['speed_y_mps'].min():.2f} - {df_trajectory['speed_y_mps'].max():.2f} m/s")
    print(f"  Speed Z range:    {df_trajectory['speed_z_mps'].min():.2f} - {df_trajectory['speed_z_mps'].max():.2f} m/s")
    print(f"  Total speed:      {df_trajectory['speed_total_mps'].min():.2f} - {df_trajectory['speed_total_mps'].max():.2f} m/s")
    print(f"  Roll range:       {df_trajectory['roll_deg_gt'].min():.3f}° - {df_trajectory['roll_deg_gt'].max():.3f}°")
    print(f"  Pitch range:      {df_trajectory['pitch_deg_gt'].min():.3f}° - {df_trajectory['pitch_deg_gt'].max():.3f}°")
    print(f"  Yaw range:        {df_trajectory['yaw_deg_gt'].min():.3f}° - {df_trajectory['yaw_deg_gt'].max():.3f}°")


    # =========================================================
    # ذخیره trajectory_info.txt
    # =========================================================

    trajectory_file = os.path.join(output_dir, "trajectory_info.txt")
    with open(trajectory_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("UAV TRAJECTORY INFORMATION (3D VELOCITY)\n")
        f.write("=" * 70 + "\n")
        f.write(f"Total frames: {int(num_points/10)}\n")
        f.write(f"Total sensors data: {(num_points)}\n")
        f.write(f"Flight duration: {flight_duration:.2f} seconds ({flight_duration/60:.2f} minutes)\n")
        f.write(f"FPS: 1\n")
        f.write(f"\nSpeed Components (base values):\n")
        f.write(f"  X (East-West):   {base_speed_x:.2f} m/s  ({base_speed_x*3.6:.1f} km/h)\n")
        f.write(f"  Y (North-South): {base_speed_y:.2f} m/s  ({base_speed_y*3.6:.1f} km/h)\n")
        f.write(f"  Z (Vertical):    {base_speed_z:.2f} m/s  ({base_speed_z*3.6:.1f} km/h)\n")
        f.write(f"\nInitial Camera altitude: {flight_height_meters} meters\n")
        f.write(f"Altitude range: [{alt_array.min():.1f}, {alt_array.max():.1f}] m\n")
        f.write(f"\nStart GPS: ({gps_trajectory[0][0]:.8f}, {gps_trajectory[0][1]:.8f})\n")
        f.write(f"End GPS:   ({gps_trajectory[-1][0]:.8f}, {gps_trajectory[-1][1]:.8f})\n")
        f.write(f"\nFull trajectory data: {csv_file}\n")

    print(f"\n💾 Trajectory info saved to: {trajectory_file}")


"""
frame_count.py - محاسبه‌ی خودکار تعداد فریم‌های موردنیاز بر اساس سرعت و مسافت.
"""

import math


def calculate_auto_num_points(sim, start_col_pixel, start_row_pixel,
                               base_speed_x_mps, base_speed_y_mps, base_speed_z_mps,
                               fps, flight_duration_seconds=0):
    start_lat, start_lon = sim.pixel_to_gps(start_row_pixel, start_col_pixel)
    end_col_pixel = sim.W - 1
    end_row_pixel = start_row_pixel

    total_distance_meters = sim.get_ground_distance_between_pixels(
        start_row_pixel, start_col_pixel,
        end_row_pixel, end_col_pixel
    )

    speed_total = math.sqrt(base_speed_x_mps**2 + base_speed_y_mps**2 + base_speed_z_mps**2)

    print("=" * 70)
    print("🎯 AUTO-CALCULATING TRAJECTORY PARAMETERS (3D)")
    print("=" * 70)
    print(f"🎯 Start Point (Pixel): col={start_col_pixel:.1f}, row={start_row_pixel:.1f}")
    print(f"🎯 Start Point (GPS): ({start_lat:.8f}, {start_lon:.8f})")
    
    end_lat, end_lon = sim.pixel_to_gps(end_row_pixel, end_col_pixel)
    print(f"\n🚀 Speed Components:")
    print(f"   X (East-West):   {base_speed_x_mps:>8.2f} m/s  ({base_speed_x_mps*3.6:.1f} km/h)")
    print(f"   Y (North-South): {base_speed_y_mps:>8.2f} m/s  ({base_speed_y_mps*3.6:.1f} km/h)")
    print(f"   Z (Vertical):    {base_speed_z_mps:>8.2f} m/s  ({base_speed_z_mps*3.6:.1f} km/h)")
    print(f"   Total:           {speed_total:>8.2f} m/s  ({speed_total*3.6:.1f} km/h)")

    if flight_duration_seconds == 0 :
        flight_duration_seconds = total_distance_meters / max(abs(base_speed_x_mps), 0.001)
        print(f"\n⏱️  Estimated flight duration: {flight_duration_seconds:.2f}s ({flight_duration_seconds/60:.2f} min)")
    else:
        print(f"\n⏱️  User-specified flight duration: {flight_duration_seconds:.2f}s")

    num_points = int(flight_duration_seconds * fps)

    return num_points, flight_duration_seconds, start_lat, start_lon

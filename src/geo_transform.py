"""
توابع تبدیل مختصات جغرافیایی: WGS-84 (GPS) <-> UTM

این توابع بدون وابستگی به pyproj/utm پیاده‌سازی شده‌اند و در چند ماژول
دیگر پروژه (simulation.py، path_generation.py) استفاده می‌شوند.

این ماژول قبلاً به‌صورت کد تکراری (copy-paste) در چند فایل مختلف پروژه
وجود داشت؛ در نسخه‌ی فعلی، همه در یک‌جا نگه‌داری می‌شود تا هرگونه تغییر
یا رفع باگ آینده فقط در یک محل لازم باشد.
"""

import math

# ثابت‌های بیضی‌وار WGS-84
_A = 6378137.0                 # نیم‌محور بزرگ (متر)
_F = 1 / 298.257223563         # تخت‌شدگی
_B = _A * (1 - _F)
_E2 = 1 - (_B / _A) ** 2        # e^2
_E_PRIME2 = _E2 / (1 - _E2)     # e'^2

_K0 = 0.9996                    # ضریب مقیاس UTM
_E0 = 500000.0                  # false easting


def utm_zone_from_lon(lon: float) -> int:
    """محاسبه‌ی شماره‌ی زون UTM بر اساس طول جغرافیایی."""
    return int((lon + 180) / 6) + 1


def gps_to_utm(lat: float, lon: float):
    """
    تبدیل WGS-84 (درجه) به UTM (متر).

    Returns:
        (easting, northing, zone_number, hemisphere)
    """
    zone = utm_zone_from_lon(lon)
    lon0 = math.radians((zone - 1) * 6 - 180 + 3)  # مرکز زون

    lat_r = math.radians(lat)
    lon_r = math.radians(lon)

    N = _A / math.sqrt(1 - _E2 * math.sin(lat_r) ** 2)
    T = math.tan(lat_r) ** 2
    C = _E_PRIME2 * math.cos(lat_r) ** 2
    A = math.cos(lat_r) * (lon_r - lon0)

    M = _A * (
        (1 - _E2 / 4 - 3 * _E2**2 / 64 - 5 * _E2**3 / 256) * lat_r
        - (3 * _E2 / 8 + 3 * _E2**2 / 32 + 45 * _E2**3 / 1024) * math.sin(2 * lat_r)
        + (15 * _E2**2 / 256 + 45 * _E2**3 / 1024) * math.sin(4 * lat_r)
        - (35 * _E2**3 / 3072) * math.sin(6 * lat_r)
    )

    easting = _K0 * N * (
        A
        + (1 - T + C) * A**3 / 6
        + (5 - 18 * T + T**2 + 72 * C - 58 * _E_PRIME2) * A**5 / 120
    ) + _E0

    northing = _K0 * (
        M
        + N * math.tan(lat_r) * (
            A**2 / 2
            + (5 - T + 9 * C + 4 * C**2) * A**4 / 24
            + (61 - 58 * T + T**2 + 600 * C - 330 * _E_PRIME2) * A**6 / 720
        )
    )

    hemisphere = 'north' if lat >= 0 else 'south'
    if hemisphere == 'south':
        northing += 10_000_000.0  # false northing برای نیمکره‌ی جنوبی

    return easting, northing, zone, hemisphere


def utm_to_gps(easting: float, northing: float, zone: int, hemisphere: str):
    """
    تبدیل UTM (متر) به WGS-84 (درجه).

    Returns:
        (lat, lon)
    """
    if hemisphere == 'south':
        northing -= 10_000_000.0

    x = easting - _E0
    M = northing / _K0

    mu = M / (_A * (1 - _E2 / 4 - 3 * _E2**2 / 64 - 5 * _E2**3 / 256))

    e1 = (1 - math.sqrt(1 - _E2)) / (1 + math.sqrt(1 - _E2))

    phi1 = (mu
            + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
            + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
            + (151 * e1**3 / 96) * math.sin(6 * mu)
            + (1097 * e1**4 / 512) * math.sin(8 * mu))

    N1 = _A / math.sqrt(1 - _E2 * math.sin(phi1) ** 2)
    T1 = math.tan(phi1) ** 2
    C1 = _E_PRIME2 * math.cos(phi1) ** 2
    R1 = _A * (1 - _E2) / (1 - _E2 * math.sin(phi1) ** 2) ** 1.5
    D = x / (N1 * _K0)

    lat = phi1 - (N1 * math.tan(phi1) / R1) * (
        D**2 / 2
        - (5 + 3 * T1 + 10 * C1 - 4 * C1**2 - 9 * _E_PRIME2) * D**4 / 24
        + (61 + 90 * T1 + 298 * C1 + 45 * T1**2 - 252 * _E_PRIME2 - 3 * C1**2) * D**6 / 720
    )

    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    lon = lon0 + (
        D
        - (1 + 2 * T1 + C1) * D**3 / 6
        + (5 - 2 * C1 + 28 * T1 - 3 * C1**2 + 8 * _E_PRIME2 + 24 * T1**2) * D**5 / 120
    ) / math.cos(phi1)

    return math.degrees(lat), math.degrees(lon)


# نگهداری نام‌های قدیمی به‌عنوان مستعار (alias) برای سازگاری با کد قبلی
_utm_zone_from_lon = utm_zone_from_lon
gps_to_utm_manual = gps_to_utm
utm_to_gps_manual = utm_to_gps

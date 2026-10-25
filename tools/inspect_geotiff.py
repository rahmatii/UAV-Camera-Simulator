"""
خواندن فایل GeoTIFF و استخراج اندازه پیکسل به سانتی‌متر
"""

import sys
import os
import math


# ========================================================
# تبدیل واحد به سانتی‌متر
# ========================================================

def to_cm(value: float, unit: str) -> float:
    """تبدیل مقدار به سانتی‌متر بر اساس واحد CRS"""
    conversions = {
        "metre":       100.0,
        "meter":       100.0,
        "m":           100.0,
        "kilometre":   100_000.0,
        "kilometer":   100_000.0,
        "km":          100_000.0,
        "foot":        30.48,
        "feet":        30.48,
        "ft":          30.48,
        "us survey foot": 30.480060960,
        "inch":        2.54,
        "centimetre":  1.0,
        "centimeter":  1.0,
        "cm":          1.0,
        "millimetre":  0.1,
        "millimeter":  0.1,
        "mm":          0.1,
    }
    key = unit.strip().lower()
    if key in conversions:
        return value * conversions[key]
    return None  # واحد ناشناخته


def degree_to_cm(degrees: float, latitude_deg: float = 0.0) -> float:
    """
    تبدیل درجه جغرافیایی به سانتی‌متر.
    برای X (طول جغرافیایی) تصحیح cos(lat) اعمال می‌شود.
    از مدل WGS-84 استفاده می‌شود.
    """
    # شعاع زمین در استوا (متر)
    R = 6_378_137.0
    cm_per_degree = (2 * math.pi * R / 360) * 100  # ~11_131_949 cm per degree at equator
    return degrees * cm_per_degree * math.cos(math.radians(latitude_deg))


# ========================================================
# خواندن GeoTIFF با GDAL
# ========================================================

def get_pixel_size_gdal(filepath: str) -> dict:
    from osgeo import gdal, osr

    ds = gdal.Open(filepath)
    if ds is None:
        raise FileNotFoundError(f"فایل یافت نشد یا قابل باز شدن نیست: {filepath}")

    gt = ds.GetGeoTransform()
    projection = ds.GetProjection()
    width = ds.RasterXSize
    height = ds.RasterYSize

    pixel_width = abs(gt[1])
    pixel_height = abs(gt[5])
    origin_x = gt[0]
    origin_y = gt[3]

    # تشخیص واحد CRS
    unit = "unknown"
    is_geographic = False
    center_lat = origin_y  # تقریب مرکز

    if projection:
        srs = osr.SpatialReference()
        srs.ImportFromWkt(projection)
        is_geographic = bool(srs.IsGeographic())
        if not is_geographic:
            linear_unit_name = srs.GetLinearUnitsName()
            unit = linear_unit_name.lower() if linear_unit_name else "metre"
        else:
            unit = "degree"
            # مرکز تصویر برای تصحیح cos(lat)
            center_lat = origin_y - (pixel_height * height / 2)

    ds = None

    return {
        "pixel_width": pixel_width,
        "pixel_height": pixel_height,
        "raster_width_px": width,
        "raster_height_px": height,
        "origin_x": origin_x,
        "origin_y": origin_y,
        "center_lat": center_lat,
        "unit": unit,
        "is_geographic": is_geographic,
        "projection": projection,
        "method": "gdal",
    }


# ========================================================
# خواندن GeoTIFF با rasterio
# ========================================================

def get_pixel_size_rasterio(filepath: str) -> dict:
    import rasterio

    with rasterio.open(filepath) as src:
        transform = src.transform
        pixel_width = abs(transform.a)
        pixel_height = abs(transform.e)
        crs = src.crs
        width = src.width
        height = src.height
        bounds = src.bounds

    is_geographic = False
    unit = "metre"
    center_lat = (bounds.top + bounds.bottom) / 2

    if crs:
        is_geographic = crs.is_geographic
        if is_geographic:
            unit = "degree"
        else:
            # واحد از CRS
            linear_units = crs.linear_units
            unit = linear_units.lower() if linear_units else "metre"

    return {
        "pixel_width": pixel_width,
        "pixel_height": pixel_height,
        "raster_width_px": width,
        "raster_height_px": height,
        "bounds": {
            "left": bounds.left,
            "bottom": bounds.bottom,
            "right": bounds.right,
            "top": bounds.top,
        },
        "center_lat": center_lat,
        "unit": unit,
        "is_geographic": is_geographic,
        "crs": str(crs),
        "method": "rasterio",
    }


# ========================================================
# تابع اصلی
# ========================================================

def get_pixel_size(filepath: str) -> dict:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"فایل وجود ندارد: {filepath}")

    try:
        from osgeo import gdal
        return get_pixel_size_gdal(filepath)
    except ImportError:
        pass

    try:
        import rasterio
        return get_pixel_size_rasterio(filepath)
    except ImportError:
        pass

    raise ImportError(
        "هیچ کتابخانه‌ای برای خواندن GeoTIFF یافت نشد.\n"
        "لطفاً یکی از موارد زیر را نصب کنید:\n"
        "  pip install gdal\n"
        "  pip install rasterio"
    )


def compute_cm(info: dict) -> tuple:
    """محاسبه اندازه پیکسل به سانتی‌متر"""
    unit = info.get("unit", "unknown")
    pw = info["pixel_width"]
    ph = info["pixel_height"]
    center_lat = info.get("center_lat", 0.0)

    if info.get("is_geographic"):
        # واحد = درجه؛ X نیاز به تصحیح cos(lat) دارد
        pw_cm = degree_to_cm(pw, latitude_deg=center_lat)
        ph_cm = degree_to_cm(ph, latitude_deg=0.0)  # Y در امتداد نصف‌النهار، cos(0)=1
    else:
        pw_cm = to_cm(pw, unit)
        ph_cm = to_cm(ph, unit)

    return pw_cm, ph_cm


# ========================================================
# نمایش نتیجه
# ========================================================

def print_info(info: dict, filepath: str):
    pw_cm, ph_cm = compute_cm(info)
    unit = info.get("unit", "?")

    print("=" * 55)
    print(f"📁 فایل: {os.path.basename(filepath)}")
    print("=" * 55)

    print(f"\n📐 اندازه پیکسل (واحد اصلی CRS: {unit}):")
    print(f"   عرض  (X): {info['pixel_width']:.8f} {unit}")
    print(f"   ارتفاع (Y): {info['pixel_height']:.8f} {unit}")

    print(f"\n📏 اندازه پیکسل به سانتی‌متر:")
    if pw_cm is not None:
        print(f"   عرض  (X): {pw_cm:,.4f} cm")
        print(f"   ارتفاع (Y): {ph_cm:,.4f} cm")
        if info.get("is_geographic"):
            print(f"   ⚠️  مقدار X با cos(lat={info.get('center_lat', 0):.2f}°) تصحیح شده است")
    else:
        print(f"   ⚠️  واحد '{unit}' ناشناخته است — تبدیل ممکن نیست")

    print(f"\n🖼️  ابعاد رستر: {info['raster_width_px']} × {info['raster_height_px']} پیکسل")

    if "crs" in info:
        print(f"\n🌐 سیستم مختصات: {info['crs']}")
    elif "projection" in info and info["projection"]:
        print(f"\n🌐 Projection: موجود (WKT)")

    if "bounds" in info:
        b = info["bounds"]
        print(f"\n📍 محدوده:")
        print(f"   left={b['left']:.4f}, right={b['right']:.4f}")
        print(f"   bottom={b['bottom']:.4f}, top={b['top']:.4f}")

    print(f"\n✅ خوانده شد با: {info['method']}")
    print("=" * 55)


# ========================================================
# اجرا از خط فرمان
# ========================================================

if __name__ == "__main__":
    filepath = '../Urban(Tehran) - level 16.tif'
    try:
        info = get_pixel_size(filepath)
        print_info(info, filepath)
    except Exception as e:
        print(f"❌ خطا: {e}")
        sys.exit(1)
    
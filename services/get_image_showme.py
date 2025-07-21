import datetime
import ee

def get_auto_vis_params_sentinel(image, region):
    stats = image.reduceRegion(
        reducer=ee.Reducer.percentile([2, 98]),
        geometry=region,
        scale=10,
        maxPixels=1e8
    ).getInfo()
    return {
        "min": [stats["B4_p2"], stats["B3_p2"], stats["B2_p2"]],
        "max": [stats["B4_p98"], stats["B3_p98"], stats["B2_p98"]],
        "bands": ["B4", "B3", "B2"],
        "format": "png",
        "scale": 10,
        "region": region.getInfo()
    }

def get_auto_vis_params_landsat(image, region):
    stats = image.reduceRegion(
        reducer=ee.Reducer.percentile([2, 98]),
        geometry=region,
        scale=30,
        maxPixels=1e8,
    ).getInfo()
    return {
        "min": [stats["SR_B4_p2"], stats["SR_B3_p2"], stats["SR_B2_p2"]],
        "max": [stats["SR_B4_p98"], stats["SR_B3_p98"], stats["SR_B2_p98"]],
        "bands": ["SR_B4", "SR_B3", "SR_B2"],
        "format": "png",
        "dimensions": 512,
        "region": region.getInfo(),
        "noData": 0,
        "backgroundColor": "00000000"
    }

def get_image_by_date(sensor, lat, lon, current_date_str, direction="latest"):
    point = ee.Geometry.Point([lon, lat])
    if sensor == "Sentinel 2":
        region = point.buffer(2000).bounds()
        collection = ee.ImageCollection("COPERNICUS/S2") \
            .filterBounds(point) \
            .filterDate("2024-01-01", datetime.date.today().isoformat()) \
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
        get_params_fn = get_auto_vis_params_sentinel
        sensor_label = "Sentinel 2"
    elif sensor == "Landsat 8":
        region = point.buffer(7680).bounds()
        collection = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2") \
            .filterBounds(point) \
            .filterDate("2024-01-01", datetime.date.today().isoformat()) \
            .filterMetadata('CLOUD_COVER', 'less_than', 20)
        get_params_fn = get_auto_vis_params_landsat
        sensor_label = "Landsat 8"
    elif sensor == "Landsat 9":
        region = point.buffer(7680).bounds()
        collection = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2") \
            .filterBounds(region) \
            .filterDate("2021-01-01", datetime.date.today().isoformat()) \
            .filterMetadata('CLOUD_COVER', 'less_than', 20)
        get_params_fn = get_auto_vis_params_landsat
        sensor_label = "Landsat 9"
    else:
        return None, None, None

    if current_date_str is None or direction == "latest":
        filtered = collection.sort("system:time_start", False)
    else:
        current_date = ee.Date(current_date_str)
        if direction == "previous":
            filtered = collection.filterDate("2024-01-01", current_date.format("YYYY-MM-dd")) \
                                 .sort("system:time_start", False)
        elif direction == "next":
            filtered = collection.filterDate(current_date.advance(1, "day"), datetime.date.today().isoformat()) \
                                 .sort("system:time_start")
        else:
            raise ValueError("Direction must be 'previous', 'next', or 'latest'")
    count = filtered.size().getInfo()
    print(f"[DEBUG] {sensor_label}: found {count} images after filters (direction={direction}).")
    image = filtered.first()
    info = image.getInfo()
    if info is None:
        return None, None, None
    if not image:
        return None, None, None

    image = image.unmask(0)
    date_str = image.date().format("YYYY-MM-dd").getInfo()
    params = get_params_fn(image, region)
    url = image.getThumbURL(params)
    return url, date_str, sensor_label

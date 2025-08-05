"""
Monthly-focused satellite data collection with precision regions
"""

import ee
from google.cloud import bigquery
import pandas as pd
from datetime import datetime, timedelta
import calendar
import logging

logger = logging.getLogger(__name__)

PROJECT_ID = "sound-sanctuary-451320-b8"
DATASET_ID = "satellite_data"
TABLE_ID = "raw_satellite_metrics"


def collect_satellite_data(region_name: str, latitude: float, longitude: float) -> bool:
    """
    Smart collection with precision regions and automatic gap detection
    
    CHANGED: Uses coordinate-based region_id for unique spatial storage
    
    Args:
        region_name: Display name (for logging)
        latitude: Exact latitude coordinate
        longitude: Exact longitude coordinate
        
    Returns:
        bool: True if successful
    """
    
    try:
        # NEW: Create precision region ID from coordinates
        region_id = f"{latitude:.3f}_{longitude:.3f}"
        
        logger.info(f"Smart collection for {region_name} (Precision ID: {region_id})")
        
        # Use precision region ID for all data operations
        return collect_with_gap_filling(region_id, region_name, latitude, longitude)
        
    except Exception as e:
        logger.error(f"Smart collection failed for {region_name}: {e}")
        return False


def collect_with_gap_filling(region_id: str, display_name: str, latitude: float, longitude: float) -> bool:
    """
    Smart collection with automatic gap filling using precision regions
    
    CHANGED: Uses region_id instead of region_name for storage
    """
    
    try:
        # Get the latest month we have data for (using precision region_id)
        latest_month = _get_latest_data_month(region_id)
        current_month = datetime.now().strftime('%Y-%m')
        
        if latest_month is None:
            # No historical data - collect last 6 months
            logger.info(f"No historical data for {display_name}, collecting 6 months")
            return collect_satellite_data_monthly(region_id, display_name, latitude, longitude)
        
        # Calculate months we need to fill
        missing_months = _get_missing_months(latest_month, current_month)
        
        if not missing_months:
            logger.info(f"Data is up to date for {display_name}")
            return True
        
        logger.info(f"Found {len(missing_months)} missing months for {display_name}: {missing_months}")
        
        # Collect data for all missing months
        return _fill_missing_months(region_id, display_name, latitude, longitude, missing_months)
        
    except Exception as e:
        logger.error(f"Gap filling failed for {display_name}: {e}")
        return False


def collect_satellite_data_monthly(region_id: str, display_name: str, latitude: float, longitude: float) -> bool:
    """
    Collect satellite data with monthly sampling for trend analysis
    
    CHANGED: Stores data using precision region_id
    """
    
    try:
        ee.Initialize()
        logger.info(f"Collecting monthly data for {display_name} at ({latitude}, {longitude})")
        
        # Define region
        point = ee.Geometry.Point([longitude, latitude])
        region = point.buffer(5000).bounds()
        
        # Collect data for last 6 months
        monthly_data = []
        current_date = datetime.now()
        
        for month_offset in range(6):  # Last 6 months
            # Calculate month boundaries
            target_month = current_date - timedelta(days=30 * month_offset)
            month_start = target_month.replace(day=1)
            
            # Get last day of month
            last_day = calendar.monthrange(target_month.year, target_month.month)[1]
            month_end = target_month.replace(day=last_day)
            
            logger.info(f"Processing month: {month_start.strftime('%Y-%m')} ({month_start.date()} to {month_end.date()})")
            
            # Get averaged data for this month (2-3 images)
            month_data = _get_monthly_averaged_data(point, region, month_start, month_end, max_images=3)
            
            if month_data:
                monthly_data.append(month_data)
                logger.info(f"✅ Averaged {month_data['image_count']} images for {month_start.strftime('%Y-%m')} (NDVI: {month_data['ndvi_mean']:.3f})")
            else:
                logger.warning(f"❌ No suitable images for {month_start.strftime('%Y-%m')}")
        
        if not monthly_data:
            logger.error(f"No monthly data collected for {display_name}")
            return False
        
        # Add region info to all records (CHANGED: use region_id)
        for record in monthly_data:
            record.update({
                'region_id': region_id,                    # NEW: Precision storage key
                'region_name': display_name,               # Display name for queries
                'latitude': latitude,
                'longitude': longitude,
                'processing_date': datetime.now()
            })
        
        # Upload to BigQuery
        return _upload_to_bigquery(monthly_data)
        
    except Exception as e:
        logger.error(f"Monthly collection failed for {display_name}: {e}")
        return False


def _get_latest_data_month(region_id: str) -> str:
    """Get the latest month we have data for (CHANGED: uses region_id)"""
    
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
        
        query = f"""
        SELECT MAX(acquisition_month) as latest_month
        FROM `{table_id}`
        WHERE region_id = @region_id
        AND acquisition_month IS NOT NULL
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("region_id", "STRING", region_id)
            ]
        )
        
        results = client.query(query, job_config=job_config).result()
        
        for row in results:
            return row.latest_month
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to get latest month for region {region_id}: {e}")
        return None


def _fill_missing_months(region_id: str, display_name: str, latitude: float, longitude: float, missing_months: list) -> bool:
    """Fill in data for missing months (CHANGED: uses region_id)"""
    
    try:
        ee.Initialize()
        point = ee.Geometry.Point([longitude, latitude])
        region = point.buffer(5000).bounds()
        
        collected_data = []
        
        for month_str in missing_months:
            logger.info(f"Filling gap: collecting data for {month_str}")
            
            # Parse month
            month_date = datetime.strptime(month_str, '%Y-%m')
            month_start = month_date.replace(day=1)
            
            # Get last day of month
            last_day = calendar.monthrange(month_date.year, month_date.month)[1]
            month_end = month_date.replace(day=last_day)
            
            # Get averaged data for this month
            month_data = _get_monthly_averaged_data(point, region, month_start, month_end, max_images=3)
            
            if month_data:
                month_data.update({
                    'region_id': region_id,                # NEW: Precision storage
                    'region_name': display_name,           # Display name  
                    'latitude': latitude,
                    'longitude': longitude,
                    'processing_date': datetime.now(),
                    'collection_type': 'gap_fill'
                })
                collected_data.append(month_data)
                logger.info(f"✅ Gap filled for {month_str}: NDVI={month_data['ndvi_mean']:.3f}")
            else:
                logger.warning(f"❌ Could not fill gap for {month_str} (no suitable images)")
        
        if collected_data:
            success = _upload_to_bigquery(collected_data)
            if success:
                logger.info(f"✅ Successfully filled {len(collected_data)} month gaps for {display_name}")
            return success
        else:
            logger.warning(f"No data collected during gap filling for {display_name}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to fill missing months: {e}")
        return False


def _get_monthly_averaged_data(point, region, month_start, month_end, max_images=3):
    """
    Get multiple high-quality images for a month and calculate averaged metrics
    (UNCHANGED - this function works with coordinates, not region names)
    """
    
    try:
        # Sentinel-2 collection for this month
        collection = ee.ImageCollection("COPERNICUS/S2") \
            .filterBounds(point) \
            .filterDate(month_start.strftime('%Y-%m-%d'), month_end.strftime('%Y-%m-%d')) \
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 25)) \
            .sort("CLOUDY_PIXEL_PERCENTAGE") \
            .limit(max_images)  # Take best 2-3 images
        
        # Get all available images
        images_info = collection.getInfo()
        images_list = images_info.get('features', [])
        
        if not images_list:
            logger.warning(f"No suitable images found for {month_start.strftime('%Y-%m')}")
            return None
        
        logger.info(f"Processing {len(images_list)} images for {month_start.strftime('%Y-%m')}")
        
        # Process each image and collect NDVI values
        ndvi_values = []
        cloud_percentages = []
        image_dates = []
        image_ids = []
        
        for i, img_info in enumerate(images_list):
            try:
                image = ee.Image(img_info['id'])
                properties = img_info['properties']
                
                # Calculate NDVI
                ndvi = image.normalizedDifference(['B8', 'B4'])
                ndvi_stats = ndvi.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=region,
                    scale=20,
                    maxPixels=1e8
                ).getInfo()
                
                ndvi_value = ndvi_stats.get('nd')
                if ndvi_value is not None:
                    ndvi_values.append(ndvi_value)
                    cloud_percentages.append(properties.get('CLOUDY_PIXEL_PERCENTAGE', 0))
                    
                    # Extract date
                    timestamp = int(properties['system:time_start']) / 1000
                    image_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                    image_dates.append(image_date)
                    image_ids.append(img_info['id'])
                    
                    logger.info(f"  Image {i+1}: {image_date}, NDVI={ndvi_value:.3f}, Clouds={properties.get('CLOUDY_PIXEL_PERCENTAGE', 0):.1f}%")
                
            except Exception as e:
                logger.error(f"Failed to process image {i+1}: {e}")
                continue
        
        if not ndvi_values:
            return None
        
        # Calculate averaged statistics
        avg_ndvi = sum(ndvi_values) / len(ndvi_values)
        avg_cloud_cover = sum(cloud_percentages) / len(cloud_percentages)
        
        # Calculate standard deviation for quality assessment
        if len(ndvi_values) > 1:
            variance = sum((x - avg_ndvi) ** 2 for x in ndvi_values) / len(ndvi_values)
            std_dev = variance ** 0.5
        else:
            std_dev = 0.0
        
        return {
            'acquisition_month': month_start.strftime('%Y-%m'),
            'image_count': len(ndvi_values),
            'image_ids': image_ids,
            'image_dates': image_dates,
            'ndvi_mean': round(avg_ndvi, 4),
            'ndvi_std': round(std_dev, 4),
            'ndvi_min': round(min(ndvi_values), 4),
            'ndvi_max': round(max(ndvi_values), 4),
            'cloud_percentage': round(avg_cloud_cover, 1),
            'sensor': 'Sentinel-2',
            'data_quality': _assess_monthly_data_quality(len(ndvi_values), avg_cloud_cover, std_dev)
        }
        
    except Exception as e:
        logger.error(f"Failed to get averaged data for month {month_start.strftime('%Y-%m')}: {e}")
        return None


def _assess_monthly_data_quality(image_count, avg_cloud_cover, std_dev):
    """Assess the quality of monthly averaged data (UNCHANGED)"""
    
    quality_score = 0
    
    # Image count factor (more images = better)
    if image_count >= 3:
        quality_score += 40
    elif image_count >= 2:
        quality_score += 25
    else:
        quality_score += 10
    
    # Cloud cover factor (less clouds = better)
    if avg_cloud_cover < 10:
        quality_score += 40
    elif avg_cloud_cover < 20:
        quality_score += 25
    else:
        quality_score += 10
    
    # Consistency factor (lower std dev = more reliable)
    if std_dev < 0.05:
        quality_score += 20
    elif std_dev < 0.10:
        quality_score += 10
    else:
        quality_score += 5
    
    # Determine quality rating
    if quality_score >= 80:
        return 'excellent'
    elif quality_score >= 60:
        return 'good'
    elif quality_score >= 40:
        return 'fair'
    else:
        return 'poor'


def _get_missing_months(latest_month: str, current_month: str) -> list:
    """Calculate which months are missing (UNCHANGED)"""
    
    try:
        # Parse dates
        latest_date = datetime.strptime(latest_month, '%Y-%m')
        current_date = datetime.strptime(current_month, '%Y-%m')
        
        # If current month is same or older than latest, no gap
        if current_date <= latest_date:
            return []
        
        # Generate list of missing months
        missing_months = []
        check_date = latest_date
        
        while check_date < current_date:
            # Move to next month
            if check_date.month == 12:
                check_date = check_date.replace(year=check_date.year + 1, month=1)
            else:
                check_date = check_date.replace(month=check_date.month + 1)
            
            missing_months.append(check_date.strftime('%Y-%m'))
        
        return missing_months
        
    except Exception as e:
        logger.error(f"Failed to calculate missing months: {e}")
        return []


def _upload_to_bigquery(data_rows) -> bool:
    """Upload monthly data to BigQuery (UNCHANGED)"""
    
    try:
        client = bigquery.Client(project=PROJECT_ID)
        df = pd.DataFrame(data_rows)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
        
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
            schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
        )
        
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        
        logger.info(f"✅ Uploaded {len(data_rows)} monthly records to BigQuery")
        return True
        
    except Exception as e:
        logger.error(f"BigQuery upload failed: {e}")
        return False
"""
Simple checker if satellite data exists in BigQuery
"""

from google.cloud import bigquery
import logging

logger = logging.getLogger(__name__)

PROJECT_ID = "sound-sanctuary-451320-b8"
DATASET_ID = "satellite_data"
TABLE_ID = "raw_satellite_metrics"


def should_collect_data(region_name: str) -> bool:
    """
    Check if we need to collect satellite data for a region
    
    Args:
        region_name: Name of the region to check
        
    Returns:
        bool: True if data collection needed
    """
    
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
        
        query = f"""
        SELECT COUNT(*) as record_count
        FROM `{table_id}`
        WHERE region_name = @region_name
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("region_name", "STRING", region_name)
            ]
        )
        
        results = client.query(query, job_config=job_config).result()
        
        for row in results:
            record_count = row.record_count
            
            # Need data if less than 3 records
            if record_count < 3:
                logger.info(f"Need data for {region_name}: only {record_count} records")
                return True
            else:
                logger.info(f"Sufficient data for {region_name}: {record_count} records")
                return False
    
    except Exception as e:
        logger.warning(f"Failed to check data for {region_name}: {e}")
        return True  # Safe fallback: collect data


def get_data_summary(region_name: str) -> str:
    """
    Get summary of existing data for a region
    
    Args:
        region_name: Name of the region
        
    Returns:
        str: Human readable summary
    """
    
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
        
        query = f"""
        SELECT 
            COUNT(*) as record_count,
            MAX(acquisition_date) as latest_date
        FROM `{table_id}`
        WHERE region_name = @region_name
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("region_name", "STRING", region_name)
            ]
        )
        
        results = client.query(query, job_config=job_config).result()
        
        for row in results:
            count = row.record_count
            latest = row.latest_date
            
            if count == 0:
                return f"No data found for {region_name}. Collecting new data..."
            else:
                return f"Found {count} records for {region_name}, latest: {latest}"
    
    except Exception as e:
        logger.error(f"Failed to get summary for {region_name}: {e}")
        return f"Could not check data for {region_name}"
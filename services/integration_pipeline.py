"""
End-to-end pipeline: User Location → Data Check → Satellite Collection → Analysis
"""

import logging
from typing import Dict, Any, Optional
from services.user_personalization import UserPersonalization
from services.data_checker import should_collect_data, get_data_summary
from services.satellite_collector import collect_satellite_data

logger = logging.getLogger(__name__)


class IntegrationPipeline:
    """Complete pipeline for user location analysis"""
    
    def __init__(self):
        self.personalizer = UserPersonalization()

    async def analyze_user_location(self, user_id: int, location_name: str) -> Dict[str, Any]:
        """
        Complete analysis pipeline for a user's location
        
        Args:
            user_id: Telegram user ID
            location_name: User's custom location name
            
        Returns:
            dict: Analysis results with status and data
        """
        
        try:
            logger.info(f"Starting analysis pipeline for user {user_id}, location: {location_name}")
            
            # Step 1: Get user location data
            locations = self.personalizer.get_user_locations(user_id)
            
            if location_name not in locations:
                return {
                    'success': False,
                    'error': 'location_not_found',
                    'message': f"Location '{location_name}' not found in your personal locations."
                }
            
            location_data = locations[location_name]
            region_name = location_data['actual_location']
            lat = location_data['lat']
            lon = location_data['lon']
            
            logger.info(f"Location found: {location_name} → {region_name} ({lat}, {lon})")
            
            # Step 2: Check if satellite data exists
            needs_collection = should_collect_data(region_name)
            data_status = get_data_summary(region_name)
            
            logger.info(f"Data status for {region_name}: needs_collection={needs_collection}")
            
            result = {
                'success': True,
                'location_name': location_name,
                'region_name': region_name,
                'coordinates': {'lat': lat, 'lon': lon},
                'data_status': data_status,
                'needs_collection': needs_collection
            }
            
            # Step 3: Collect satellite data if needed
            if needs_collection:
                logger.info(f"Collecting satellite data for {region_name}")
                
                collection_success = collect_satellite_data(region_name, lat, lon)
                
                if collection_success:
                    result['collection_status'] = 'success'
                    result['message'] = f"✅ Successfully collected new satellite data for {location_name}"
                    
                    # Update data status after collection
                    new_data_status = get_data_summary(region_name)
                    result['updated_data_status'] = new_data_status
                    
                else:
                    result['collection_status'] = 'failed'
                    result['message'] = f"❌ Failed to collect satellite data for {location_name}"
                    
            else:
                result['collection_status'] = 'not_needed'
                result['message'] = f"📊 Using existing satellite data for {location_name}"
            
            # Step 4: Basic analysis (simple for now)
            analysis = await self._generate_basic_analysis(region_name, location_data)
            result['analysis'] = analysis
            
            logger.info(f"Pipeline completed successfully for {location_name}")
            return result
            
        except Exception as e:
            logger.error(f"Pipeline failed for user {user_id}, location {location_name}: {e}")
            return {
                'success': False,
                'error': 'pipeline_error',
                'message': f"❌ Analysis failed: {str(e)}"
            }

    async def _generate_basic_analysis(self, region_name: str, location_data: Dict) -> Dict[str, Any]:
        """
        Generate basic analysis from available data
        
        Args:
            region_name: The actual city/region name
            location_data: User's location info
            
        Returns:
            dict: Basic analysis results
        """
        
        try:
            from google.cloud import bigquery
            
            client = bigquery.Client(project="sound-sanctuary-451320-b8")
            
            # Simple query to get basic metrics
            query = f"""
            SELECT 
                COUNT(*) as total_observations,
                AVG(ndvi_mean) as avg_vegetation,
                AVG(cloud_percentage) as avg_cloud_cover,
                MIN(acquisition_date) as earliest_date,
                MAX(acquisition_date) as latest_date
            FROM `sound-sanctuary-451320-b8.satellite_data.raw_satellite_metrics`
            WHERE region_name = @region_name
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("region_name", "STRING", region_name)
                ]
            )
            
            results = client.query(query, job_config=job_config).result()
            
            for row in results:
                if row.total_observations > 0:
                    return {
                        'has_data': True,
                        'total_observations': row.total_observations,
                        'vegetation_index': round(row.avg_vegetation or 0, 3),
                        'data_quality': round(row.avg_cloud_cover or 0, 1),
                        'date_range': f"{row.earliest_date} to {row.latest_date}",
                        'interpretation': self._interpret_metrics(row.avg_vegetation, row.avg_cloud_cover)
                    }
            
            return {
                'has_data': False,
                'message': 'No satellite data available yet'
            }
            
        except Exception as e:
            logger.error(f"Analysis generation failed: {e}")
            return {
                'has_data': False,
                'error': str(e)
            }

    def _interpret_metrics(self, ndvi: float, cloud_cover: float) -> Dict[str, str]:
        """Simple interpretation of satellite metrics"""
        
        interpretation = {}
        
        # NDVI interpretation
        if ndvi is not None:
            if ndvi > 0.6:
                interpretation['vegetation'] = "🌲 Very green area with healthy vegetation"
            elif ndvi > 0.4:
                interpretation['vegetation'] = "🌱 Moderate vegetation coverage"
            elif ndvi > 0.2:
                interpretation['vegetation'] = "🏙️ Urban area with some green spaces"
            else:
                interpretation['vegetation'] = "🏢 Highly urban/built-up area"
        
        # Cloud cover interpretation
        if cloud_cover is not None:
            if cloud_cover < 10:
                interpretation['data_quality'] = "☀️ Excellent data quality (clear skies)"
            elif cloud_cover < 20:
                interpretation['data_quality'] = "⛅ Good data quality (some clouds)"
            else:
                interpretation['data_quality'] = "☁️ Fair data quality (cloudy conditions)"
        
        return interpretation


def format_analysis_for_user(analysis_result: Dict[str, Any]) -> str:
    """
    Format analysis results for user display in Telegram
    
    Args:
        analysis_result: Result from analyze_user_location
        
    Returns:
        str: Formatted message for user
    """
    
    if not analysis_result['success']:
        return f"❌ Analysis failed: {analysis_result.get('message', 'Unknown error')}"
    
    location_name = analysis_result['location_name']
    region_name = analysis_result['region_name']
    coordinates = analysis_result['coordinates']
    
    message = f"📊 **ANALYSIS: {location_name}**\n"
    message += f"📍 Located in: {region_name}\n"
    message += f"🗺️ Coordinates: {coordinates['lat']:.4f}, {coordinates['lon']:.4f}\n\n"
    
    # Data collection status
    message += f"💾 Data Status: {analysis_result['message']}\n\n"
    
    # Analysis results
    analysis = analysis_result.get('analysis', {})
    
    if analysis.get('has_data'):
        message += f"📈 **SATELLITE ANALYSIS:**\n"
        message += f"🛰️ Observations: {analysis['total_observations']} satellite images\n"
        message += f"🌱 Vegetation Index: {analysis['vegetation_index']} (NDVI)\n"
        message += f"☁️ Data Quality: {analysis['data_quality']}% cloud cover\n"
        message += f"📅 Data Period: {analysis['date_range']}\n\n"
        
        # Interpretations
        interpretation = analysis.get('interpretation', {})
        if interpretation:
            message += f"🔍 **INSIGHTS:**\n"
            for key, value in interpretation.items():
                message += f"• {value}\n"
    else:
        message += f"📊 **Analysis will be available after data collection**\n"
    
    return message


# Quick integration test function
async def test_integration_pipeline():
    """Test the complete pipeline"""
    
    print("🧪 Testing Integration Pipeline")
    print("=" * 50)
    
    # Test with a sample user location
    pipeline = IntegrationPipeline()
    
    # Mock user ID and location for testing
    test_user_id = 12345
    test_location_name = "Test Location"
    
    result = await pipeline.analyze_user_location(test_user_id, test_location_name)
    
    formatted_result = format_analysis_for_user(result)
    print(formatted_result)
    
    return result


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_integration_pipeline())
"""
City locator service with precision region support
"""

import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_location_info(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get location information from coordinates with precision region support
    
    Args:
        latitude: User's latitude coordinate
        longitude: User's longitude coordinate
        
    Returns:
        dict: Location info with both city context and precision region ID
        {
            'region_name': str,        # City name for display
            'region_id': str,          # NEW: Unique coordinate-based ID  
            'lat': float,              # Exact coordinates
            'lon': float,
            'display_name': str,       # Full location description
            'is_city': bool            # Whether actual city found
        }
    """
    
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        'lat': latitude,
        'lon': longitude,
        'format': 'json',
        'addressdetails': 1,
        'zoom': 10
    }
    headers = {'User-Agent': 'SatelliteDataBot/1.0'}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        address = data.get('address', {})
        
        # Extract city name with fallback hierarchy
        city_name = (
            address.get('city') or 
            address.get('town') or 
            address.get('village') or 
            address.get('municipality') or
            address.get('county')
        )
        
        if city_name:
            # NEW: Create precision region ID from exact coordinates
            region_id = f"{latitude:.3f}_{longitude:.3f}"
            
            # Enhanced display name with rough area indication
            country = address.get('country', 'Unknown')
            base_display = f"{city_name}, {country}"
            
            # Add rough district hint for large cities
            district_hint = _get_district_hint(latitude, longitude, city_name)
            enhanced_display = f"{city_name} ({district_hint}), {country}" if district_hint != "Area" else base_display
            
            return {
                'region_name': city_name,                    # Keep original for backwards compatibility
                'region_id': region_id,                      # NEW: Unique storage identifier
                'lat': float(data.get('lat', latitude)),
                'lon': float(data.get('lon', longitude)),
                'display_name': enhanced_display,            # Enhanced with district
                'base_display': base_display,                # Simple city, country
                'is_city': True
            }
    
    except Exception as e:
        logger.warning(f"City lookup failed: {e}")
    
    # Fallback: use coordinates as location name
    coord_name = f"{latitude:.4f}, {longitude:.4f}"
    region_id = f"{latitude:.3f}_{longitude:.3f}"  # NEW: Consistent ID format
    
    return {
        'region_name': coord_name,
        'region_id': region_id,                      # NEW: Coordinate-based ID
        'lat': latitude,
        'lon': longitude,
        'display_name': f"Location {coord_name}",
        'base_display': coord_name,
        'is_city': False
    }


def _get_district_hint(lat: float, lon: float, city_name: str) -> str:
    """Generate rough district hint for large cities"""
    
    # Known city centers for district hints
    city_centers = {
        'Berlin': (52.5200, 13.4050),
        'Munich': (48.1351, 11.5820),
        'Hamburg': (53.5511, 9.9937),
        'Frankfurt': (50.1109, 8.6821),
        'Cologne': (50.9375, 6.9603),
        'Stuttgart': (48.7758, 9.1829),
        'Düsseldorf': (51.2277, 6.7735)
    }
    
    if city_name not in city_centers:
        return "Area"
    
    center_lat, center_lon = city_centers[city_name]
    
    # Calculate relative position
    lat_diff = lat - center_lat
    lon_diff = lon - center_lon
    
    # Simple directional hints
    if abs(lat_diff) < 0.01 and abs(lon_diff) < 0.01:
        return "Central"
    elif lat_diff > 0.02:
        return "North" + ("east" if lon_diff > 0.02 else "west" if lon_diff < -0.02 else "")
    elif lat_diff < -0.02:
        return "South" + ("east" if lon_diff > 0.02 else "west" if lon_diff < -0.02 else "")
    elif lon_diff > 0.02:
        return "East"
    elif lon_diff < -0.02:
        return "West" 
    else:
        return "Central"


def update_user_location(user_id: int, latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Update user session with precision location info
    
    Args:
        user_id: Telegram user ID
        latitude: User's latitude
        longitude: User's longitude
        
    Returns:
        dict: Location info that was stored in session
    """
    from services.user_sessions import get_user_session, user_sessions
    
    location_info = get_location_info(latitude, longitude)
    
    session = get_user_session(user_id) or {}
    session.update({
        'lat': location_info['lat'],
        'lon': location_info['lon'], 
        'region_name': location_info['region_name'],      # Keep for display
        'region_id': location_info['region_id'],          # NEW: For precise storage
        'display_name': location_info['display_name'],
        'is_city': location_info['is_city']
    })
    
    user_sessions[user_id] = session
    logger.info(f"Updated location for user {user_id}: {location_info['display_name']} (ID: {location_info['region_id']})")
    
    return location_info
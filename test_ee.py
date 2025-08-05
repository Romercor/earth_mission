"""
Simple city finder using OpenStreetMap API
Returns nearest city name or coordinates as fallback
"""

import requests
import math


def find_nearest_city(latitude: float, longitude: float) -> dict:
    """
    Find nearest city from coordinates using OpenStreetMap
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        dict: Either city info or coordinate fallback
            - If city found: {'name': 'Berlin', 'country': 'Germany', 'lat': 52.5, 'lon': 13.4}
            - If no city: {'name': '52.5200, 13.4050', 'country': 'Unknown', 'lat': 52.5, 'lon': 13.4}
    """
    
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        'lat': latitude,
        'lon': longitude,
        'format': 'json',
        'addressdetails': 1,
        'zoom': 10
    }
    headers = {'User-Agent': 'SatelliteBot/1.0'}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        address = data.get('address', {})
        
        # Try to find city name
        city_name = (
            address.get('city') or 
            address.get('town') or 
            address.get('village') or 
            address.get('municipality')
        )
        
        if city_name:
            # City found - return city info
            return {
                'name': city_name,
                'country': address.get('country', 'Unknown'),
                'lat': float(data.get('lat', latitude)),
                'lon': float(data.get('lon', longitude))
            }
    
    except Exception:
        pass  # Fallback to coordinates
    
    # No city found or API failed - return coordinates as name
    return {
        'name': f"{latitude:.4f}, {longitude:.4f}",
        'country': 'Unknown',
        'lat': latitude,
        'lon': longitude
    }


# Test function
if __name__ == "__main__":
    test_cases = [
        (53.6320025980369, 11.367526770509686),  # Berlin
        (40.7128, -74.0060), # NYC  
        (71.0, 8.0),         # Middle of nowhere
    ]
    
    for lat, lon in test_cases:
        result = find_nearest_city(lat, lon)
        print(f"({lat}, {lon}) → {result['name']}, {result['country']}")
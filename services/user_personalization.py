"""
services/user_personalization.py

Flexible user location management - users define their own location names
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from services.user_sessions import user_sessions
from services.city_locator import get_location_info
from google.cloud import bigquery

logger = logging.getLogger(__name__)

PROJECT_ID = "sound-sanctuary-451320-b8"
DATASET_ID = "satellite_data"


class UserPersonalization:
    """Manage user's personal locations and preferences"""
    
    def __init__(self):
        self.client = bigquery.Client(project=PROJECT_ID)
    
    def add_user_location(self, user_id: int, location_name: str, 
                         latitude: float, longitude: float) -> bool:
        """
        Add a custom-named location for user
        
        Args:
            user_id: Telegram user ID
            location_name: User's custom name (e.g., "Meine Wohnung", "Omas Haus", "Lieblings-Café")
            latitude: Location latitude  
            longitude: Location longitude
            
        Returns:
            bool: Success status
        """
        
        try:
            # Get actual location info from coordinates
            location_info = get_location_info(latitude, longitude)
            
            # Initialize user session if not exists
            if user_id not in user_sessions:
                user_sessions[user_id] = {}
            
            # Initialize personal locations
            if 'personal_locations' not in user_sessions[user_id]:
                user_sessions[user_id]['personal_locations'] = {}
            
            # Store user's custom location
            user_sessions[user_id]['personal_locations'][location_name] = {
                'user_name': location_name,  # User's custom name
                'actual_location': location_info['region_name'],  # Real city/area name
                'display_name': location_info['display_name'],
                'lat': location_info['lat'],
                'lon': location_info['lon'], 
                'is_city': location_info['is_city'],
                'added_date': str(datetime.now().date())
            }
            
            logger.info(f"Added location '{location_name}' for user {user_id}: {location_info['region_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add location for user {user_id}: {e}")
            return False
    
    def get_user_locations(self, user_id: int) -> Dict[str, Dict]:
        """
        Get all user's personal locations
        
        Returns:
            dict: User's locations with their custom names
        """
        
        session = user_sessions.get(user_id, {})
        return session.get('personal_locations', {})
    
    def remove_user_location(self, user_id: int, location_name: str) -> bool:
        """Remove a user's custom location"""
        
        try:
            if user_id in user_sessions and 'personal_locations' in user_sessions[user_id]:
                if location_name in user_sessions[user_id]['personal_locations']:
                    del user_sessions[user_id]['personal_locations'][location_name]
                    logger.info(f"Removed location '{location_name}' for user {user_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove location: {e}")
            return False
    
    def rename_user_location(self, user_id: int, old_name: str, new_name: str) -> bool:
        """Rename a user's location"""
        
        try:
            locations = self.get_user_locations(user_id)
            if old_name in locations:
                # Copy location data with new name
                location_data = locations[old_name].copy()
                location_data['user_name'] = new_name
                
                # Add with new name, remove old
                user_sessions[user_id]['personal_locations'][new_name] = location_data
                del user_sessions[user_id]['personal_locations'][old_name]
                
                logger.info(f"Renamed location '{old_name}' to '{new_name}' for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to rename location: {e}")
            return False
    
    def get_user_dashboard(self, user_id: int) -> str:
        """
        Generate personalized dashboard for user
        
        Returns:
            str: Formatted dashboard text
        """
        
        locations = self.get_user_locations(user_id)
        
        if not locations:
            return "📍 You haven't added any personal locations yet!\n\nUse /add_location to get started."
        
        dashboard = "🏙️ YOUR PERSONAL URBAN INTELLIGENCE DASHBOARD\n"
        dashboard += "=" * 50 + "\n\n"
        
        for i, (user_name, location_data) in enumerate(locations.items(), 1):
            actual_location = location_data['actual_location']
            is_city = "🏙️" if location_data['is_city'] else "📍"
            
            dashboard += f"{i}. {is_city} {user_name}\n"
            dashboard += f"   📍 Located in: {actual_location}\n"
            dashboard += f"   📅 Added: {location_data['added_date']}\n\n"
        
        dashboard += f"💡 Use /analyze [location_name] to get detailed insights\n"
        dashboard += f"📊 Use /compare to compare your locations\n"
        dashboard += f"⚙️ Use /manage_locations to edit your list"
        
        return dashboard
    
    def search_user_location(self, user_id: int, search_term: str) -> Optional[str]:
        """
        Find user location by partial name match
        
        Args:
            user_id: User ID
            search_term: Partial location name
            
        Returns:
            str: Exact location name if found
        """
        
        locations = self.get_user_locations(user_id)
        search_lower = search_term.lower()
        
        # Exact match first
        for location_name in locations:
            if location_name.lower() == search_lower:
                return location_name
        
        # Partial match
        for location_name in locations:
            if search_lower in location_name.lower():
                return location_name
        
        return None


# Helper functions for bot integration
def add_location_interactive(user_id: int, location_name: str, lat: float, lon: float) -> str:
    """
    Add location with user feedback
    
    Returns:
        str: Response message for user
    """
    
    personalizer = UserPersonalization()
    success = personalizer.add_user_location(user_id, location_name, lat, lon)
    
    if success:
        location_info = get_location_info(lat, lon)
        return (f"✅ Added '{location_name}' to your personal locations!\n\n"
                f"📍 Located in: {location_info['display_name']}\n"
                f"🎯 You can now use: /analyze {location_name}")
    else:
        return "❌ Failed to add location. Please try again."


def get_location_suggestions(partial_name: str) -> List[str]:
    """Get suggestions for location names (could be expanded)"""
    
    common_suggestions = [
        "Meine Wohnung", "Arbeitsplatz", "Elternhaus", "Freundin", 
        "Uni", "Lieblings-Café", "Fitnessstudio", "Investition",
        "Traumwohnung", "Kindheit", "Wochenendhaus", "Büro"
    ]
    
    # Filter suggestions that start with partial name
    if partial_name:
        suggestions = [s for s in common_suggestions 
                      if s.lower().startswith(partial_name.lower())]
        return suggestions[:5]  # Max 5 suggestions
    
    return common_suggestions[:8]  # Show some examples


if __name__ == "__main__":
    # Test the personalization system
    personalizer = UserPersonalization()
    
    # Test adding locations with custom names
    test_locations = [
        ("Meine Wohnung", 52.5200, 13.4050),
        ("Arbeitsplatz", 50.1109, 8.6821),
        ("Omas Haus", 48.1351, 11.5820),
        ("Lieblings-Café", 53.5511, 9.9937)
    ]
    
    test_user_id = 12345
    
    print("🧪 Testing User Personalization System")
    print("=" * 50)
    
    for location_name, lat, lon in test_locations:
        success = personalizer.add_user_location(test_user_id, location_name, lat, lon)
        print(f"Adding '{location_name}': {'✅' if success else '❌'}")
    
    print("\n📊 User Dashboard:")
    print(personalizer.get_user_dashboard(test_user_id))
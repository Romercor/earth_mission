"""
handlers/personalized_locations.py

Bot handlers for flexible user location management
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from services.user_personalization import UserPersonalization, add_location_interactive, get_location_suggestions
from services.user_sessions import user_sessions

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("add_location"))
async def start_add_location(message: Message):
    """Start process to add a personal location"""
    user_id = message.from_user.id
    
    # Initialize user session for location addition
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    
    user_sessions[user_id]['adding_location'] = {'step': 'name'}
    
    await message.answer(
        "📍 Let's add a personal location!\n\n"
        "First, what would you like to call this location?\n"
        "Examples: 'Meine Wohnung', 'Arbeitsplatz', 'Omas Haus', 'Lieblings-Café'\n\n"
        "✨ Be creative - use any name that's meaningful to you!",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(F.text, lambda message: message.from_user.id in user_sessions and 
                user_sessions[message.from_user.id].get('adding_location', {}).get('step') == 'name')
async def handle_location_name(message: Message):
    """Handle user's custom location name"""
    user_id = message.from_user.id
    location_name = message.text.strip()
    
    # Validate name
    if len(location_name) < 2:
        await message.answer("Please provide a name with at least 2 characters.")
        return
    
    if len(location_name) > 50:
        await message.answer("Please use a shorter name (max 50 characters).")
        return
    
    # Check if name already exists
    personalizer = UserPersonalization()
    existing_locations = personalizer.get_user_locations(user_id)
    
    if location_name in existing_locations:
        await message.answer(f"You already have a location called '{location_name}'.\nPlease choose a different name.")
        return
    
    # Store name and ask for coordinates
    user_sessions[user_id]['adding_location']['name'] = location_name
    user_sessions[user_id]['adding_location']['step'] = 'coordinates'
    
    # Create keyboard for location sharing
    location_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Share My Current Location", request_location=True)],
            [KeyboardButton(text="🗺️ Choose Location on Map")],
            [KeyboardButton(text="📝 Enter Coordinates Manually")],
            [KeyboardButton(text="❌ Cancel")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        f"Great! I'll call this location '{location_name}' 📝\n\n"
        f"Now, how would you like to set the location?\n\n"
        f"🗺️ **Choose Location on Map** - Pick any location worldwide\n"
        f"📍 **Share My Current Location** - Use your current GPS position\n"
        f"📝 **Enter Manually** - Type coordinates directly",
        reply_markup=location_keyboard
    )


@router.message(F.location, lambda message: message.from_user.id in user_sessions and 
                user_sessions[message.from_user.id].get('adding_location', {}).get('step') in ['coordinates', 'map_selection'])
async def handle_location_coordinates(message: Message):
    """Handle GPS coordinates from user (either current location or map-selected)"""
    user_id = message.from_user.id
    lat = message.location.latitude
    lon = message.location.longitude
    
    location_name = user_sessions[user_id]['adding_location']['name']
    current_step = user_sessions[user_id]['adding_location']['step']
    
    # Determine the source of the location
    location_source = "📍 Current location" if current_step == 'coordinates' else "🗺️ Map selection"
    
    # Add location
    response_text = add_location_interactive(user_id, location_name, lat, lon)
    
    # Enhance response with location source info
    enhanced_response = f"{response_text}\n\n💡 Source: {location_source}"
    
    # Clean up session
    del user_sessions[user_id]['adding_location']
    
    await message.answer(enhanced_response, reply_markup=ReplyKeyboardRemove())


@router.message(F.text == "🗺️ Choose Location on Map", 
                lambda message: message.from_user.id in user_sessions and 
                user_sessions[message.from_user.id].get('adding_location', {}).get('step') == 'coordinates')
async def request_map_location(message: Message):
    """Request location selection from map"""
    user_id = message.from_user.id
    user_sessions[user_id]['adding_location']['step'] = 'map_selection'
    
    # Create an inline keyboard with location request
    map_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📍 Send Location from Map", 
                                callback_data="request_location")]
        ]
    )
    
    await message.answer(
        "🗺️ **Pick Location from Map**\n\n"
        "Click the button below, then:\n"
        "1️⃣ Tap 'Location' in Telegram\n"
        "2️⃣ Choose 'Send My Current Location' **OR** 'Send Selected Location'\n"
        "3️⃣ If 'Send Selected Location': drag the map to choose any location worldwide\n"
        "4️⃣ Tap 'Send Selected Location'\n\n"
        "💡 You can pick ANY location - your home, work, a restaurant, or anywhere in the world!",
        reply_markup=map_keyboard
    )


@router.callback_query(F.data == "request_location")
async def handle_location_request_callback(callback_query: CallbackQuery):
    """Handle the inline button for location request"""
    
    # Create a keyboard that requests location
    location_request_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Send Location", request_location=True)],
            [KeyboardButton(text="❌ Cancel Location Selection")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback_query.message.answer(
        "📍 **Tap 'Send Location' below**\n\n"
        "When Telegram opens the location selector:\n"
        "• **Current Location**: Uses your GPS position\n"
        "• **Selected Location**: Let you choose any point on the map\n\n"
        "🌍 You can search for cities, addresses, or drag the map to any location!",
        reply_markup=location_request_keyboard
    )
    
    await callback_query.answer()


@router.message(F.text == "❌ Cancel Location Selection")
async def cancel_map_selection(message: Message):
    """Cancel map-based location selection"""
    user_id = message.from_user.id
    
    if user_id in user_sessions and 'adding_location' in user_sessions[user_id]:
        # Go back to coordinate selection step
        user_sessions[user_id]['adding_location']['step'] = 'coordinates'
    
    location_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Share My Current Location", request_location=True)],
            [KeyboardButton(text="🗺️ Choose Location on Map")],
            [KeyboardButton(text="📝 Enter Coordinates Manually")],
            [KeyboardButton(text="❌ Cancel")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "🔄 Back to location selection options:", 
        reply_markup=location_keyboard
    )


@router.message(F.text == "📝 Enter Coordinates Manually", 
                lambda message: message.from_user.id in user_sessions and 
                user_sessions[message.from_user.id].get('adding_location', {}).get('step') == 'coordinates')
async def request_manual_coordinates(message: Message):
    """Request manual coordinate entry"""
    user_id = message.from_user.id
    user_sessions[user_id]['adding_location']['step'] = 'manual_coords'
    
    await message.answer(
        "📝 Please enter coordinates in this format:\n"
        "latitude, longitude\n\n"
        "Example: 52.5200, 13.4050\n\n"
        "💡 You can get coordinates from Google Maps by right-clicking on a location.",
        reply_markup=ReplyKeyboardRemove()
    )
    """Request manual coordinate entry"""
    user_id = message.from_user.id
    user_sessions[user_id]['adding_location']['step'] = 'manual_coords'
    
    await message.answer(
        "📝 Please enter coordinates in this format:\n"
        "latitude, longitude\n\n"
        "Example: 52.5200, 13.4050\n\n"
        "💡 You can get coordinates from Google Maps by right-clicking on a location.",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(F.text.regexp(r'^-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?$'),
                lambda message: message.from_user.id in user_sessions and 
                user_sessions[message.from_user.id].get('adding_location', {}).get('step') == 'manual_coords')
async def handle_manual_coordinates(message: Message):
    """Handle manually entered coordinates"""
    user_id = message.from_user.id
    
    try:
        lat_str, lon_str = map(str.strip, message.text.split(","))
        lat = float(lat_str)
        lon = float(lon_str)
        
        location_name = user_sessions[user_id]['adding_location']['name']
        
        # Add location
        response_text = add_location_interactive(user_id, location_name, lat, lon)
        
        # Clean up session
        del user_sessions[user_id]['adding_location']
        
        await message.answer(response_text)
        
    except Exception as e:
        await message.answer(
            "❌ Invalid format. Please use: latitude, longitude\n"
            "Example: 52.5200, 13.4050"
        )


@router.message(F.text == "❌ Cancel")
async def cancel_add_location(message: Message):
    """Cancel location addition"""
    user_id = message.from_user.id
    
    if user_id in user_sessions and 'adding_location' in user_sessions[user_id]:
        del user_sessions[user_id]['adding_location']
    
    await message.answer("❌ Location addition cancelled.", reply_markup=ReplyKeyboardRemove())


@router.message(Command("my_locations"))
async def show_user_locations(message: Message):
    """Show user's personal dashboard"""
    user_id = message.from_user.id
    personalizer = UserPersonalization()
    
    dashboard = personalizer.get_user_dashboard(user_id)
    await message.answer(dashboard)


@router.message(Command("remove_location"))
async def start_remove_location(message: Message):
    """Start location removal process"""
    user_id = message.from_user.id
    personalizer = UserPersonalization()
    
    locations = personalizer.get_user_locations(user_id)
    
    if not locations:
        await message.answer("You don't have any personal locations to remove.")
        return
    
    # Create keyboard with user's locations
    keyboard_buttons = []
    for location_name in locations.keys():
        keyboard_buttons.append([KeyboardButton(text=f"🗑️ {location_name}")])
    
    keyboard_buttons.append([KeyboardButton(text="❌ Cancel")])
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    user_sessions[user_id]['removing_location'] = True
    
    await message.answer(
        "🗑️ Which location would you like to remove?",
        reply_markup=keyboard
    )


@router.message(F.text.startswith("🗑️ "), 
                lambda message: user_sessions.get(message.from_user.id, {}).get('removing_location'))
async def handle_location_removal(message: Message):
    """Handle location removal"""
    user_id = message.from_user.id
    location_name = message.text[3:]  # Remove "🗑️ " prefix
    
    personalizer = UserPersonalization()
    success = personalizer.remove_user_location(user_id, location_name)
    
    if success:
        response = f"✅ Removed '{location_name}' from your personal locations."
    else:
        response = f"❌ Failed to remove '{location_name}'. Location not found."
    
    # Clean up session
    user_sessions[user_id]['removing_location'] = False
    
    await message.answer(response, reply_markup=ReplyKeyboardRemove())


@router.message(Command("analyze"))
async def analyze_location(message: Message):
    """Analyze a specific user location with complete pipeline"""
    user_id = message.from_user.id
    command_parts = message.text.split(' ', 1)
    
    if len(command_parts) < 2:
        await message.answer(
            "Please specify which location to analyze.\n"
            "Usage: /analyze [location_name]\n\n"
            "Use /my_locations to see your available locations."
        )
        return
    
    search_term = command_parts[1]
    personalizer = UserPersonalization()
    
    # Find exact location name
    location_name = personalizer.search_user_location(user_id, search_term)
    
    if not location_name:
        locations = personalizer.get_user_locations(user_id)
        if locations:
            location_list = "\n".join([f"• {name}" for name in locations.keys()])
            await message.answer(
                f"❌ Location '{search_term}' not found.\n\n"
                f"Your locations:\n{location_list}"
            )
        else:
            await message.answer("You don't have any personal locations yet. Use /add_location to get started.")
        return
    
    # Send "analyzing" message
    analyzing_message = await message.answer(
        f"🔄 **Analyzing {location_name}...**\n\n"
        f"📡 Checking satellite data availability...\n"
        f"🛰️ Collecting new data if needed...\n"
        f"📊 Generating insights...\n\n"
        f"⏱️ This may take 30-60 seconds..."
    )
    
    try:
        # Import and run the integration pipeline
        from services.integration_pipeline import IntegrationPipeline, format_analysis_for_user
        
        pipeline = IntegrationPipeline()
        analysis_result = await pipeline.analyze_user_location(user_id, location_name)
        
        # Format result for user
        formatted_result = format_analysis_for_user(analysis_result)
        
        # Update the analyzing message with results
        await analyzing_message.edit_text(formatted_result, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        await analyzing_message.edit_text(
            f"❌ **Analysis Failed**\n\n"
            f"Sorry, I couldn't analyze {location_name} right now.\n"
            f"Please try again later.\n\n"
            f"Error: {str(e)}"
        )


# Auto-complete suggestions for location names
@router.message(F.text, lambda message: len(message.text) > 1 and 
                message.from_user.id in user_sessions and 
                user_sessions[message.from_user.id].get('adding_location', {}).get('step') == 'name')
async def suggest_location_names(message: Message):
    """Provide name suggestions as user types"""
    partial_name = message.text.strip()
    suggestions = get_location_suggestions(partial_name)
    
    if suggestions and len(partial_name) > 2:
        suggestion_text = "💡 Suggestions:\n" + "\n".join([f"• {s}" for s in suggestions[:3]])
        # Note: This would be sent as a separate message, but might be too noisy
        # Better to implement as inline keyboard or only on request
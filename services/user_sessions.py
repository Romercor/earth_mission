user_sessions = {}

def init_mode_session(user_id, mode):
    user_sessions[user_id] = {
        "mode": mode
    }
def init_user_session(user_id, sensor):
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["sensor"] = sensor


def update_user_session(user_id, lat, lon, sensor, current_date):
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id].update({
        "lat": lat,
        "lon": lon,
        "sensor": sensor,
        "current_date": current_date
    })

def get_user_session(user_id):
    return user_sessions.get(user_id, None)

def check_and_update_session(user_id, lat, lon):
    session = get_user_session(user_id)
    if session:
        session["lat"] = lat
        session["lon"] = lon
        return session["sensor"]
    return None

def init_timetravelling_location(user_id, lat, lon):
    session = user_sessions.get(user_id)
    if not session:
        raise ValueError("Session not initialized for user_id {}".format(user_id))
    session.update({
        "lat": lat,
        "lon": lon
    })

from bottle import route, run, request, response
from datetime import datetime, timedelta
from typing import Dict, Tuple
import pytz
import json

from roomsApi import RoomsAPI, Availability

api = RoomsAPI()
cet = pytz.timezone('CET')

data_cache: Dict[Tuple[datetime, bool], Tuple[datetime, Availability]] = {}
def get_data_with_empty_rooms(date: datetime, include_teacher_only_rooms: bool) -> Availability:
    '''
    Get data from Sirius API, cached per day.
    This takes into account FIT rooms: only those will be returned.
    If FIT room has no schedule on that day, it'll be returned as well.
    Teacher-only rooms will be returned depending on the parameter provided.
    '''
    print("Include teacher rooms:", include_teacher_only_rooms)
    # Check cache (expire after 4 hours)
    if (cache_key := (datetime, bool)) in data_cache:
        entry = data_cache[cache_key]
        if entry[0] + timedelta(hours=4) < datetime.now(cet):
            del data_cache[cache_key]
        else:
            return entry[1]

    # Compute the data
    availability = api.get_room_availability(date)
    # Filter out only FIT rooms
    availability = {k:availability[k] for k in availability if
                    k in RoomsAPI.seminar_rooms or k in RoomsAPI.computer_rooms or (include_teacher_only_rooms and k in RoomsAPI.restricted_rooms)}
    # Add empty rooms
    for room in RoomsAPI.seminar_rooms + RoomsAPI.computer_rooms + (RoomsAPI.restricted_rooms if include_teacher_only_rooms else []):
        if room not in availability:
            availability[room] = [(date.replace(hour=0,minute=0,second=0)+RoomsAPI.opening_time,
                                   date.replace(hour=0,minute=0,second=0)+(RoomsAPI.closing_time_restricted if room in RoomsAPI.restricted_rooms else RoomsAPI.closing_time_normal))]

    # Save to cache
    data_cache[(date, include_teacher_only_rooms)] = (datetime.now(cet), availability)

    return availability

def get_room_type(room: str) -> str:
    if room in RoomsAPI.seminar_rooms:
        return "seminar"
    elif room in RoomsAPI.computer_rooms:
        return "computer"
    elif room in RoomsAPI.restricted_rooms:
        return "restricted"
    else:
        return "unknown"

@route('/api/freeRooms')
def index():
    date = cet.localize(datetime.fromisoformat(request.query.date)) if request.query.date else datetime.now(cet)
    include_teacher_rooms = bool(request.query.includeTeacherRooms)

    data = get_data_with_empty_rooms(date, include_teacher_rooms)
    response.content_type = 'application/json'
    # Can probably be removed
    # response.add_header("Access-Control-Allow-Origin", "*")
    return json.dumps([{'room':room, 'type':get_room_type(room), 'availability':[{'from': fromTime.isoformat(), 'to': toTime.isoformat()} for (fromTime, toTime) in data[room]]} for room in data])

run(host='localhost', port=8090)

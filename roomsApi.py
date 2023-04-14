from requests_oauth2client import OAuth2Client, BearerToken, ClientSecretBasic, ApiClient, OAuth2ClientCredentialsAuth
from datetime import datetime, timedelta
from typing import Dict, Tuple, List
import json

Availability = Dict[str, List[Tuple[datetime, datetime]]]

class RoomsAPI:
    __client_id = "INSERT CLIENT ID HERE"
    __client_secret = "INSERT CLIENT SECRET HERE"
    __token_url = "https://auth.fit.cvut.cz/oauth/token"
    __base_url = "https://sirius.fit.cvut.cz/api/v1"
    __client: OAuth2Client
    __api: ApiClient

    opening_time = timedelta(hours=6, minutes=0, seconds=0)
    closing_time_normal = timedelta(hours=20, minutes=0, seconds=0)
    closing_time_restricted = timedelta(hours=22, minutes=0, seconds=0)

    seminar_rooms = ['T9:301', 'T9:302', 'T9:343', 'T9:346', 'T9:347', 'TH:A-942', 'TH:A-1242', 'TH:A-1247',
                     'TH:A-1442']
    computer_rooms = ['T9:303', 'T9:345', 'T9:348', 'T9:349', 'T9:350', 'T9:351']
    restricted_rooms = ['TH:A-1142', 'T9:344', 'TH:A-1042', 'TH:A-1048', 'TK:PU1']

    def __init__(self):
        self.__client = OAuth2Client(
            token_endpoint=self.__token_url,
            auth=ClientSecretBasic(self.__client_id, self.__client_secret)
        )
        self.__api = ApiClient(
            self.__base_url, auth=OAuth2ClientCredentialsAuth(self.__client)
        )

    def get_raw_data_for_day(self, date: datetime) -> bytes:
        return self.__api.get("events?limit=1000&from={}&to={}".format(
            date.strftime("%Y-%m-%d"),
            (date + timedelta(days=1)).strftime("%Y-%m-%d")
        )).content

    def get_room_occupancy(self, date: datetime) -> List[Tuple[datetime, datetime, str]]:
        events_json = json.loads(self.get_raw_data_for_day(date))

        time_with_rooms:List[Tuple[datetime, datetime, str]] =\
            [(datetime.fromisoformat(event['starts_at']), datetime.fromisoformat(event['ends_at']), event['links'].get('room'))
                for event in events_json['events']
                if 'room' in event['links']]

        return time_with_rooms

    def get_room_availability(self, date:datetime) -> Availability:
        room_occupancy = self.get_room_occupancy(date)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Sort occupancy by end time
        room_occupancy.sort(key=lambda occ: occ[1])

        # Create a list of all rooms
        rooms = {occupancy[2] for occupancy in room_occupancy}
        # When will be room available next
        next_room_available_time = {room: date_start + RoomsAPI.opening_time for room in rooms}

        # Initialize an empty list for each room to store its available times
        availability: Dict[str, List[Tuple[datetime, datetime]]] = {room: [] for room in rooms}

        # Iterate over the list of tuples
        for occupancy in room_occupancy:
            start, end, room = occupancy

            next_time_available = next_room_available_time[room]

            # There might be a collision
            if next_time_available > start:
                next_room_available_time[room] = max(end, next_time_available)
                continue

            availability[room].append((next_time_available, start))
            next_room_available_time[room] = end

        # Add free time till the end of the day
        for room in availability:
            availability[room].append((next_room_available_time[room], date_start + (RoomsAPI.closing_time_restricted if room in RoomsAPI.restricted_rooms else RoomsAPI.closing_time_normal)))

        return availability

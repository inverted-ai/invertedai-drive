from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from enum import Enum

RecurrentStates = List[float]  # Recurrent Dim
TrafficLightId = str


class TrafficLightState(Enum):
    none = "none"
    green = "green"
    yellow = "yellow"
    red = "red"


@dataclass
class Location:
    name: str
    version: Optional[str]


@dataclass
class AgentAttributes:
    length: float
    width: float
    rear_axis_offset: float

    def tolist(self):
        return [self.length, self.width, self.rear_axis_offset]


@dataclass
class AgentState:
    x: float
    y: float
    orientation: float  # in radians with 0 pointing along x and pi/2 pointing along y
    speed: float  # in m/s

    def tolist(self):
        return [self.x, self.y, self.orientation, self.speed]


@dataclass
class TrafficLightStates:
    id: str
    states: List[TrafficLightState]


@dataclass
class InfractionIndicators:
    collisions: List[bool]
    offroad: List[bool]
    wrong_way: List[bool]


@dataclass
class DriveResponse:
    agent_states: List[AgentState]
    present_mask: List[float]  # A
    recurrent_states: List[RecurrentStates]  # Ax2x64
    bird_view: List[int]
    infractions: Optional[InfractionIndicators]


@dataclass
class InitializeResponse:
    agent_states: List[AgentState]
    agent_attributes: List[AgentAttributes]
    recurrent_states: List[RecurrentStates]


@dataclass
class LocationResponse:
    """
    rendered_map : List[int]
        Rendered image of the amp encoded in JPEG format
        (for decoding use JPEG decoder
        e.g., cv2.imdecode(response["rendered_map"], cv2.IMREAD_COLOR) ).

    lanelet_map_source : str
        Serialized XML file of the OSM map.
        save the map by write(response["lanelet_map_source"])
    static_actors : List[Dict]
        A list of static actors of the location, i.e, traffic signs and lights
            <track_id> : int
                    A unique ID of the actor, used to track and change state of the actor
            <agent_type> : str
                Type of the agent, either "traffic-light", or "stop-sign"
            <x> : float
                The x coordinate of the agent on the map
            <y> : float
                The y coordinate of the agent on the map
            <psi_rad> : float
                The orientation of the agent
            <length> : float
                The length of the actor
            <width> : float
                The width of the actor
    """

    rendered_map: List[int]
    lanelet_map_source: Optional[str]
    static_actors: Optional[List[Dict]]

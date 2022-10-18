"""
Python SDK for

Functions
---------
.. autosummary::
   :toctree: generated/
    available_locations
    drive
    location_info
    initialize
"""
from invertedai.error import TryAgain
from typing import List, Optional, Dict
import time
import invertedai as iai
from invertedai.models import (
    LocationResponse,
    InitializeResponse,
    DriveResponse,
    AgentState,
    AgentAttributes,
    InfractionIndicators,
    StaticMapActor,
    RecurrentStates,
    TrafficLightId,
    TrafficLightState,
)

TIMEOUT = 10


def location_info(
    location: str = "iai:ubc_roundabout", include_map_source: bool = False
) -> LocationResponse:
    """
    Providing map information, i.e., rendered bird's-eye view image, map in OSM format,
    list of static agents (traffic lights).

    Parameters
    ----------
    location : str
        Name of the location.

    include_map_source: bool
        Flag for requesting the map in Lanelet-OSM format.

    Returns
    -------
    Response : LocationResponse


    See Also
    --------
    invertedai.initialize

    Notes
    -----

    Examples
    --------
    >>> import invertedai as iai
    >>> response = iai.location_info(location="")
    >>> if response.osm_map is not None:
    >>>     file_path = f"{file_name}.osm"
    >>>     with open(file_path, "w") as f:
    >>>         f.write(response.osm_map[0])
    >>> if response.birdview_image is not None:
    >>>     file_path = f"{file_name}.jpg"
    >>>     rendered_map = np.array(response.birdview_image, dtype=np.uint8)
    >>>     image = cv2.imdecode(rendered_map, cv2.IMREAD_COLOR)
    >>>     cv2.imwrite(file_path, image)
    """

    start = time.time()
    timeout = TIMEOUT

    params = {"location": location, "include_map_source": include_map_source}
    while True:
        try:
            response = iai.session.request(model="location_info", params=params)
            if response["static_actors"] is not None:
                response["static_actors"] = [
                    StaticMapActor(**actor) for actor in response["static_actors"]
                ]
            return LocationResponse(**response)
        except TryAgain as e:
            if timeout is not None and time.time() > start + timeout:
                raise e
            iai.logger.info(iai.logger.logfmt("Waiting for model to warm up", error=e))


def initialize(
    location: str = "iai:ubc_roundabout",
    agent_attributes: Optional[List[AgentAttributes]] = None,
    states_history: Optional[List[List[AgentState]]] = None,
    traffic_light_state_history: Optional[
        List[Dict[TrafficLightId, TrafficLightState]]
    ] = None,
    agent_count: Optional[int] = None,
    random_seed: Optional[int] = None,
) -> InitializeResponse:
    """
    Parameters
    ----------
    location : str
        Name of the location.

    agent_attributes : Optional[List[AgentAttributes]]
        List of agent attributes. Each agent requires, length: [float]
        width: [float] and rear_axis_offset: [float] all in meters.

    states_history: Optional[[List[List[AgentState]]]]
       History of list of agent states. Each agent state must include x: [float],
       y: [float] corrdinate in meters orientation: [float] in radians with 0
       pointing along x and pi/2 pointing along y and speed: [float] in m/s.

    traffic_light_state_history: Optional[List[Dict[TrafficLightId, TrafficLightState]]]
       History of traffic light states.

    agent_count : Optional[int]
        Number of cars to spawn on the map.

    random_seed: Optional[int]
        This parameter controls the stochastic behavior of INITIALIZE. With the
        same seed and the same inputs, the outputs will be approximately the same
        with high accuracy.


    Returns
    -------
    Response : InitializeResponse

    See Also
    --------
    invertedai.drive

    Notes
    -----

    Examples
    --------
    >>> import invertedai as iai
    >>> response = iai.initialize(location="iai:ubc_roundabout", agent_count=10)
    """

    start = time.time()
    timeout = TIMEOUT

    while True:
        try:
            include_recurrent_states = (
                False if location.split(":")[0] == "huawei" else True
            )
            params = {
                "location": location,
                "num_agents_to_spawn": agent_count,
                "include_recurrent_states": include_recurrent_states,
            }
            model_inputs = dict(
                states_history=states_history
                if states_history is None
                else [state.tolist() for state in states_history],
                agent_attributes=agent_attributes
                if agent_attributes is None
                else [state.tolist() for state in agent_attributes],
                traffic_light_state_history=traffic_light_state_history,
                random_seed=random_seed,
            )
            initial_states = iai.session.request(
                model="initialize", params=params, data=model_inputs
            )
            agents_spawned = len(initial_states["agent_states"])
            if agents_spawned != agent_count:
                iai.logger.warning(
                    f"Unable to spawn a scenario for {agent_count} agents,  {agents_spawned} spawned instead."
                )
            response = InitializeResponse(
                agent_states=[
                    AgentState(*state) for state in initial_states["agent_states"]
                ],
                agent_attributes=[
                    AgentAttributes(*attr)
                    for attr in initial_states["agent_attributes"]
                ],
                recurrent_states=initial_states["recurrent_states"],
            )
            return response
        except TryAgain as e:
            if timeout is not None and time.time() > start + timeout:
                raise e
            iai.logger.info(iai.logger.logfmt("Waiting for model to warm up", error=e))


def drive(
    location: str = "iai:ubc_roundabout",
    agent_states: List[AgentState] = [],
    agent_attributes: List[AgentAttributes] = [],
    recurrent_states: RecurrentStates = [],
    traffic_lights_states: Optional[
        Dict[TrafficLightId, List[TrafficLightState]]
    ] = None,
    get_birdviews: bool = False,
    get_infractions: bool = False,
    random_seed: Optional[int] = None,
) -> DriveResponse:
    """
    Parameters
    ----------
    location : str
        Name of the location.

    agent_states : List[AgentState]
        List of agent states. The state must include x: [float], y: [float] corrdinate in meters
        orientation: [float] in radians with 0 pointing along x and pi/2 pointing along y and
        speed: [float] in m/s.

    agent_attributes : List[AgentAttributes]
        List of agent attributes. Each agent requires, length: [float]
        width: [float] and rear_axis_offset: [float] all in meters.

    recurrent_states : List[RecurrentStates]
        Internal simulation state obtained from previous calls to DRIVE or INITIZLIZE.

    get_birdviews: bool = False
        If True, a rendered bird's-eye view of the map with agents is returned.

    get_infractions: bool = False
        If True, 'collision', 'offroad', 'wrong_way' infractions of each agent
        are returned.

    traffic_light_state_history: Optional[Dict[TrafficLightId, List[TrafficLightState]]]
       Traffic light states.

    random_seed: Optional[int]
        This parameter controls the stochastic behavior of DRIVE. With the
        same seed and the same inputs, the outputs will be approximately the same
        with high accuracy.


    Returns
    -------
    Response : DriveResponse

    See Also
    --------
    invertedai.initialize

    Notes
    -----

    Examples
    --------
    >>> import invertedai as iai
    >>> response = iai.initialize(location="iai:ubc_roundabout", agent_count=10)
    >>> agent_attributes = response.agent_attributes
    >>> for _ in range(10):
    >>>     response = iai.drive(
                location="iai:ubc_roundabout",
                agent_attributes=agent_attributes,
                agent_states=response.agent_states,
                recurrent_states=response.recurrent_states,
                get_birdviews=True,
                get_infractions=True,)
    """

    def _tolist(input_data: List):
        if not isinstance(input_data, list):
            return input_data.tolist()
        else:
            return input_data

    recurrent_states = (
        _tolist(recurrent_states) if recurrent_states is not None else None
    )  # AxTx2x64
    model_inputs = dict(
        location=location,
        agent_states=[state.tolist() for state in agent_states],
        agent_attributes=[state.tolist() for state in agent_attributes],
        recurrent_states=recurrent_states,
        traffic_lights_states=traffic_lights_states,
        get_birdviews=get_birdviews,
        get_infractions=get_infractions,
        random_seed=random_seed,
    )

    start = time.time()
    timeout = TIMEOUT

    while True:
        try:
            response = iai.session.request(model="drive", data=model_inputs)

            response = DriveResponse(
                agent_states=[AgentState(*state) for state in response["agent_states"]],
                recurrent_states=response["recurrent_states"],
                bird_view=response["bird_view"],
                infractions=InfractionIndicators(
                    collisions=response["collision"],
                    offroad=response["offroad"],
                    wrong_way=response["wrong_way"],
                ),
                present_mask=response["present_mask"],
            )

            return response
        except Exception as e:
            iai.logger.warning("Retrying")
            if timeout is not None and time.time() > start + timeout:
                raise e

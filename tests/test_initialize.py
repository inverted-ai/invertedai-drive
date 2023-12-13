import sys
import pytest

sys.path.insert(0, "../../")
from invertedai.api.initialize import initialize, InitializeResponse
from invertedai.api.location import location_info
from invertedai.api.light import light
from invertedai.error import InvalidRequestError

positive_tests = [
    ("canada:ubc_roundabout",
     [[dict(center=dict(x=-31.1, y=-24.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-46.62, y=-25.02), orientation=0.04, speed=1.09)]],
     [dict(length=1.39, width=1.78, rear_axis_offset=0.0, agent_type='pedestrian'),
      dict(length=1.37, width=1.98, rear_axis_offset=0.0, agent_type='pedestrian'),
      dict(agent_type='pedestrian')],
     False, None),
    ("canada:ubc_roundabout",
     [[dict(center=dict(x=-31.1, y=-24.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-46.62, y=-25.02), orientation=0.04, speed=1.09)],
      [dict(center=dict(x=-31.1, y=-23.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-47.62, y=-23.02), orientation=0.04, speed=1.09)]],
     [dict(length=1.39, width=1.78, agent_type='pedestrian'),
      dict(length=1.37, width=1.98, rear_axis_offset=0.0, agent_type='pedestrian'),
      dict(agent_type='pedestrian'),
      dict(agent_type='car')],
     False, None),
    ("canada:ubc_roundabout",
     [[dict(center=dict(x=-31.1, y=-24.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-46.62, y=-25.02), orientation=0.04, speed=1.09)],
      [dict(center=dict(x=-31.1, y=-23.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-47.62, y=-23.02), orientation=0.04, speed=1.09)]],
     [dict(length=1.39, width=1.78, rear_axis_offset=0.0, agent_type='pedestrian'),
      dict(length=1.37, width=1.98, agent_type='pedestrian'),
      dict(agent_type='car'),
      dict()],
     False, None),
    ("carla:Town03",
     [[dict(center=dict(x=-31.1, y=-24.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-46.62, y=-25.02), orientation=0.04, speed=1.09)],
      [dict(center=dict(x=-31.1, y=-23.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-47.62, y=-23.02), orientation=0.04, speed=1.09)]],
     [dict(length=1.39, width=1.78, agent_type='pedestrian'),
      dict(length=1.37, width=1.98, rear_axis_offset=None, agent_type='pedestrian'),
      dict(agent_type='car'),
      dict()],
     False, 5),
    ("carla:Town03",
     None,
     [dict(agent_type='pedestrian'),
      dict(),
      dict(agent_type='car'),
      dict()],
     False, 5),
    ("carla:Town03",
     None,
     [dict(agent_type='pedestrian'),
      dict(),
      dict(agent_type='car'),
      dict()],
     False, None),
    ("canada:drake_street_and_pacific_blvd",
     None,
     [dict(agent_type='pedestrian'),
      dict(),
      dict(agent_type='car'),
      dict()],
     False, None),
    ("canada:drake_street_and_pacific_blvd",
     None,
     [dict(agent_type='pedestrian'),
      dict(),
      dict(agent_type='car'),
      dict()],
     False, 5),
    ("canada:drake_street_and_pacific_blvd",
     [[dict(center=dict(x=-31.1, y=-24.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-46.62, y=-25.02), orientation=0.04, speed=1.09)],
      [dict(center=dict(x=-31.1, y=-23.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-47.62, y=-23.02), orientation=0.04, speed=1.09)]],
     [dict(length=1.39, width=1.78, agent_type='pedestrian'),
      dict(length=1.37, width=1.98, agent_type='pedestrian'),
      dict(agent_type='pedestrian'),
      dict(agent_type='car')],
     False, 6),
    ("carla:Town04",
     None,
     None,
     False, 5),
]

negative_tests = [
    ("canada:ubc_roundabout",
     [[dict(center=dict(x=-31.1, y=-24.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-46.62, y=-25.02), orientation=0.04, speed=1.09)]],
     None,
     False, None),
    ("canada:ubc_roundabout",
     [[dict(center=dict(x=-31.1, y=-24.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-46.62, y=-25.02), orientation=0.04, speed=1.09)],
      [dict(center=dict(x=-31.1, y=-23.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-47.62, y=-23.02), orientation=0.04, speed=1.09)]],
     [dict(length=1.39, agent_type='pedestrian'),
      dict(width=1.98, rear_axis_offset=0.0, agent_type='pedestrian'),
      dict(agent_type='pedestrian'),
      dict(agent_type='car')],
     False, None),
    ("canada:ubc_roundabout",
     [[dict(center=dict(x=-31.1, y=-24.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-46.62, y=-25.02), orientation=0.04, speed=1.09)],
      [dict(center=dict(x=-31.1, y=-23.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-47.62, y=-23.02), orientation=0.04, speed=1.09)]],
     [dict(length=1.39, width=1.20, agent_type='pedestrian'),
      dict(length=1.37, width=1.98, agent_type='car'),
      dict(agent_type='pedestrian'),
      dict(agent_type='car')],
     False, None),
    ("canada:ubc_roundabout",
     [[dict(center=dict(x=-31.1, y=-24.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-46.62, y=-25.02), orientation=0.04, speed=1.09)],
      [dict(center=dict(x=-31.1, y=-23.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-47.62, y=-23.02), orientation=0.04, speed=1.09)]],
     [dict(length=1.39, width=1.26, rear_axis_offset=0.0, agent_type='pedestrian'),
      dict(length=1.37, width=1.98, rear_axis_offset=0.0, agent_type='pedestrian'),
      dict(width=1.15, agent_type='pedestrian'),
      dict(agent_type='car')],
     False, None),
    ("canada:ubc_roundabout",
     [[dict(center=dict(x=-31.1, y=-24.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-46.62, y=-25.02), orientation=0.04, speed=1.09)],
      [dict(center=dict(x=-31.1, y=-23.36), orientation=2.21, speed=0.11),
       dict(center=dict(x=-47.62, y=-23.02), orientation=0.04, speed=1.09)]],
     [dict(length=1.39, width=1.26, rear_axis_offset=0.0, agent_type='pedestrian'),
      dict(length=1.37, width=1.98, rear_axis_offset=0.0, agent_type='pedestrian'),
      dict(agent_type='pedestrian'),
      dict(agent_type='car')],
     False, 1),
]

def run_initialize(location, states_history, agent_attributes, get_infractions, agent_count):
    location_info_response = location_info(location=location, rendering_fov=200)
    if any(actor.agent_type == "traffic-light" for actor in location_info_response.static_actors):
        scene_has_lights = True
        light_response = light(location=location)
    else:
        light_response = None
        scene_has_lights = False
    response = initialize(
        location,
        agent_attributes=agent_attributes,
        states_history=states_history,
        traffic_light_state_history=[light_response.traffic_lights_states] if scene_has_lights else None,
        get_birdview=False,
        get_infractions=get_infractions,
        agent_count=agent_count,
    )
    assert isinstance(response,
                      InitializeResponse) and response.agent_attributes is not None and response.agent_states is not None


@pytest.mark.parametrize("location, states_history, agent_attributes, get_infractions, agent_count", negative_tests)
def test_negative(location, states_history, agent_attributes, get_infractions, agent_count):
    with pytest.raises(InvalidRequestError):
        run_initialize(location, states_history, agent_attributes, get_infractions, agent_count)


@pytest.mark.parametrize("location, states_history, agent_attributes, get_infractions, agent_count", positive_tests)
def test_positive(location, states_history, agent_attributes, get_infractions, agent_count):
    run_initialize(location, states_history, agent_attributes, get_infractions, agent_count)

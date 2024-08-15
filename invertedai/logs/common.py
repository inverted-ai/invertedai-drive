from pydantic import BaseModel
from typing import List, Optional, Dict, Tuple

import matplotlib.pyplot as plt
import json

from invertedai import location_info
from invertedai.utils import ScenePlotter
from invertedai.common import ( 
    AgentAttributes, 
    AgentProperties,
    AgentState, 
    LightRecurrentState,
    LightRecurrentStates,
    Point,
    RecurrentState,
    TrafficLightStatesDict 
)

class ScenarioLog(BaseModel):
    """
    A log containing simulation information for storage, replay, or an initial state from which a simulation 
    can be continued. Some data fields contain data for all historic time steps while others contain information
    for the most recent time step to be used to continue a simulation.
    """

    agent_states: List[List[AgentState]] #: Historic data for all agents states up until the most recent time step.
    agent_properties: List[AgentProperties] #: Agent properties data for all agents in this scenario/log.
    traffic_lights_states: Optional[List[TrafficLightStatesDict]] = None #: Historic data for all TrafficLightStatesDict up until the most recent time step.

    location: str #: Location name in IAI format.
    rendering_center: Optional[Tuple[float, float]] = None #: Please refer to the documentation of :func:`location_info` for information on this parameter.
    rendering_fov: Optional[int] = None #: Please refer to the documentation of :func:`location_info` for information on this parameter.

    lights_random_seed: Optional[int] = None #: Controls the stochastic aspects of the the traffic lights states.
    initialize_random_seed: Optional[int] = None #: Please refer to the documentation of :func:`initialize` for information on the random_seed parameter.
    drive_random_seed: Optional[int] = None #: Please refer to the documentation of :func:`drive` for information on the random_seed parameter.

    initialize_model_version: Optional[str] = "best" #: Please refer to the documentation of :func:`initialize` for information on the api_model_version parameter.
    drive_model_version: Optional[str] = "best" #: Please refer to the documentation of :func:`drive` for information on the api_model_version parameter.
    
    light_recurrent_states: Optional[LightRecurrentStates] = None #: As of the most recent time step. Please refer to the documentation of :func:`drive` for further information on this parameter.
    recurrent_states: Optional[List[RecurrentState]] = None #: As of the most recent time step. Please refer to the documentation of :func:`drive` for further information on this parameter.

    waypoints: Optional[Dict[str,List[Point]]] = None #: As of the most recent time step. A list of waypoints keyed to agent ID's not including waypoints already passed. These waypoints are not automatically populated into the agent properties.


class LogHandler():
    """
    A class for containing features relevant to both log reading and writing such as visualization.
    """

    def __init__(self):
        self.scenario_log = None
        self.simulation_length = None

    def visualize_up_to_timestep(
        self,
        timestep,
        gif_path,
        fov = 200,
        resolution = (2048,2048),
        dpi = 300,
        map_center = None,
        direction_vec = False,
        velocity_vec = False,
        plot_frame_number = True
    ):
        assert timestep >= 1 or timestep <= (self.simulation_length - 1), "Simulation period to plot is invalid."

        location_info_response = location_info(location=self.scenario_log.location)
        rendered_static_map = location_info_response.birdview_image.decode()
        map_center = tuple([location_info_response.map_center.x, location_info_response.map_center.y]) if map_center is None else map_center

        scene_plotter = ScenePlotter(
            map_image=rendered_static_map,
            fov=fov,
            xy_offset=map_center,
            static_actors=location_info_response.static_actors,
            resolution=resolution,
            dpi=dpi
        )
        scene_plotter.initialize_recording(
            agent_states=self.scenario_log.agent_states[0],
            agent_properties=self.scenario_log.agent_properties,
            traffic_light_states=None if self.scenario_log.traffic_lights_states is None else self.scenario_log.traffic_lights_states[0]
        )

        traffic_lights_states = [None]*(timestep-1) if self.scenario_log.traffic_lights_states is None else self.scenario_log.traffic_lights_states[1:timestep]
        for states, lights in zip(self.scenario_log.agent_states[1:timestep],traffic_lights_states):
            scene_plotter.record_step(states,lights)

        fig, ax = plt.subplots(constrained_layout=True, figsize=(50, 50))
        plt.axis('off')
        scene_plotter.animate_scene(
            output_name=gif_path,
            ax=ax,
            direction_vec=direction_vec,
            velocity_vec=velocity_vec,
            plot_frame_number=plot_frame_number,
        )

    def visualize(
        self,
        gif_path,
        fov = 200,
        resolution = (2048,2048),
        dpi = 300,
        map_center = None,
        direction_vec = False,
        velocity_vec = False,
        plot_frame_number = True
    ):
        self.visualize_up_to_timestep(
            timestep = self.simulation_length-1,
            gif_path = gif_path,
            fov = fov,
            resolution = resolution,
            dpi = dpi,
            map_center = map_center,
            direction_vec = direction_vec,
            velocity_vec = velocity_vec,
            plot_frame_number = plot_frame_number
        )

class LogWriter(LogHandler):
    """
    A class for conveniently writing a log to a JSON log format.
    """

    def __init__(self):
        super().__init__()

    def write_scenario_log_to_json(
        self,
        log_path,
        scenario_log = None
    ):  
        if scenario_log is None:
            scenario_log = self.scenario_log
        num_cars, num_pedestrians = 0, 0
        for prop in scenario_log.agent_properties:
            if prop.agent_type == "car":
                num_cars += 1
            elif prop.agent_type == "pedestrian":
                num_pedestrians += 1

        num_controls_light, num_controls_yield, num_controls_stop, num_controls_other = 0, 0, 0, 0
        static_actors_list = location_info(location=scenario_log.location).static_actors
        for actor in static_actors_list:
            if actor.agent_type == "traffic_light":
                num_controls_light += 1
            elif actor.agent_type == "yield_sign":
                num_controls_yield += 1
            elif actor.agent_type == "stop_sign":
                num_controls_stop += 1
            else:
                num_controls_other += 1

        predetermined_agents_dict = {}
        for i, prop in enumerate(scenario_log.agent_properties):
            states_dict = {}
            for t, states in enumerate(scenario_log.agent_states):
                states_dict[str(t)] = {
                    "center": {"x": states[i].center.x, "y": states[i].center.y},
                    "orientation": states[i].orientation,
                    "speed": states[i].speed
                }

            predetermined_agents_dict[str(i)] = {
                "entity_type": prop.agent_type,
                "static_attributes": {
                    "length": prop.length,
                    "width": prop.width,
                    "rear_axis_offset": prop.rear_axis_offset,
                },
                "states":states_dict
            }

        predetermined_controls_dict = {}
        if scenario_log.traffic_lights_states is not None:
            for actor in [actor for actor in static_actors_list if actor.agent_type == "traffic_light"]:
                actor_id = actor.actor_id
                states_dict = {}

                for t, tls in enumerate(scenario_log.traffic_lights_states):
                    states_dict[str(t)] = {
                        "center": {"x": actor.center.x, "y": actor.center.y},
                        "orientation": actor.orientation,
                        "speed": 0,
                        "control_state": tls[actor_id]
                    }

                predetermined_controls_dict[actor_id] = {
                    "entity_type": "traffic_light",
                    "static_attributes": {
                        "length": actor.length,
                        "width": actor.width,
                        "rear_axis_offset": 0,
                    },
                    "states":states_dict
                }

        individual_suggestions_dict = {}
        for i, prop in enumerate(scenario_log.agent_properties):
            wp = prop.waypoint
            if wp is not None:
                individual_suggestions_dict[str(i)] = {
                    "suggestion_strength": 0.8,
                    "states": {
                        "0": {
                            "center": {
                                "x": wp.center.x,
                                "y": wp.center.y
                            }
                        }
                    }
                }

        output_dict = {
            "location": {
                "identifier": scenario_log.location
            },
            "scenario_length": len(scenario_log.agent_states),
            "num_agents": {
                "car": num_cars,
                "pedestrian": num_pedestrians
            },
            "predetermined_agents": predetermined_agents_dict,
            "num_controls": {
                "traffic_light": num_controls_light,
                "yield_sign": num_controls_yield,
                "stop_sign": num_controls_stop,
                "other": num_controls_other,
            },
            "predetermined_controls": predetermined_controls_dict,
            "individual_suggestions": individual_suggestions_dict,
            "initialize_random_seed": scenario_log.initialize_random_seed,
            "lights_random_seed": scenario_log.lights_random_seed,
            "drive_random_seed": scenario_log.drive_random_seed,
            "drive_model_version": scenario_log.drive_model_version,
            "initialize_model_version": scenario_log.initialize_model_version,
            "birdview_options": {
                "rendering_center": [
                    scenario_log.rendering_center[0],
                    scenario_log.rendering_center[1]
                ],
                "renderingFOV": scenario_log.rendering_fov
            },
            "light_recurrent_states": [] if scenario_log.light_recurrent_states is None else [lrs.tolist() for lrs in scenario_log.light_recurrent_states],
            "rendering_centers": [
                scenario_log.rendering_center[0],
                scenario_log.rendering_center[1]
            ]
        }

        with open(log_path, "w") as outfile:
            json.dump(output_dict, outfile)

    @classmethod
    def write_json_from_scenario_log(
        cls, 
        log_path,
        scenario_log
    ):
        cls.write_scenario_log_to_json(cls,log_path,scenario_log)

    def initialize(
        self,
        location,
        location_info_response,
        init_response,
        lights_random_seed = None,
        initialize_random_seed = None,
        drive_random_seed = None
    ): 

        agent_properties = init_response.agent_properties
        if type(agent_properties[0]) == AgentAttributes:
            agent_properties = [convert_attributes_to_properties(attr) for attr in agent_properties]

        self.init_response = init_response
        self.location_info_response = location_info_response
        self.scenario_log = ScenarioLog(
            agent_states=[init_response.agent_states], 
            agent_properties=agent_properties, 
            traffic_lights_states=[init_response.traffic_lights_states] if init_response.traffic_lights_states is not None else None, 
            location=location,
            rendering_center=[
                self.location_info_response.map_center.x,
                self.location_info_response.map_center.y
            ],
            lights_random_seed=lights_random_seed,
            initialize_random_seed=initialize_random_seed,
            drive_random_seed=drive_random_seed,
            initialize_model_version=init_response.api_model_version,
            drive_model_version=None,
            light_recurrent_states=init_response.light_recurrent_states,
            recurrent_states=init_response.recurrent_states,
            waypoints=None
        )

        self.simulation_length = 1

    def drive(
        self,
        drive_response
    ): 
        self.scenario_log.agent_states.append(drive_response.agent_states)
        if drive_response.traffic_lights_states is not None:
            self.scenario_log.traffic_lights_states.append(drive_response.traffic_lights_states)
        
        self.scenario_log.drive_model_version = drive_response.api_model_version
        self.scenario_log.light_recurrent_states = drive_response.light_recurrent_states
        self.scenario_log.recurrent_states = drive_response.recurrent_states

        self.simulation_length += 1

class LogReader(LogHandler):
    """
    A class for conveniently reading in a log file then rendering it and/or plugging it into a simulation.
    """

    def __init__(self,log_path):
        super().__init__()
        self.current_timestep = 1

        with open(log_path) as f:
            LOG_DATA = json.load(f)

        location = LOG_DATA["location"]["identifier"]

        all_agent_states = []
        all_agent_properties = []
        for i in range(LOG_DATA["scenario_length"]):
            agent_states_ts = []
            for agent_num, agent in LOG_DATA["predetermined_agents"].items():
                if i == 0:
                    agent_attributes_json = agent["static_attributes"]
                    agent_properties = AgentProperties()
                    agent_properties.length = agent_attributes_json["length"]
                    agent_properties.width = agent_attributes_json["width"]
                    agent_properties.rear_axis_offset = agent_attributes_json["rear_axis_offset"]
                    agent_properties.agent_type = agent["entity_type"]
                    all_agent_properties.append(agent_properties)

                agent_state = agent["states"][str(i)]
                agent_states_ts.append(AgentState.fromlist([
                    agent_state["center"]["x"],
                    agent_state["center"]["y"],
                    agent_state["orientation"],
                    agent_state["speed"],
                ]))

            all_agent_states.append(agent_states_ts)

        all_traffic_light_states = []
        for i in range(LOG_DATA["scenario_length"]):
            traffic_light_states_ts = {}
            for actor_id, actor in LOG_DATA["predetermined_controls"].items():
                if actor["entity_type"] == "traffic_light":
                    actor_info_ts = actor["states"][str(i)]
                    traffic_light_states_ts[int(actor_id)] = actor_info_ts["control_state"]
            if traffic_light_states_ts:
                all_traffic_light_states.append(traffic_light_states_ts)

        if not all_traffic_light_states:
            all_traffic_light_states = None

        agent_waypoints = {}
        for agent_id, waypoints in LOG_DATA["individual_suggestions"].items():
            agent_waypoints[agent_id] = []
            for i, pt in waypoints["states"].items():
                data = pt["center"]
                agent_waypoints[agent_id].append(Point.fromlist([data["x"],data["y"]]))
        if not agent_waypoints:
            agent_waypoints = None

        self.scenario_log = ScenarioLog(
            agent_states=all_agent_states, 
            agent_properties=all_agent_properties, 
            traffic_lights_states=all_traffic_light_states, 
            location=location, 
            rendering_center=tuple([LOG_DATA["birdview_options"]["rendering_center"][0],LOG_DATA["birdview_options"]["rendering_center"][1]]),
            rendering_fov=LOG_DATA["birdview_options"]["renderingFOV"],
            lights_random_seed=LOG_DATA["lights_random_seed"],
            initialize_random_seed=LOG_DATA["initialize_random_seed"],
            drive_random_seed=LOG_DATA["drive_random_seed"],
            initialize_model_version=LOG_DATA["initialize_model_version"],
            drive_model_version=LOG_DATA["drive_model_version"],
            light_recurrent_states=None if LOG_DATA["light_recurrent_states"] is [] else [LightRecurrentState(state=state[0],time_remaining=state[1]) for state in LOG_DATA["light_recurrent_states"]],
            recurrent_states=None,
            waypoints=agent_waypoints
        )
        self._scenario_log_original = self.scenario_log

        self.simulation_length = len(all_agent_states)

        self.agent_states = None
        self.recurrent_states = None
        self.agent_properties = None
        self.traffic_lights_states = None
        self.light_recurrent_states = None

        self.init_api_model_version = None
        self.drive_api_model_version = None

        self.location_info_response = location_info(
            location=self.scenario_log.location,
            rendering_fov=self.scenario_log.rendering_fov,
            rendering_center=self.scenario_log.rendering_center,
        )

    def return_state_at_timestep(self,timestep):
        if timestep == 0:
            return self.initialize()
        elif timestep >= self.simulation_length:
            return False

        self.agent_states = self.scenario_log.agent_states[timestep]
        self.recurrent_states = None
        self.traffic_lights_states = None if self.scenario_log.traffic_lights_states is None else self.scenario_log.traffic_lights_states[timestep]
        self.light_recurrent_states = self.scenario_log.light_recurrent_states if timestep == (self.simulation_length - 1) else None
        self.drive_api_model_version = self.scenario_log.drive_model_version

        return True

    def return_last_state(self):
        return self.return_state_at_timestep(timestep=self.simulation_length-1)

    def reset_log(self):
        self.scenario_log = self._scenario_log_original
        self.current_timestep = 1

    def initialize(self):
        current_timestep = 0

        self.agent_states = self.scenario_log.agent_states[current_timestep]
        self.recurrent_states = None
        self.agent_properties = self.scenario_log.agent_properties
        self.traffic_lights_states = None if self.scenario_log.traffic_lights_states is None else self.scenario_log.traffic_lights_states[current_timestep]
        self.light_recurrent_states = self.scenario_log if current_timestep == (len(self.scenario_log.agent_states) - 1) else None
        self.init_api_model_version = self.scenario_log.initialize_model_version

        return True

    def drive(self):
        if self.current_timestep >= self.simulation_length:
            return False

        drive_response = self.return_state_at_timestep(timestep=self.current_timestep)
        self.current_timestep += 1

        return True



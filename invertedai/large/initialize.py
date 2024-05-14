import time
from pydantic import BaseModel, validate_call
from typing import List, Optional, Tuple
from itertools import product
from tqdm.contrib import tenumerate
import numpy as np
from random import choices

import invertedai as iai
from invertedai.large.common import Region
from invertedai.api.initialize import InitializeResponse
from invertedai.common import TrafficLightStatesDict, Point
from invertedai.utils import get_default_agent_attributes
from invertedai.error import InvertedAIError

AGENT_SCOPE_FOV_BUFFER = 20
ATTEMPT_PER_NUM_REGIONS = 15

@validate_call
def get_regions_default(
    location: str,
    total_num_agents: Optional[int] = None,
    area_shape: Optional[Tuple[float,float]] = None,
    map_center: Optional[Tuple[float,float]] = (0.0,0.0),
    random_seed: Optional[int] = None, 
    display_progress_bar: Optional[bool] = True
) -> List[Region]:
    """
    A utility function to create a set of Regions to be passed into :func:`large_initialize` in
    a single convenient entry point. 

    Arguments
    ----------
    location:
        Location name in IAI format.

    total_num_agents:
        The total number of agents to initialize across all regions.

    area_shape:
        Contains the [width, height] of the rectangular area to be broken into smaller regions. If
        this argument is not provided, a bounding box around the location polygon from :func:`location_info`
        will be used.

    map_center:
        The coordinates of the center of the rectangular area to be broken into smaller regions. If
        this argument is not provided, default coordinates of (0,0) are used.

    random_seed:
        Controls the stochastic aspects of assigning agents to regions for reproducibility. If this
        argument is not provided, a random seed is chosen.

    display_progress_bar:
        A flag to control whether a command line progress bar is displayed for convenience.
    
    """
    if area_shape is None:
        location_response = iai.location_info(
            location = location,
            rendering_center = map_center
        )
        polygon_x, polygon_y = [], []
        for pt in location_response.bounding_polygon:
            polygon_x.append(pt.x)
            polygon_y.append(pt.y)
        width = max(polygon_x) - min(polygon_x)
        height = max(polygon_y) - min(polygon_y)

        area_shape = (width,height)

    regions = iai.get_regions_in_grid(
        width = area_shape[0], 
        height = area_shape[1],
        map_center = map_center
    )

    if total_num_agents is None:
        total_num_agents = 10*len(regions)

    new_regions = iai.get_number_of_agents_per_region_by_drivable_area(
        location = location,
        regions = regions,
        total_num_agents = total_num_agents,
        random_seed = random_seed,
        display_progress_bar = display_progress_bar
    )

    return new_regions

@validate_call
def get_regions_in_grid(
    width: float,
    height: float,
    map_center: Optional[Tuple[float,float]] = (0.0,0.0), 
    stride: Optional[float] = 50.0
) -> List[Region]:
    """
    A utility function to help initialize an area larger than 100x100m. This function breaks up an 
    area into a grid of 100x100m regions, each of which can be initialized directly. Each of these
    regions will only have its shaped specified and no agent information. 

    Arguments
    ----------
    width:
        The horizontal size of the area which will be broken into smaller regions.

    height:
        The vertical size of the area which will be broken into smaller regions.

    map_center:
        The coordinates of the center of the rectangular area to be broken into smaller regions. If
        this argument is not provided, default coordinates of (0,0) are used.

    stride:
        How far apart the centers of the 100x100m regions should be. Some overlap is recommended for 
        best results and if no argument is provided, a value of 50 is used.
    
    """
    def check_valid_center(center):
        return (map_center[0] - width) < center[0] < (map_center[0] + width) and \
            (map_center[1] - height) < center[1] < (map_center[1] + height)

    def get_neighbors(center):
        return [
            (center[0] + (i * stride), center[1] + (j * stride))
            for i, j in list(product(*[(-1, 1),]* 2))
        ]

    queue, centers = [map_center], []

    while queue:
        center = queue.pop(0)
        neighbors = filter(check_valid_center, get_neighbors(center))
        queue.extend([
            neighbor
            for neighbor in neighbors
            if neighbor not in queue and neighbor not in centers
        ])
        if center not in centers and check_valid_center(center):
            centers.append(center)
    
    regions = [None for _ in range(len(centers))]
    for i, center in enumerate(centers):
        regions[i] = Region.create_square_region(center=Point.fromlist(list(center)))

    return regions

@validate_call
def get_number_of_agents_per_region_by_drivable_area(
    location: str,
    regions: List[Region],
    total_num_agents: Optional[int] = 10,
    random_seed: Optional[int] = None,
    display_progress_bar: Optional[bool] = True
) -> List[Region]:
    """
    This function takes in a list of regions, calculates the driveable area for each of them using 
    :func:`location_info`, then creates a new Region object with copied location and shape data and 
    inserts a number of default AgentAttributes objects into it porportional to its drivable surface 
    area relative to the other regions. Regions with no or a relatively small amount of drivable 
    surfaces will be assigned zero agents.

    Arguments
    ----------
    location:
        Location name in IAI format.

    regions:
        A list of empty Regions (i.e. no pre-existing agent information) for which the number of 
        agents to initialize is calculated. 

    total_num_agents:
        The total number of agents to initialize throughout all the regions.

    random_seed:
        Controls the stochastic aspects of assigning agents to regions for reproducibility. If this
        argument is not provided, a random seed is chosen.

    display_progress_bar:
        A flag to control whether a command line progress bar is displayed for convenience.
    
    """

    new_regions = [Region.copy(region) for region in regions]
    region_road_area = []
    total_drivable_area_ratio = 0

    if random_seed is not None:
        random.seed(random_seed)
    
    if display_progress_bar:
        iterable_regions = tenumerate(
            new_regions, 
            total=len(new_regions),
            desc=f"Calculating drivable surface areas"
        )
    else:
        iterable_regions = new_regions

    for i, region in iterable_regions:
        center_tuple = (region.center.x, region.center.y)
        birdview = iai.location_info(
            location=location,
            rendering_fov=int(region.size),
            rendering_center=center_tuple
        ).birdview_image.decode()

        birdview_arr_shape = birdview.shape
        total_num_pixels = birdview_arr_shape[0]*birdview_arr_shape[1]
        number_of_black_pix = np.sum(birdview.sum(axis=-1) == 0)

        drivable_area_ratio = (total_num_pixels-number_of_black_pix)/total_num_pixels 
        total_drivable_area_ratio += drivable_area_ratio
        region_road_area.append(drivable_area_ratio)

    # Select region in which to assign agents using drivable area as weight
    all_region_weights = [0]*len(new_regions)
    for i, drivable_ratio in enumerate(region_road_area):
        all_region_weights[i] = drivable_ratio/total_drivable_area_ratio
    random_indexes = choices(list(range(len(new_regions))), weights=all_region_weights, k=total_num_agents)

    for ind in random_indexes:
        new_regions[ind].agent_attributes.extend(get_default_agent_attributes({"car":1}))

    return new_regions

def _get_all_existing_agents_from_regions(regions,exclude_index=None):
    agent_states = []
    agent_attributes = []
    recurrent_states = []
    for ind, region in enumerate(regions):
        if not ind == exclude_index:
            region_agent_states = region.agent_states
            agent_states.extend(region_agent_states)
            agent_attributes.extend(region.agent_attributes[:len(region_agent_states)])
            recurrent_states.extend(region.recurrent_states)
    
    return agent_states, agent_attributes, recurrent_states

@validate_call
def large_initialize(
    location: str,
    regions: List[Region],
    traffic_light_state_history: Optional[List[TrafficLightStatesDict]] = None,
    get_infractions: bool = False,
    random_seed: Optional[int] = None,
    api_model_version: Optional[str] = None,
    display_progress_bar: bool = True,
    return_exact_agents: bool = False
) -> InitializeResponse:
    """
    A utility function to initialize an area larger than 100x100m. This function takes in a 
    list of Region objects on each of which :func:`initialize` is run and each initialize 
    response is combined into a single response which is returned. While looping over all
    regions, if there are agents in other regions that are near enough to the region of
    interest, they will be passed as conditional to :func:`initialize`. :func:`initialize` 
    will not be called if no agent_states or agent_attributes are specified in the region. 
    As well, predefined agents may be passed via the regions and will be considered as 
    conditional. A boolean flag can be used to control failure behaviour if :func:`initialize` 
    is unable to produce viable vehicle placements if the initialization should continue or 
    raise an exception.

    Arguments
    ----------
    location:
        Please refer to the documentation of :func:`initialize` for information on this parameter.

    regions:
        List of regions that contains information about the center, size, and agent_states and 
        agent_attributes formatted to align with :func:`initialize`. Please refer to the 
        documentation for :func:`initialize` for more details. The Region objects are not 
        modified, rather they are used 
    
    traffic_light_state_history:
        Please refer to the documentation of :func:`initialize` for information on this parameter.

    get_infractions:
        Please refer to the documentation of :func:`initialize` for information on this parameter.
    
    random_seed:
        Please refer to the documentation of :func:`initialize` for information on this parameter.

    api_model_version:
        Please refer to the documentation of :func:`initialize` for information on this parameter.

    display_progress_bar:
        If True, a bar is displayed showing the progress of all relevant processes.

    return_exact_agents:
        If set to True, this function will raise an InvertedAIError exception if it cannot fit 
        the requested number of agents in any single region. If set to False, a region that 
        fails to return the number of requested agents will be skipped and only its predefined 
        agents (if any) will be returned with respective RecurrentState's. 
    
    See Also
    --------
    :func:`initialize`
    """

    agent_states_sampled = []
    agent_attributes_sampled = []
    agent_rs_sampled = []
    light_recurrent_states = None

    def inside_fov(center: Point, agent_scope_fov: float, point: Point) -> bool:
        return ((center.x - (agent_scope_fov / 2) < point.x < center.x + (agent_scope_fov / 2)) and
                (center.y - (agent_scope_fov / 2) < point.y < center.y + (agent_scope_fov / 2)))
    
    if display_progress_bar:
        iterable_regions = tenumerate(
            regions, 
            total=len(regions),
            desc=f"Initializing regions"
        )
    else:
        iterable_regions = regions

    num_attempts = 1 + len(regions) // ATTEMPT_PER_NUM_REGIONS
    for i, region in iterable_regions:
        region_center = region.center
        region_size = region.size

        existing_agent_states, existing_agent_attributes, _ = _get_all_existing_agents_from_regions(regions,i)

        # Acquire agents that exist in other regions that must be passed as conditional to avoid collisions
        out_of_region_conditional_agents = list(filter(
            lambda x: inside_fov(center=region_center, agent_scope_fov=region_size+AGENT_SCOPE_FOV_BUFFER, point=x[0].center), 
            zip(existing_agent_states,existing_agent_attributes)
        ))

        out_of_region_conditional_agent_states = [x[0] for x in out_of_region_conditional_agents]
        out_of_region_conditional_agent_attributes = [x[1] for x in out_of_region_conditional_agents]

        region_conditional_agent_states = [] if region.agent_states is None else region.agent_states
        num_region_conditional_agents = len(region_conditional_agent_states)
        region_conditional_agent_attributes = [] if region.agent_attributes is None else region.agent_attributes[:num_region_conditional_agents]
        region_unsampled_agent_attributes = [] if region.agent_attributes is None else region.agent_attributes[num_region_conditional_agents:]
        all_agent_states = out_of_region_conditional_agent_states + region_conditional_agent_states
        all_agent_attributes = out_of_region_conditional_agent_attributes + region_conditional_agent_attributes + region_unsampled_agent_attributes

        num_out_of_region_conditional_agents = len(out_of_region_conditional_agent_states)

        regions[i].clear_agents()
        if len(all_agent_attributes) > 0:
            for attempt in range(num_attempts):
                try:
                    response = iai.initialize(
                        location=location,
                        states_history=None if len(all_agent_states) == 0 else [all_agent_states],
                        agent_attributes=all_agent_attributes,
                        get_infractions=get_infractions,
                        traffic_light_state_history=traffic_light_state_history,
                        location_of_interest=(region_center.x, region_center.y),
                        random_seed=random_seed
                    )

                except InvertedAIError as e:
                    # If error has occurred, display the warning and retry
                    iai.logger.debug(f"Region initialize attempt {attempt} error: {e}")
                    continue

                # Initialization of this region was successful, break the loop and proceed to the next region
                break
            
            else:
                exception_string = f"Unable to initialize region at {region.center} with size {region.size} after {num_attempts} attempts."
                if return_exact_agents: 
                    raise InvertedAIError(message=exception_string)
                else:
                    iai.logger.debug(exception_string)
                    if num_region_conditional_agents > 0:
                    # Get the recurrent states for all predefined agents within the region
                        response = iai.initialize(
                            location=location,
                            states_history=[all_agent_states],
                            agent_attributes=all_agent_attributes[:num_out_of_region_conditional_agents+num_region_conditional_agents],
                            get_infractions=get_infractions,
                            traffic_light_state_history=traffic_light_state_history,
                            location_of_interest=(region_center.x, region_center.y),
                            random_seed=random_seed
                        )

            # Filter out conditional agents from other regions
            for state, attrs, r_state in zip(
                response.agent_states[num_out_of_region_conditional_agents:],
                response.agent_attributes[num_out_of_region_conditional_agents:],
                response.recurrent_states[num_out_of_region_conditional_agents:]
            ):
                regions[i].insert_all_agent_details(state,attrs,r_state)

            if traffic_light_state_history is None and response.traffic_lights_states is not None:
                traffic_light_state_history = [response.traffic_lights_states]
                light_recurrent_states = response.light_recurrent_states
        else:
            #There are no agents to initialize within this region, proceed to the next region
            continue


    all_agent_states, all_agent_attributes, all_recurrent_states = _get_all_existing_agents_from_regions(regions)

    response.agent_states = all_agent_states
    response.agent_attributes = all_agent_attributes
    response.recurrent_states = all_recurrent_states 
    response.light_recurrent_states = light_recurrent_states
    
    return response
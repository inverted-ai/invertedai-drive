#include "initialize_request.h"
#include <iostream>
using json = nlohmann::json;

namespace invertedai {
InitializeRequest::InitializeRequest(const std::string &body_str) {
  this->body_json_ = json::parse(body_str);
  this->location_ = this->body_json_["location"];
  this->states_history_.clear();
  for (const auto &elements : this->body_json_["states_history"]) {
    std::vector<AgentState> agent_states;
    agent_states.clear();
    for (const auto &element : elements) {
      AgentState agent_state = {
        element[0], 
        element[1], 
        element[2], 
        element[3]
      };
      agent_states.push_back(agent_state);
    }
    this->states_history_.push_back(agent_states);
  }
  if (this->body_json_["agent_attributes"].is_null()) {
    this->agent_attributes_ = std::nullopt;
  } else {
    this->agent_attributes_ = std::vector<AgentAttributes>();
    for (const auto &element : this->body_json_["agent_attributes"]) {
      AgentAttributes agent_attribute(element);
      this->agent_attributes_.value().push_back(agent_attribute);
    }
  }
  if (this->body_json_["agent_properties"].is_null()) {
    this->agent_properties_ = std::nullopt;
  } else {
    this->agent_properties_ = std::vector<AgentProperties>();
    for (const auto &element : this->body_json_["agent_properties"]) {
      AgentProperties ap(element);
      this->agent_properties_.value().push_back(ap);
    }
  }
  this->traffic_light_state_history_.clear();
  std::vector<std::map<std::string, std::string>> traffic_light_states;
  for (const auto &element : this->body_json_["traffic_light_state_history"]) {
    std::map<std::string, std::string> light_states;
    for (const auto &pair : element.items()) {
      light_states[pair.key()] = pair.value();
    }
    traffic_light_states.push_back(light_states);
  }
  this->traffic_light_state_history_ = traffic_light_states;
  this->location_of_interest_ = this->body_json_["location_of_interest"].is_null()
    ? std::nullopt
    : std::optional<std::pair<double, double>>{this->body_json_["location_of_interest"]};
  this->get_birdview_ = this->body_json_["get_birdview"].is_boolean()
    ? this->body_json_["get_birdview"].get<bool>()
    : false;
  this->get_infractions_ = this->body_json_["get_infractions"].is_boolean()
    ? this->body_json_["get_infractions"].get<bool>()
    : false;
  this->num_agents_to_spawn_ = this->body_json_["num_agents_to_spawn"].is_number_integer()
    ? std::optional<int>{this->body_json_["num_agents_to_spawn"].get<int>()}
    : std::nullopt;
  this->random_seed_ = this->body_json_["random_seed"].is_number_integer()
    ? std::optional<int>{this->body_json_["random_seed"].get<int>()}
    : std::nullopt;
  this->model_version_ = this->body_json_["model_version"].is_null()
    ? std::nullopt
    : std::optional<std::string>{this->body_json_["model_version"]};
}

void InitializeRequest::refresh_body_json_() {
  this->body_json_["location"] = this->location_;
  this->body_json_["states_history"].clear();
  for (const std::vector<AgentState> &agent_states : this->states_history_) {
    json elements;
    elements.clear();
    for (const AgentState &agent_state : agent_states) {
      json element = {
        agent_state.x, 
        agent_state.y, 
        agent_state.orientation,
        agent_state.speed
      };
      elements.push_back(element);
    }
    this->body_json_["states_history"].push_back(elements);
  }
  if (this->agent_attributes_.has_value()) {
    this->body_json_["agent_attributes"].clear();
    for (const AgentAttributes &agent_attribute : this->agent_attributes_.value()) {
      json element = agent_attribute.toJson();
      this->body_json_["agent_attributes"].push_back(element);
    }
  } else {
    this->body_json_["agent_attributes"] = nullptr;
  }

  if (this->agent_properties_.has_value()) {
    this->body_json_["agent_properties"].clear();
    for (const AgentProperties &ap : this->agent_properties_.value()) {
      json element;
      if (ap.length.has_value()) {
        element["length"] = ap.length.value();
      }

      if (ap.width.has_value()) {
        element["width"] = ap.width.value();
      }

      if (ap.rear_axis_offset.has_value()) {
        element["rear_axis_offset"] = ap.rear_axis_offset.value();
      }

      if (ap.agent_type.has_value()) {
        element["agent_type"] = ap.agent_type.value();
      }

      if (ap.max_speed.has_value()) {
        element["max_speed"] = ap.max_speed.value();
      }
      if (ap.waypoint.has_value()) {
        element["waypoint"] = {ap.waypoint->x, ap.waypoint->y};
      }
      this->body_json_["agent_properties"].push_back(element);
    }
  } else {
    this->body_json_["agent_properties"] = nullptr;
  }
  this->body_json_["traffic_light_state_history"].clear();
  for (const std::map<std::string, std::string> &traffic_light_states : this->traffic_light_state_history_) {
    json elements;
    elements.clear();
    for (const auto &pair : traffic_light_states) {
      elements[pair.first] = pair.second;
    }
    this->body_json_["traffic_light_state_history"].push_back(elements);
  }
  if (this->location_of_interest_.has_value()) {
    this->body_json_["location_of_interest"] =
      this->location_of_interest_.value();
  } else {
    this->body_json_["location_of_interest"] = nullptr;
  }
  this->body_json_["get_birdview"] = this->get_birdview_;
  this->body_json_["get_infractions"] = this->get_infractions_;
  if (this->num_agents_to_spawn_.has_value()) {
    this->body_json_["num_agents_to_spawn"] = this->num_agents_to_spawn_.value();
  } else {
    this->body_json_["num_agents_to_spawn"] = nullptr;
  }
  if (this->random_seed_.has_value()) {
    this->body_json_["random_seed"] = this->random_seed_.value();
  } else {
    this->body_json_["random_seed"] = nullptr;
  }
  if (this->model_version_.has_value()) {
    this->body_json_["model_version"] = this->model_version_.value();
  } else {
    this->body_json_["model_version"] = nullptr;
  }
};

std::string InitializeRequest::body_str() {
  this->refresh_body_json_();
  return this->body_json_.dump();
}

std::string InitializeRequest::location() const { return this->location_; }

std::optional<int> InitializeRequest::num_agents_to_spawn() const {
  return this->num_agents_to_spawn_;
}

std::vector<std::vector<AgentState>> InitializeRequest::states_history() const {
  return this->states_history_;
}

std::optional<std::vector<AgentAttributes>> InitializeRequest::agent_attributes() const {
  return this->agent_attributes_;
}

std::optional<std::vector<AgentProperties>> InitializeRequest::agent_properties() const {
  return this->agent_properties_;
}

std::vector<std::map<std::string, std::string>> InitializeRequest::traffic_light_state_history() const {
  return this->traffic_light_state_history_;
}

std::optional<std::pair<double, double>> InitializeRequest::location_of_interest() const {
  return this->location_of_interest_;
}

bool InitializeRequest::get_birdview() const { 
  return this->get_birdview_; 
}

bool InitializeRequest::get_infractions() const {
  return this->get_infractions_;
}

std::optional<int> InitializeRequest::random_seed() const {
  return this->random_seed_;
}

std::optional<std::string> InitializeRequest::model_version() const {
  return this->model_version_;
}

void InitializeRequest::set_location(const std::string &location) {
  this->location_ = location;
}

void InitializeRequest::set_num_agents_to_spawn(std::optional<int> num_agents_to_spawn) {
  this->num_agents_to_spawn_ = num_agents_to_spawn;
}

void InitializeRequest::set_states_history(const std::vector<std::vector<AgentState>> &states_history) {
  this->states_history_ = states_history;
}

void InitializeRequest::set_agent_attributes(const std::vector<AgentAttributes> &agent_attributes) {
  this->agent_attributes_ = agent_attributes;
}

void InitializeRequest::set_agent_properties(const std::vector<AgentProperties> &agent_properties) {
  this->agent_properties_ = agent_properties;
}

void InitializeRequest::set_traffic_light_state_history(const std::vector<std::map<std::string, std::string>>&traffic_light_state_history) {
  this->traffic_light_state_history_ = traffic_light_state_history;
}

void InitializeRequest::set_location_of_interest(const std::optional<std::pair<double, double>> &location_of_interest) {
  this->location_of_interest_ = location_of_interest;
}

void InitializeRequest::set_get_birdview(bool get_birdview) {
  this->get_birdview_ = get_birdview;
}

void InitializeRequest::set_get_infractions(bool get_infractions) {
  this->get_infractions_ = get_infractions;
}

void InitializeRequest::set_random_seed(std::optional<int> random_seed) {
  this->random_seed_ = random_seed;
}

void InitializeRequest::set_model_version(std::optional<std::string> model_version) {
  this->model_version_ = model_version;
}

} // namespace invertedai

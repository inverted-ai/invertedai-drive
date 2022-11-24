#include "initialize_response.h"

using json = nlohmann::json;

InitializeResponse::InitializeResponse(const std::string &body_str) {
  this->body_json_ = json::parse(body_str);

  this->agent_states_.clear();
  for (const auto &element : body_json_["agent_states"]) {
    AgentState agent_state = {element[0], element[1], element[2], element[3]};
    this->agent_states_.push_back(agent_state);
  }
  this->agent_attributes_.clear();
  for (const auto &element : body_json_["agent_attributes"]) {
    AgentAttributes agent_attribute = {element[0], element[1], element[2]};
    this->agent_attributes_.push_back(agent_attribute);
  }
  this->recurrent_states_.clear();
  for (const auto &element : body_json_["recurrent_states"]) {
    std::vector<double> recurrent_state;
    recurrent_state.clear();
    for (const auto &inside_element : element) {
      recurrent_state.push_back(inside_element);
    }
    this->recurrent_states_.push_back(recurrent_state);
  }
  this->birdview_.clear();
  for (auto &element : body_json_["birdview"]) {
    this->birdview_.push_back(element);
  }
  this->infraction_indicators_.clear();
  for (auto &element : body_json_["infraction_indicators"]) {
    InfractionIndicator infraction_indicator = {element[0], element[1],
                                                element[2]};
    this->infraction_indicators_.push_back(infraction_indicator);
  }
}

void InitializeResponse::refresh_body_json_() {
  this->body_json_["agent_states"].clear();
  for (const AgentState &agent_state : this->agent_states_) {
    json element = {agent_state.x, agent_state.y, agent_state.orientation,
                    agent_state.speed};
    this->body_json_["agent_states"].push_back(element);
  }
  this->body_json_["agent_attributes"].clear();
  for (const AgentAttributes &agent_attribute : this->agent_attributes_) {
    json element = {agent_attribute.length, agent_attribute.width,
                    agent_attribute.rear_axis_offset};
    this->body_json_["agent_attributes"].push_back(element);
  }
  this->body_json_["recurrent_states"].clear();
  for (const std::vector<double> &recurrent_state : this->recurrent_states_) {
    json elements;
    elements.clear();
    for (double element : recurrent_state) {
      elements.push_back(element);
    }
    this->body_json_["recurrent_states"].push_back(elements);
  }
  this->body_json_["birdview"].clear();
  for (unsigned char element : this->birdview_) {
    this->body_json_["birdview"].push_back(element);
  }
  this->body_json_["infraction_indicators"].clear();
  for (InfractionIndicator infraction_indicator :
       this->infraction_indicators_) {
    json element = {infraction_indicator.collisions,
                    infraction_indicator.offroad,
                    infraction_indicator.wrong_way};
    this->body_json_["infraction_indicators"].push_back(element);
  }
}

std::string InitializeResponse::body_str() {
  this->refresh_body_json_();
  return this->body_json_.dump();
}

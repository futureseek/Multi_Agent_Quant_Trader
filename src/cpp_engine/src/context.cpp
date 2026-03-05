#include "context.h"
#include "engine.h"
#include <stdexcept>

namespace cpp_engine {

Context::Context(SimpleCppEngine* engine) : engine_(engine) {}

std::vector<double> Context::get_series(const std::string& symbol, const std::string& field, int count) {
    if (!engine_) {
        throw std::runtime_error("Context: engine pointer is null");
    }
    // symbol参数暂时忽略（单股票回测）
    return engine_->get_series(field, count);
}

double Context::get_bar(const std::string& symbol, const std::string& field, int offset) {
    if (!engine_) {
        throw std::runtime_error("Context: engine pointer is null");
    }
    // symbol参数暂时忽略（单股票回测）
    return engine_->get_bar(field, offset);
}

std::unordered_map<std::string, double> Context::get_current_bar() {
    if (!engine_) {
        throw std::runtime_error("Context: engine pointer is null");
    }
    return engine_->get_current_bar_data();
}

std::string Context::get_current_date() {
    if (!engine_) {
        throw std::runtime_error("Context: engine pointer is null");
    }
    return engine_->get_current_date();
}

void Context::buy(const std::string& symbol, int quantity, double price) {
    if (!engine_) {
        throw std::runtime_error("Context: engine pointer is null");
    }
    engine_->submit_buy_order(symbol, quantity, price);
}

void Context::sell(const std::string& symbol, int quantity, double price) {
    if (!engine_) {
        throw std::runtime_error("Context: engine pointer is null");
    }
    engine_->submit_sell_order(symbol, quantity, price);
}

double Context::get_cash() {
    if (!engine_) {
        throw std::runtime_error("Context: engine pointer is null");
    }
    return engine_->get_cash();
}

int Context::get_position(const std::string& symbol) {
    if (!engine_) {
        throw std::runtime_error("Context: engine pointer is null");
    }
    return engine_->get_position(symbol);
}

} // namespace cpp_engine

#include "environment.hpp"

#include <utility>

Environment::Environment(std::shared_ptr<Environment> parent)
    : parent_(std::move(parent)) {}

void Environment::define(const std::string& name, Value value) {
    values_.insert_or_assign(name, std::move(value));
}

void Environment::assign(const std::string& name, Value value) {
    Environment* current = this;

    while (current != nullptr) {
        auto existing = current->values_.find(name);

        if (existing != current->values_.end()) {
            existing->second = std::move(value);
            return;
        }

        current = current->parent_.get();
    }

    define(name, std::move(value));
}

const Value* Environment::find(const std::string& name) const {
    const Environment* current = this;

    while (current != nullptr) {
        auto existing = current->values_.find(name);

        if (existing != current->values_.end()) {
            return &existing->second;
        }

        current = current->parent_.get();
    }

    return nullptr;
}

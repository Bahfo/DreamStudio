#pragma once

#include <memory>
#include <string>
#include <unordered_map>

#include "value.hpp"

/**
 * A lexical scope for DreamScript variables.
 *
 * Each block creates a child environment. Reading walks up the chain to the
 * global environment; assigning updates the nearest existing binding, or
 * creates a binding in the current scope when no binding exists yet.
 */
class Environment {
public:
    explicit Environment(std::shared_ptr<Environment> parent = nullptr);

    void define(const std::string& name, Value value);
    void assign(const std::string& name, Value value);

    const Value* find(const std::string& name) const;

private:
    std::shared_ptr<Environment> parent_;
    std::unordered_map<std::string, Value> values_;
};

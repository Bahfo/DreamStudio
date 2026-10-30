#include "value.hpp"

Value::Value() : data_(std::monostate{}) {}

Value::Value(int value) : data_(static_cast<double>(value)) {}

Value::Value(double value) : data_(value) {}

Value::Value(std::string value) : data_(std::move(value)) {}

Value::Value(bool value) : data_(value) {}

Value::Value(const char* value) : data_(std::string(value)) {}

Value::Type Value::type() const {
    if (std::holds_alternative<std::monostate>(data_)) return Type::Null;
    if (std::holds_alternative<double>(data_)) return Type::Number;
    if (std::holds_alternative<std::string>(data_)) return Type::String;
    return Type::Boolean;
}

bool Value::isNull() const {
    return type() == Type::Null;
}

bool Value::isNumber() const {
    return type() == Type::Number;
}

bool Value::isString() const {
    return type() == Type::String;
}

bool Value::isBoolean() const {
    return type() == Type::Boolean;
}

double Value::asNumber() const {
    if (!isNumber()) {
        throw std::runtime_error(
            "Expected a number, but got " + typeName() + ".");
    }

    return std::get<double>(data_);
}

const std::string& Value::asString() const {
    if (!isString()) {
        throw std::runtime_error(
            "Expected a string, but got " + typeName() + ".");
    }

    return std::get<std::string>(data_);
}

bool Value::asBoolean() const {
    switch (type()) {
        case Type::Null:
            return false;
        case Type::Boolean:
            return std::get<bool>(data_);
        case Type::Number:
            return std::get<double>(data_) != 0.0;
        case Type::String:
            return !std::get<std::string>(data_).empty();
    }

    return false;
}

std::string Value::toString() const {
    switch (type()) {
        case Type::Null:
            return "";
        case Type::Boolean:
            return std::get<bool>(data_) ? "true" : "false";
        case Type::Number: {
            std::ostringstream output;
            output << std::setprecision(15) << std::get<double>(data_);
            return output.str();
        }
        case Type::String:
            return std::get<std::string>(data_);
    }

    return "";
}

std::string Value::typeName() const {
    switch (type()) {
        case Type::Null:
            return "null";
        case Type::Number:
            return "number";
        case Type::String:
            return "string";
        case Type::Boolean:
            return "boolean";
    }

    return "unknown";
}

bool Value::equals(const Value& other) const {
    return data_ == other.data_;
}
#pragma once

#include <string>
#include <variant>
#include <iomanip>
#include <sstream>
#include <utility>
#include <stdexcept>


class Value {
public:
    enum class Type {
        Null,
        Number,
        String,
        Boolean,
    };

    Value();
    explicit Value(int value);
    explicit Value(double value);
    explicit Value(std::string value);
    explicit Value(bool value);

    Value(const char* value);

    Type type() const;

    bool isNull() const;
    bool isNumber() const;
    bool isString() const;
    bool isBoolean() const;

    double asNumber() const;
    const std::string& asString() const;
    bool asBoolean() const;

    std::string toString() const;
    std::string typeName() const;

    bool equals(const Value& other) const;

private:
    std::variant<std::monostate, double, std::string, bool> data_;
};
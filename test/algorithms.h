#pragma once

/// Returns its argument unchanged.
/// @tparam T the value type
/// @param value the value to pass through
/// @return the same value
template <typename T>
T identity(T value)
{
    return value;
}
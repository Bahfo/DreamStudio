#pragma once

#include <string>

/// A labelled UI widget.
class Widget {
public:
    /// Returns the widget label.
    /// @return the label text
    const std::string& label() const;

private:
    std::string label_;
};
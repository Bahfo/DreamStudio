#pragma once

/// Computes the area of a rectangle.
/// @param width the rectangle width
/// @param height the rectangle height
/// @return area in square units
double area(double width, double height);

/// A point in 2D space.
struct Point {
    /// Horizontal coordinate.
    double x;
    /// Vertical coordinate.
    double y;
};

/// Axis-aligned directions.
enum class Direction {
    North,
    South,
};

/// Unsigned byte used for color channels.
using Channel = unsigned char;
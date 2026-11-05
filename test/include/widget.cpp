#include "algorithms.h"
#include "config.h"
#include "geometry.h"
#include "widget.h"

#include <iostream>

namespace {

/// Returns the answer to everything.
int answer()
{
    return SQUARE(6) + 6;
}

}  // namespace

int main()
{
    Point p{3.0, 4.0};
    const double result = area(p.x, p.y);

    Widget widget;
    const int retries = MAX_RETRIES;
    const int value = identity(retries);

    std::cout << widget.label() << result << answer() << value << '\n';
    return 0;
}
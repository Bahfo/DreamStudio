// COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
// Part of the Debugger Utility for DreamStudio IDE.
//
// Processor-Related script for grabbing processor info.
//
// THIS PART OF THE CODE IS PROTECTED UNDER GPLv3. READ LICENSE FOR MORE INFO.

// Written by Bahaa Nofal

#pragma once

#include <cstdint>
#include <string>
#include <vector>

struct ProcessorInfo {
    std::string vendor;
    std::string brand;
    uint32_t    physical_cores;
    uint32_t    logical_cores;
    uint32_t    family;
    uint32_t    model;
    uint32_t    stepping;
    double      current_freq_mhz;
    double      max_freq_mhz;
};

class Processor {
public:
    Processor();
    ~Processor();

    ProcessorInfo info() const;

private:
    ProcessorInfo m_info;

#ifdef __linux__
    void read_from_cpuinfo();
#endif
};

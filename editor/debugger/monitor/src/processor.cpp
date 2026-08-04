// COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
// Part of the Debugger Utility for DreamStudio IDE.
//
// Main implementation for processor utility (expands processor.h)
//
// THIS PART OF THE CODE IS PROTECTED UNDER GPLv3. READ LICENSE FOR MORE INFO.

// Written by Bahaa Nofal

#include "processor.h"

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <intrin.h>
#endif

#ifdef __linux__
#include <fstream>
#include <sstream>
#include <unistd.h>
#endif

#include <cstring>


Processor::Processor() {
#ifdef _WIN32
    int cpu_info[4] = {0};

    __cpex(cpu_info, 0);
    int vendor_ids[4];
    memcpy(vendor_ids, cpu_info, sizeof(vendor_ids));
    char vendor_str[13] = {0};
    memcpy(vendor_str, vendor_ids, 12);
    m_info.vendor = vendor_str;

    __cpex(cpu_info, 0x80000002);
    char brand1[17] = {0};
    memcpy(brand1, cpu_info, 16);

    __cpex(cpu_info, 0x80000003);
    char brand2[17] = {0};
    memcpy(brand2, cpu_info, 16);

    __cpex(cpu_info, 0x80000004);
    char brand3[17] = {0};
    memcpy(brand3, cpu_info, 16);

    m_info.brand = std::string(brand1) + brand2 + brand3;

    __cpex(cpu_info, 1);
    m_info.family = (cpu_info[0] >> 8) & 0xF;
    m_info.model = (cpu_info[0] >> 4) & 0xF;
    m_info.stepping = cpu_info[0] & 0xF;

    // Extended family/model for modern CPUs
    uint32_t ext_family = (cpu_info[0] >> 20) & 0xFF;
    uint32_t ext_model = (cpu_info[0] >> 16) & 0xF;
    if (m_info.family == 0xF) m_info.family += ext_family;
    if (m_info.family == 0x6 || m_info.family == 0xF) m_info.model |= (ext_model << 4);

    SYSTEM_INFO sys_info;
    GetSystemInfo(&sys_info);
    m_info.logical_cores = sys_info.dwNumberOfProcessors;

    // Count physical cores via wmic (fallback: logical = physical)
    m_info.physical_cores = m_info.logical_cores;

    // Frequency from registry
    HKEY hkey;
    DWORD freq = 0, size = sizeof(freq);
    if (RegOpenKeyExA(HKEY_LOCAL_MACHINE,
            "HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0", 0,
            KEY_READ, &hkey) == ERROR_SUCCESS) {
        RegQueryValueExA(hkey, "~MHz", nullptr, nullptr, reinterpret_cast<LPBYTE>(&freq), &size);
        RegCloseKey(hkey);
    }
    m_info.current_freq_mhz = static_cast<double>(freq);
    m_info.max_freq_mhz = m_info.current_freq_mhz;
#endif

#ifdef __linux__
    read_from_cpuinfo();
#endif
}

Processor::~Processor() = default;

ProcessorInfo Processor::info() const {
    return m_info;
}


#ifdef __linux__

static std::string trim(const std::string& s) {
    size_t start = s.find_first_not_of(" \t\r\n");
    size_t end = s.find_last_not_of(" \t\r\n");
    if (start == std::string::npos) return "";
    return s.substr(start, end - start + 1);
}

void Processor::read_from_cpuinfo() {
    std::ifstream f("/proc/cpuinfo");
    if (!f.is_open()) return;

    std::string line;
    bool first_core = true;

    while (std::getline(f, line)) {
        size_t colon = line.find(':');
        if (colon == std::string::npos) {
            if (!line.empty() && first_core) first_core = false;
            continue;
        }

        std::string key = trim(line.substr(0, colon));
        std::string val = trim(line.substr(colon + 1));

        if (key == "vendor_id" && m_info.vendor.empty()) {
            m_info.vendor = val;
        }
        if (key == "model name") {
            if (m_info.brand.empty()) m_info.brand = val;
        }
        if (key == "cpu family") {
            try { m_info.family = static_cast<uint32_t>(std::stoul(val)); } catch (...) {}
        }
        if (key == "model") {
            try { m_info.model = static_cast<uint32_t>(std::stoul(val)); } catch (...) {}
        }
        if (key == "stepping") {
            try { m_info.stepping = static_cast<uint32_t>(std::stoul(val)); } catch (...) {}
        }
        if (key == "cpu MHz") {
            try { m_info.current_freq_mhz = std::stod(val); } catch (...) {}
        }
    }

    m_info.logical_cores = static_cast<uint32_t>(sysconf(_SC_NPROCESSORS_ONLN));
    m_info.physical_cores = m_info.logical_cores;
    m_info.max_freq_mhz = m_info.current_freq_mhz;
}

#endif

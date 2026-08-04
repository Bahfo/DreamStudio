// COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
// Part of the Debugger Utility for DreamStudio IDE.
//
// Implementation code for the system manager (expands system.h)
//
// THIS PART OF THE CODE IS PROTECTED UNDER GPLv3. READ LICENSE FOR MORE INFO.

// Written by Bahaa Nofal

#include "system.h"

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#endif

#ifdef __linux__
#include <fstream>
#include <sstream>
#include <unistd.h>
#endif


SystemMonitor::SystemMonitor()
#ifdef _WIN32
    : m_token(nullptr)
#endif
{
#ifdef _WIN32
    OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &m_token);
#endif
}

SystemMonitor::~SystemMonitor() {
#ifdef _WIN32
    if (m_token) {
        CloseHandle(m_token);
        m_token = nullptr;
    }
#endif
}

SystemInfo SystemMonitor::snapshot() {
    SystemInfo info{};

#ifdef _WIN32
    // --- Memory ---
    MEMORYSTATUSEX mem_status{};
    mem_status.dwLength = sizeof(mem_status);
    if (GlobalMemoryStatusEx(&mem_status)) {
        info.total_memory_bytes = mem_status.ullTotalPhys;
        info.available_memory_bytes = mem_status.ullAvailPhys;
    }

    // --- Uptime ---
    info.uptime_seconds = static_cast<uint64_t>(GetTickCount64() / 1000ULL);

    // --- OS name ---
    info.os_name = "Windows";
#endif

#ifdef __linux__
    {
        std::ifstream ifs("/proc/meminfo");
        if (ifs.is_open()) {
            std::string line, label;
            uint64_t value = 0;

            while (std::getline(ifs, line)) {
                std::istringstream ss(line);
                ss >> label >> value;

                if (label == "MemTotal:")
                    info.total_memory_bytes = value * 1024;
                else if (label == "MemAvailable:")
                    info.available_memory_bytes = value * 1024;

                if (!info.total_memory_bytes && !info.available_memory_bytes)
                    continue;
                if (info.total_memory_bytes && info.available_memory_bytes)
                    break;
            }
        }
    }

    {
        std::ifstream ifs("/proc/uptime");
        if (ifs.is_open()) {
            double seconds = 0.0;
            ifs >> seconds;
            info.uptime_seconds = static_cast<uint64_t>(seconds);
        }
    }

    info.os_name = "Linux";
#endif

    return info;
}

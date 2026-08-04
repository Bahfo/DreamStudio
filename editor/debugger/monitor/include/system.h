// COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
// Part of the Debugger Utility for DreamStudio IDE.
//
// System info detector tool and manager for system monitor.
//
// THIS PART OF THE CODE IS PROTECTED UNDER GPLv3. READ LICENSE FOR MORE INFO.

// Written by Bahaa Nofal

#pragma once

#include <cstdint>
#include <string>

struct SystemInfo {
    uint64_t total_memory_bytes;
    uint64_t available_memory_bytes;
    uint64_t uptime_seconds;
    std::string os_name;
};

class SystemMonitor {
public:
    SystemMonitor();
    ~SystemMonitor();

    SystemInfo snapshot();

private:
#ifdef _WIN32
    void* m_token;
#endif
};

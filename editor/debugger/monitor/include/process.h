// COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
// Part of the Debugger Utility for DreamStudio IDE.
//
// Process manager tool. Grabs a process by its PID and monitors
// memory usage, CPU usage, disk usage, and current state.
//
// THIS PART OF THE CODE IS PROTECTED UNDER GPLv3. READ LICENSE FOR MORE INFO.

// Written by Bahaa Nofal

#pragma once

#include <cstdint>
#include <string>

struct ProcessInfo {
    uint64_t pid;
    double   cpu_usage;
    uint64_t memory_usage_bytes;
    uint64_t disk_read_bytes;
    uint64_t disk_write_bytes;
    std::string state;
    std::string name;
};

class ProcessMonitor {
public:
    explicit ProcessMonitor(uint64_t pid);
    ~ProcessMonitor();

    bool        is_valid() const;
    ProcessInfo snapshot();

private:
    uint64_t    m_pid;
    bool        m_valid;

#ifdef _WIN32
    void* m_process_handle;
    uint64_t m_last_cpu_time;
    uint64_t m_last_sys_time;
    uint64_t m_last_timestamp;
#endif

#ifdef __linux__
    double m_prev_cpu_total;
    double m_prev_cpu_process;
#endif
};

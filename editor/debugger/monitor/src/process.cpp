// COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
// Part of the Debugger Utility for DreamStudio IDE.
//
// Main implementation for process manager (expands process.h)
//
// THIS PART OF THE CODE IS PROTECTED UNDER GPLv3. READ LICENSE FOR MORE INFO.

// Written by Bahaa Nofal

#include "process.h"

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <psapi.h>
#include <pdh.h>
#pragma comment(lib, "psapi.lib")
#pragma comment(lib, "pdh.lib")
#endif

#ifdef __linux__
#include <fstream>
#include <sstream>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/time.h>
#endif

#include <chrono>
#include <thread>

// ---------------------------------------------------------------------------
// Common
// ---------------------------------------------------------------------------

ProcessMonitor::ProcessMonitor(uint64_t pid)
    : m_pid(pid), m_valid(false)
#ifdef _WIN32
    , m_process_handle(nullptr), m_last_cpu_time(0),
      m_last_sys_time(0), m_last_timestamp(0)
#endif
#ifdef __linux__
    , m_prev_cpu_total(0.0), m_prev_cpu_process(0.0)
#endif
{
#ifdef _WIN32
    m_process_handle = OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, static_cast<DWORD>(pid));
    m_valid = (m_process_handle != nullptr);

    if (m_valid) {
        FILETIME creation_time, exit_time, kernel_time, user_time;
        if (GetProcessTimes(m_process_handle, &creation_time, &exit_time, &kernel_time, &user_time)) {
            ULARGE_INTEGER kt, ut;
            kt.LowPart = kernel_time.dwLowDateTime;
            kt.HighPart = kernel_time.dwHighDateTime;
            ut.LowPart = user_time.dwLowDateTime;
            ut.HighPart = user_time.dwHighDateTime;
            m_last_cpu_time = kt.QuadPart + ut.QuadPart;

            FILETIME sys_idle, sys_kernel, sys_user;
            if (GetSystemTimes(&sys_idle, &sys_kernel, &sys_user)) {
                ULARGE_INTEGER sk, su;
                sk.LowPart = sys_kernel.dwLowDateTime;
                sk.HighPart = sys_kernel.dwHighDateTime;
                su.LowPart = sys_user.dwLowDateTime;
                su.HighPart = sys_user.dwHighDateTime;
                m_last_sys_time = sk.QuadPart + su.QuadPart;
            }
        }
        m_last_timestamp = static_cast<uint64_t>(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now().time_since_epoch())
                .count());
    }
#endif

#ifdef __linux__
    std::string stat_path = "/proc/" + std::to_string(pid) + "/stat";
    std::ifstream f(stat_path);
    m_valid = f.good();
#endif
}

ProcessMonitor::~ProcessMonitor() {
#ifdef _WIN32
    if (m_process_handle) {
        CloseHandle(static_cast<HANDLE>(m_process_handle));
        m_process_handle = nullptr;
    }
#endif
}

bool ProcessMonitor::is_valid() const {
    return m_valid;
}


#ifdef _WIN32

ProcessInfo ProcessMonitor::snapshot() {
    ProcessInfo info{};
    info.pid = m_pid;

    if (!m_valid) return info;

    // --- Process name ---
    char exe_name[MAX_PATH] = {0};
    DWORD name_len = MAX_PATH;
    if (QueryFullProcessImageNameA(m_process_handle, 0, exe_name, &name_len)) {
        info.name = exe_name;
    }

    // --- Memory usage ---
    PROCESS_MEMORY_COUNTERS pmc{};
    if (GetProcessMemoryInfo(m_process_handle, &pmc, sizeof(pmc))) {
        info.memory_usage_bytes = pmc.WorkingSetSize;
    }

    // --- CPU usage ---
    FILETIME creation_time, exit_time, kernel_time, user_time;
    if (GetProcessTimes(m_process_handle, &creation_time, &exit_time, &kernel_time, &user_time)) {
        ULARGE_INTEGER kt, ut;
        kt.LowPart = kernel_time.dwLowDateTime;
        kt.HighPart = kernel_time.dwHighDateTime;
        ut.LowPart = user_time.dwLowDateTime;
        ut.HighPart = user_time.dwHighDateTime;
        uint64_t current_cpu_time = kt.QuadPart + ut.QuadPart;

        FILETIME sys_idle, sys_kernel, sys_user;
        GetSystemTimes(&sys_idle, &sys_kernel, &sys_user);
        ULARGE_INTEGER sk, su;
        sk.LowPart = sys_kernel.dwLowDateTime;
        sk.HighPart = sys_kernel.dwHighDateTime;
        su.LowPart = sys_user.dwLowDateTime;
        su.HighPart = sys_user.dwHighDateTime;
        uint64_t current_sys_time = sk.QuadPart + su.QuadPart;

        uint64_t cpu_delta = current_cpu_time - m_last_cpu_time;
        uint64_t sys_delta = current_sys_time - m_last_sys_time;

        uint64_t now_ms = static_cast<uint64_t>(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now().time_since_epoch())
                .count());
        uint64_t time_delta = now_ms - m_last_timestamp;

        if (sys_delta > 0 && time_delta > 0) {
            SYSTEM_INFO sys_info;
            GetSystemInfo(&sys_info);
            DWORD num_cpus = sys_info.dwNumberOfProcessors;
            info.cpu_usage = (static_cast<double>(cpu_delta) / static_cast<double>(sys_delta)) *
                             static_cast<double>(num_cpus) * 100.0;
            if (info.cpu_usage > 100.0 * num_cpus)
                info.cpu_usage = 100.0 * num_cpus;
        }

        m_last_cpu_time = current_cpu_time;
        m_last_sys_time = current_sys_time;
        m_last_timestamp = now_ms;
    }

    // --- Disk usage (I/O counters) ---
    IO_COUNTERS io_counters{};
    if (GetProcessIoCounters(m_process_handle, &io_counters)) {
        info.disk_read_bytes = io_counters.ReadTransferCount;
        info.disk_write_bytes = io_counters.WriteTransferCount;
    }

    // --- Process state ---
    DWORD exit_code = 0;
    if (GetExitCodeProcess(m_process_handle, &exit_code)) {
        if (exit_code == STILL_ACTIVE)
            info.state = "running";
        else
            info.state = "terminated";
    }

    return info;
}

#endif


#ifdef __linux__

static uint64_t read_sys_uptime() {
    std::ifstream f("/proc/uptime");
    double uptime_s = 0.0;
    if (f.is_open()) f >> uptime_s;
    static long ticks_per_sec = sysconf(_SC_CLK_TCK);
    return static_cast<uint64_t>(uptime_s * ticks_per_sec);
}

static long get_num_cpus() {
    std::ifstream f("/proc/cpuinfo");
    long count = 0;
    std::string line;
    while (std::getline(f, line)) {
        if (line.substr(0, 9) == "processor") count++;
    }
    return count > 0 ? count : 1;
}

ProcessInfo ProcessMonitor::snapshot() {
    ProcessInfo info{};
    info.pid = m_pid;

    if (!m_valid) return info;

    std::string base = "/proc/" + std::to_string(m_pid);

    {
        std::ifstream comm(base + "/comm");
        if (comm.is_open()) {
            std::getline(comm, info.name);
            while (!info.name.empty() && (info.name.back() == '\n' || info.name.back() == '\r'))
                info.name.pop_back();
        }
    }

    {
        std::ifstream status(base + "/status");
        std::string line;
        while (std::getline(status, line)) {
            if (line.substr(0, 6) == "VmRSS:") {
                std::istringstream ss(line.substr(6));
                uint64_t kb = 0;
                ss >> kb;
                info.memory_usage_bytes = kb * 1024;
                break;
            }
        }
    }

    {
        std::ifstream stat_file(base + "/stat");
        if (stat_file.is_open()) {
            std::string line;
            std::getline(stat_file, line);

            size_t rp = line.rfind(')');
            if (rp != std::string::npos) {
                std::istringstream ss(line.substr(rp + 2));
                std::string token;
                // fields: state(3) ppid(4) pgrp(5) session(6) tty_nr(7) tpgid(8)
                //          flags(9) minflt(10) cminflt(11) majflt(12) cmajflt(13)
                //          utime(14) stime(15)
                for (int i = 0; i < 11; ++i) {
                    if (!(ss >> token)) break;
                }
                long utime = 0, stime = 0;
                if (ss >> utime >> stime) {
                    double process_total = static_cast<double>(utime + stime);
                    long ticks_per_sec = sysconf(_SC_CLK_TCK);
                    uint64_t uptime_ticks = read_sys_uptime();

                    double seconds = static_cast<double>(uptime_ticks) -
                                     (static_cast<double>(process_total) / static_cast<double>(ticks_per_sec));

                    if (seconds > 0.0) {
                        long num_cpus = get_num_cpus();
                        info.cpu_usage = (process_total / static_cast<double>(ticks_per_sec)) /
                                         seconds * 100.0 / static_cast<double>(num_cpus);
                        if (info.cpu_usage < 0.0) info.cpu_usage = 0.0;
                        if (info.cpu_usage > 100.0) info.cpu_usage = 100.0;
                    }

                    m_prev_cpu_process = process_total;
                }
            }
        }
    }

    {
        std::ifstream io_file(base + "/io");
        std::string line;
        while (std::getline(io_file, line)) {
            if (line.substr(0, 12) == "read_bytes: ") {
                std::istringstream ss(line.substr(12));
                ss >> info.disk_read_bytes;
            } else if (line.substr(0, 13) == "write_bytes: ") {
                std::istringstream ss(line.substr(13));
                ss >> info.disk_write_bytes;
            }
        }
    }

    {
        std::ifstream stat_file(base + "/stat");
        if (stat_file.is_open()) {
            std::string line;
            std::getline(stat_file, line);
            size_t lp = line.find('(');
            size_t rp = line.rfind(')');
            if (lp != std::string::npos && rp != std::string::npos && rp > lp) {
                char state_char = 0;
                std::istringstream ss(line.substr(rp + 2));
                ss >> state_char;
                switch (state_char) {
                    case 'R': info.state = "running"; break;
                    case 'S': info.state = "sleeping"; break;
                    case 'D': info.state = "disk_sleep"; break;
                    case 'Z': info.state = "zombie"; break;
                    case 'T': info.state = "stopped"; break;
                    case 't': info.state = "tracing_stop"; break;
                    case 'X': info.state = "dead"; break;
                    case 'x': info.state = "dead"; break;
                    case 'P': info.state = "parked"; break;
                    default:  info.state = "unknown"; break;
                }
            }
        }
    }

    return info;
}

#endif

// COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
// Part of the Debugger Utility for DreamStudio IDE.
//
// Main code for the system monitor utility. Launched by the IDE as
// DreamStudioProcessManager. Accepts a PID, monitors the process,
// and outputs results as JSON.
//
// THIS PART OF THE CODE IS PROTECTED UNDER GPLv3. READ LICENSE FOR MORE INFO.

// Written by Bahaa Nofal

#include "process.h"
#include "processor.h"
#include "system.h"

#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <thread>
#include <chrono>

static std::string json_escape(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 8);
    for (char c : s) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:   out += c;      break;
        }
    }
    return out;
}

static std::string process_info_json(const ProcessInfo& p) {
    std::ostringstream ss;
    ss << "    {\n"
       << "      \"pid\": " << p.pid << ",\n"
       << "      \"name\": \"" << json_escape(p.name) << "\",\n"
       << "      \"state\": \"" << json_escape(p.state) << "\",\n"
       << "      \"cpu_usage\": " << p.cpu_usage << ",\n"
       << "      \"memory_bytes\": " << p.memory_usage_bytes << ",\n"
       << "      \"disk_read_bytes\": " << p.disk_read_bytes << ",\n"
       << "      \"disk_write_bytes\": " << p.disk_write_bytes << "\n"
       << "    }";
    return ss.str();
}

static std::string processor_info_json(const ProcessorInfo& p) {
    std::ostringstream ss;
    ss << "  \"processor\": {\n"
       << "    \"vendor\": \"" << json_escape(p.vendor) << "\",\n"
       << "    \"brand\": \"" << json_escape(p.brand) << "\",\n"
       << "    \"physical_cores\": " << p.physical_cores << ",\n"
       << "    \"logical_cores\": " << p.logical_cores << ",\n"
       << "    \"family\": " << p.family << ",\n"
       << "    \"model\": " << p.model << ",\n"
       << "    \"stepping\": " << p.stepping << ",\n"
       << "    \"current_freq_mhz\": " << p.current_freq_mhz << ",\n"
       << "    \"max_freq_mhz\": " << p.max_freq_mhz << "\n"
       << "  }";
    return ss.str();
}

static std::string system_info_json(const SystemInfo& s) {
    std::ostringstream ss;
    ss << "  \"system\": {\n"
       << "    \"os\": \"" << json_escape(s.os_name) << "\",\n"
       << "    \"total_memory_bytes\": " << s.total_memory_bytes << ",\n"
       << "    \"available_memory_bytes\": " << s.available_memory_bytes << ",\n"
       << "    \"uptime_seconds\": " << s.uptime_seconds << "\n"
       << "  }";
    return ss.str();
}

static std::string build_snapshot_json(const ProcessorInfo& proc_info,
                                       const ProcessInfo& procmon_info,
                                       const SystemInfo& sys_info,
                                       uint64_t pid) {
    std::ostringstream ss;
    ss << "{\n"
       << "  \"pid\": " << pid << ",\n"
       << processor_info_json(proc_info) << ",\n"
       << "  \"process\":\n"
       << process_info_json(procmon_info) << ",\n"
       << system_info_json(sys_info) << "\n"
       << "}\n";
    return ss.str();
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << (argc > 0 ? argv[0] : "DreamStudioProcessManager")
                  << " <PID>\n";
        return 1;
    }

    uint64_t pid = 0;
    try {
        pid = static_cast<uint64_t>(std::stoull(argv[1]));
    } catch (...) {
        std::cerr << "Error: invalid PID '" << argv[1] << "'\n";
        return 1;
    }

    Processor processor;
    ProcessMonitor monitor(pid);
    SystemMonitor system_mon;

    if (!monitor.is_valid()) {
        std::cerr << "Error: could not attach to process " << pid << "\n";
        return 1;
    }

    std::cerr << "DreamStudioProcessManager: monitoring PID " << pid << "\n";

    while (true) {
        ProcessInfo snapshot = monitor.snapshot();
        SystemInfo sys_snapshot = system_mon.snapshot();
        std::string json = build_snapshot_json(processor.info(), snapshot, sys_snapshot, pid);

        std::cout << json << std::flush;
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    return 0;
}

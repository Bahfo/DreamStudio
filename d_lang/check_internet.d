module d_lang.check_internet;

import core.time;
import std.stdio;
import std.socket;
import std.string;
import std.process;
import std.algorithm;
import std.datetime.stopwatch;

bool checkIfInternet(string ip = "8.8.8.8", ushort port = 53, out long latencyMS) {
    auto sw = StopWatch(AutoStart.no);

    try {
        auto addr = new InternetAddress(ip, port);
        auto sock = new Socket(AddressFamily.INET, SocketType.STREAM, ProtocolType.TCP);

        scope(exit) sock.close();

        sock.setOption(SocketOptionLevel.SOCKET, SocketOption.RCVTIMEO, dur!"seconds"(3));
        sock.setOption(SocketOptionLevel.SOCKET, SocketOption.SNDTIMEO, dur!"seconds"(3));

        sw.start();
        sock.connect(addr);
        sw.stop();

        latencyMS = sw.peek().total!"msecs";
        return true;
    } catch (SocketOSException e) {
        return false;
    } catch (Exception e) {
        return false;
    }
}

void checkWiFiSignalStrength() {
    version (Windows) {
        auto result = executeShell("netsh wlan show interface");

        if (result.status == 0) {
            auto lines = result.output.splitLines();
            foreach (line; lines) {
                if (line.canFind("Signal")) {
                    writeln("Wi-Fi Strength: ", line.strip());
                    return;
                }
            }
            writeln("ERROR: Not Connected to Wi-Fi");
        } else {
            writeln("ERROR: Failed to Execute Network Connection!");
        }
    } else version (linux) {
        auto result = executeShell("iwconfig");

        if (result.status == 0) {
            auto lines = result.output.splitLines();
            foreach (line; lines) {
                if (line.canFind("Link Quality")) {
                    writeln("Wi-Fi Strength: ", line.strip());
                    return;
                }
            }
            writeln("ERROR: Not Connected to Wi-Fi");
        } else {
            writeln("ERROR: Failed to Execute Network Connection!");
        }
    } else {
        writeln("ERROR: Wi-Fi signal check is not implemented for this OS.");
    }
}

void main() {
    long connectionSpeed;
    bool online = checkIfInternet("8.8.8.8", 53, connectionSpeed);

    if (online) {
        writeln("You are online!");
        writeln("Latency: ", connectionSpeed, " ms");
        if (connectionSpeed < 40) writeln("Connection Strength: Excellent (Blazing fast)");
        else if (connectionSpeed < 100) writeln("Connection Strength: Good (Decent for daily use)");
        else writeln("Connection Strength: Poor (Expect some lag)");
    } else writeln(" You are offline! Check your cables or router.");

    checkWiFiSignalStrength();
}
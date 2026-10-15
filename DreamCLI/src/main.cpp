#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#include "lexer.hpp"
#include "token.hpp"

namespace {

std::string escapeForDisplay(const std::string& value) {
    std::string out;
    for (char c : value) {
        switch (c) {
            case '\n': out += "\\n"; break;
            case '\t': out += "\\t"; break;
            case '\r': out += "\\r"; break;
            default: out += c; break;
        }
    }
    return out;
}

int dumpSource(const std::string& source, const std::string& label) {
    try {
        Lexer lexer(source);
        for (const Token& token : lexer.tokenize()) {
            std::cout << tokenTypeToString(token.type) << "(\""
                      << escapeForDisplay(token.value) << "\") @" << token.line
                      << ":" << token.column;
            if (token.type == TokenType::END_OF_FILE) {
                std::cout << "  # " << label;
            }
            std::cout << "\n";
        }
    } catch (const std::exception& ex) {
        std::cerr << "Lexer error in " << label << ": " << ex.what() << "\n";
        return 1;
    }
    return 0;
}

}  // namespace

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cout << "Usage: dscript <file.dscript>\n";
        return 2;
    }
    const std::string path = argv[1];
    std::ifstream file(path);
    if (!file) {
        std::cerr << "Cannot open file: " << path << "\n";
        return 1;
    }
    std::ostringstream buffer;
    buffer << file.rdbuf();
    return dumpSource(buffer.str(), path);
}

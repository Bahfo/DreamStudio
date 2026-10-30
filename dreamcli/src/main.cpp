#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#include "interpreter.hpp"
#include "lexer.hpp"
#include "parser.hpp"

namespace {

void printUsage(std::ostream& output) {
    output << "Usage: dscript <file.dscript>\n"
              "       dscript -e \"<script>\"\n"
              "       dscript --help\n";
}

int runSource(const std::string& source, const std::string& label,
              std::istream& input, std::ostream& output) {
    try {
        Lexer lexer(source);
        std::vector<Token> tokens = lexer.tokenize();

        Parser parser(tokens);
        Program program = parser.parse();

        Interpreter interpreter(input, output);
        interpreter.execute(program);
        return 0;
    } catch (const RuntimeError& error) {
        std::cerr << label << ":" << error.line() << ":" << error.column()
                  << ": runtime error: " << error.what() << "\n";
        return 1;
    } catch (const std::exception& error) {
        std::cerr << label << ": " << error.what() << "\n";
        return 1;
    }
}

}  // namespace

int main(int argc, char* argv[]) {
    if (argc == 2) {
        const std::string argument = argv[1];

        if (argument == "--help" || argument == "-h") {
            printUsage(std::cout);
            return 0;
        }

        std::ifstream file(argument, std::ios::binary);
        if (!file) {
            std::cerr << "Cannot open file: " << argument << "\n";
            return 1;
        }

        std::ostringstream buffer;
        buffer << file.rdbuf();
        return runSource(buffer.str(), argument, std::cin, std::cout);
    }

    if (argc == 3 && std::string(argv[1]) == "-e") {
        return runSource(argv[2], "<command>", std::cin, std::cout);
    }

    printUsage(std::cerr);
    return 2;
}

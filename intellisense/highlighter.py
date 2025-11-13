import re

class PythonHighlighter():
    def __init__(self):
        self.blue_words = ["and", "class", "def", "False", "global", "in", "is", "lambda", "None", "nonlocal",
                           "not", "or", "True","self"]

        self.pink_words = ["as", "assert", "async", "await", "break", "case", "continue", "del",
                           "elif", "else", "except", "finally", "for", "from", "if", "import",
                           "match", "pass", "raise", "return", "try", "while", "with", "yield"]

        self.yellow_functions = ["abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
                                 "chr", "complex", "dict", "divmod", "enumerate", "filter", "float",
                                 "format", "frozenset", "hash", "hex", "id", "int", "len", "list",
                                 "map", "max", "min", "next", "oct", "ord", "pow", "range", "repr",
                                 "reversed", "round", "set", "slice", "sorted", "str", "sum", "tuple",
                                 "type", "zip", "print", "input", "dir", "help", "globals", "locals"]
        
        self.green_functions = ["callable", "classmethod", "compile", "delattr", "eval", "exec",
                                "getattr", "hasattr", "isinstance", "issubclass", "memoryview",
                                "object", "property", "setattr", "staticmethod", "super", "vars",
                                "__import__"]
        
        self.yellow_functions_strings = ["capitalize", "casefold", "center", "count", "encode", "endswith",
                                         "expandtabs", "find", "format", "format_map", "index", "isalnum",
                                         "isalpha", "isdecimal", "isdigit", "isidentifier", "islower",
                                         "isnumeric", "isprintable", "isspace", "istitle", "isupper",
                                         "join", "ljust", "lower", "lstrip", "maketrans", "partition",
                                         "replace", "rfind", "rindex", "rjust", "rpartition", "rsplit",
                                         "rstrip", "split", "splitlines", "startswith", "strip", "swapcase",
                                         "title", "translate", "upper", "zfill"]
        
        self.yellow_functions_lists = ["append", "extend", "insert", "remove", "pop", "clear",
                                       "index", "count", "sort", "reverse", "copy"]

        self.yellow_functions_dict = ["clear", "copy", "fromkeys", "get", "items", "keys",
                                      "pop", "popitem", "setdefault", "update", "values"]
        
        self.yellow_functions_tuple = ["count", "index"]

        self.yellow_functions_set = ["add", "clear", "copy", "difference", "difference_update",
                                     "discard", "intersection", "intersection_update", "isdisjoint",
                                     "issubset", "issuperset", "pop", "remove", "symmetric_difference",
                                     "symmetric_difference_update", "union", "update"]
        
        self.orange_reddish = ["BaseException", "Exception", "ArithmeticError", "AssertionError",
                               "AttributeError", "BufferError", "EOFError", "FloatingPointError",
                               "GeneratorExit", "ImportError", "ModuleNotFoundError", "IndexError",
                               "KeyError", "KeyboardInterrupt", "MemoryError", "NameError",
                               "NotImplementedError", "OSError", "OverflowError", "RecursionError",
                               "ReferenceError", "RuntimeError", "StopIteration",
                               "StopAsyncIteration", "SyntaxError", "IndentationError", "TabError",
                               "SystemError", "SystemExit", "TypeError", "UnboundLocalError",
                               "ValueError", "ZeroDivisionError"]
        
        self.purple = ["+", "-", "*", "/", "//", "%", "**", "@"]

        self.purple2 = ["=", "+=", "-=", "*=", "/=", "//=", "%=", "**=", "@=", "&=", "|=",
                        "^=", ">>=", "<<="]
        
        self.greenish = ["==", "!=", ">", "<", ">=", "<="]

        self.blueish = ["&", "|", "^", "~", "<<", ">>"]

        self.yellow = ["(",")","{","}","[","]"]

        self.special = ["if not","is not","is True","is False"]

        # Use \b for keywords to match whole words, escape all items to handle special chars (e.g., **)
        self.dictionary = {
            "python_logic_keywords": rf"\b({'|'.join(re.escape(w) for w in self.blue_words)})\b",
            "python_control_keywords": rf"\b({'|'.join(re.escape(w) for w in self.pink_words)})\b",
            "python_builtin_simple_returns": rf"\b({'|'.join(re.escape(w) for w in self.yellow_functions)})\b",
            "python_builtin_complex_returns": rf"\b({'|'.join(re.escape(w) for w in self.green_functions)})\b",
            "python_string_methods": rf"\b({'|'.join(re.escape(w) for w in self.yellow_functions_strings)})\b",
            "python_list_methods": rf"\b({'|'.join(re.escape(w) for w in self.yellow_functions_lists)})\b",
            "python_dictionary_methods": rf"\b({'|'.join(re.escape(w) for w in self.yellow_functions_dict)})\b",
            "python_tuple_methods": rf"\b({'|'.join(re.escape(w) for w in self.yellow_functions_tuple)})\b",
            "python_set_methods": rf"\b({'|'.join(re.escape(w) for w in self.yellow_functions_set)})\b",
            "python_exceptions_list": rf"\b({'|'.join(re.escape(w) for w in self.orange_reddish)})\b",
            "python_arithmetic_operators": rf"({'|'.join(re.escape(op) for op in self.purple)})",
            "python_assignments_operators": rf"({'|'.join(re.escape(op) for op in self.purple2)})",
            "python_comparison_operators": rf"({'|'.join(re.escape(op) for op in self.greenish)})",
            "python_logical_operators": rf"({'|'.join(re.escape(op) for op in self.blueish)})",
            "python_brackets": rf"({'|'.join(re.escape(op) for op in self.yellow)})",
            "python_special_logic_statments":rf"({'|'.join(re.escape(op) for op in self.special)})",
            "strings": r"(\".*?\"|'.*?')",
            "comments": r"#.*",
            "numbers": r"\b\d+(\.\d+)?([eE][-+]?\d+)?\b"
        }

        self.variables = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

        self.colors = {
            "strings":"#C77859",
            "comments":"#6A9955",
            "python_logic_keywords": "#569CD6",
            "python_control_keywords": "#C586C0",
            "python_builtin_simple_returns": "#DCDCAA",
            "python_builtin_complex_returns": "#3FC8AD",
            "python_string_methods": "#DCDCAA",
            "python_list_methods": "#DCDCAA",
            "python_dictionary_methods": "#DCDCAA",
            "python_tuple_methods": "#DCDCAA",
            "python_set_methods": "#DCDCAA",
            "python_exceptions_list": "#F44747",
            "python_arithmetic_operators": "#D4D4D4",
            "python_assignments_operators": "#916484",
            "python_comparison_operators": "#B5CEA8",
            "python_logical_operators": "#5656D6",
            "python_brackets": "#ffff00",
            "python_numbers": "#CEA8A8",
            "variables":"#9CDCFE",
            "special_statements":"#8D59FF"
        }

        self.token_pattern = r"#.*|\".*?\"|\b\d+(\.\d+)?([eE][-+]?\d+)?\b|'.*?'|\b\w+\b|==|!=|>=|<=|//|<<|>>|[-+*/%&|^~@]=?|[(){}\[\],.:]"
        self.special_logic_pattern = re.compile(r'\b(?:is\s+not|is\s+True|is\s+False|if\s+not)\b')

    def highlight_token(self, token):
        for category, pattern in self.dictionary.items():
            if re.fullmatch(pattern, token):
                return category
        return None
    

class CHighlighter():
    def __init__(self):
        self.blue_words = ["auto", "break", "case", "char", "const", "continue", "default",
                           "do", "double", "else", "enum", "extern", "float", "for", "goto",
                           "if", "inline", "int", "long", "register", "restrict", "return",
                           "short", "signed", "sizeof", "static", "struct", "switch", "typedef",
                           "union", "unsigned", "void", "volatile", "while", "_Alignas", "_Alignof",
                           "_Atomic", "_Bool", "_Complex", "_Generic", "_Imaginary", "_Noreturn", "_Static_assert", "_Thread_local"]

        self.library_definition = ["#include", "#define", "#ifdef", "#ifndef", "#endif"]
        
        self.green_functions = ["printf", "scanf", "sprintf", "sscanf", "fopen", "fclose", 
                                "fread", "fwrite", "malloc", "calloc", "free", "exit", "atoi",
                                "atof", "strcpy", "strncpy", "strlen", "strcmp", "strcat"]
        
        self.orange_reddish = ["NULL", "EOF", "EXIT_SUCCESS", "EXIT_FAILURE"]

        self.purple = ["+", "-", "*", "/", "%", "++", "--"]
        self.purple2 = ["=", "+=", "-=", "*=", "/=", "%="]
        self.greenish = ["==", "!=", ">", "<", ">=", "<="]
        self.blueish = ["&", "|", "^", "~", "<<", ">>", "&&", "||", "!"]
        self.yellow = ["(",")","{","}","[","]",";",","]

        # Dictionary with regex for tags
        self.dictionary = {
            "c_keywords": rf"\b({'|'.join(re.escape(w) for w in self.blue_words)})\b",
            "c_builtin_functions": rf"\b({'|'.join(re.escape(w) for w in self.green_functions)})\b",
            "c_constants": rf"\b({'|'.join(re.escape(w) for w in self.orange_reddish)})\b",
            "c_arithmetic_operators": rf"({'|'.join(re.escape(op) for op in self.purple)})",
            "c_assignment_operators": rf"({'|'.join(re.escape(op) for op in self.purple2)})",
            "c_comparison_operators": rf"({'|'.join(re.escape(op) for op in self.greenish)})",
            "c_logical_operators": rf"({'|'.join(re.escape(op) for op in self.blueish)})",
            "c_brackets": rf"({'|'.join(re.escape(op) for op in self.yellow)})",
            "c_library": rf"({'|'.join(re.escape(op) for op in self.library_definition)})",
            "strings": r"(\".*?\"|'.*?')",
            "comments": r"(//.*|/\*[\s\S]*?\*/)",
            "numbers": r"\b\d+(\.\d+)?([eE][-+]?\d+)?\b"
        }

        self.variables = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

        self.colors = {
            "strings":"#C77859",
            "comments":"#6A9955",
            "c_keywords": "#569CD6",
            "c_builtin_functions": "#DCDCAA",
            "c_constants": "#F44747",
            "c_arithmetic_operators": "#D4D4D4",
            "c_assignment_operators": "#916484",
            "c_comparison_operators": "#B5CEA8",
            "c_logical_operators": "#5656D6",
            "c_brackets": "#ffff00",
            "numbers": "#CEA8A8",
            "variables":"#9CDCFE",
            "c_library": "#C586C0"
        }

        self.token_pattern = r"(?:#\w+)|//.*|/\*[\s\S]*?\*/|\".*?\"|'.*?'|\b\d+(\.\d+)?\b|\b\w+\b|==|!=|>=|<=|\+\+|--|[-+*/%&|^~<>]=?|[(){}\[\],.;]"
        self.special_logic_pattern = re.compile(r'\b(?:==|!=|>=|<=)\b')

    def highlight_token(self, token):
        for category, pattern in self.dictionary.items():
            if re.fullmatch(pattern, token):
                return category
        return None

class CPPHighlighter():
    def __init__(self):
        self.blue_words = ["alignas","alignof","and","and_eq","asm","auto","bitand","bitor","bool",
                           "break","case","catch","char","char16_t","char32_t","class","compl","const",
                           "constexpr","const_cast","continue","decltype","default","delete","do","double",
                           "dynamic_cast","else","enum","explicit","export","extern","false","float","for",
                           "friend","goto","if","inline","int","long","mutable","namespace","new","noexcept",
                           "not","not_eq","nullptr","operator","or","or_eq","private","protected","public",
                           "register","reinterpret_cast","return","short","signed","sizeof","static",
                           "static_assert","static_cast","struct","switch","template","this","thread_local",
                           "throw","true","try","typedef","typeid","typename","union","unsigned","using",
                           "virtual","void","volatile","wchar_t","while","xor","xor_eq"]

        self.green_functions = ["std::cout","std::cin","printf","scanf","sprintf","sscanf","fopen","fclose",
                                "fread","fwrite","malloc","calloc","free","exit","atoi","atof","strcpy",
                                "strncpy","strlen","strcmp","strcat"]

        self.orange_reddish = ["NULL","EOF","EXIT_SUCCESS","EXIT_FAILURE"]

        self.purple = ["+", "-", "*", "/", "%", "++", "--"]
        self.purple2 = ["=", "+=", "-=", "*=", "/=", "%="]
        self.greenish = ["==", "!=", ">", "<", ">=", "<="]
        self.blueish = ["&","|","^","~","<<",">>","&&","||","!"]
        self.yellow = ["(",")","{","}","[","]",";",","]

        self.library_definition = ["#include","#define","#ifdef","#ifndef","#endif"]

        self.dictionary = {
            "cpp_keywords": rf"\b({'|'.join(re.escape(w) for w in self.blue_words)})\b",
            "cpp_builtin_functions": rf"\b({'|'.join(re.escape(w) for w in self.green_functions)})\b",
            "cpp_constants": rf"\b({'|'.join(re.escape(w) for w in self.orange_reddish)})\b",
            "cpp_arithmetic_operators": rf"({'|'.join(re.escape(op) for op in self.purple)})",
            "cpp_assignment_operators": rf"({'|'.join(re.escape(op) for op in self.purple2)})",
            "cpp_comparison_operators": rf"({'|'.join(re.escape(op) for op in self.greenish)})",
            "cpp_logical_operators": rf"({'|'.join(re.escape(op) for op in self.blueish)})",
            "cpp_brackets": rf"({'|'.join(re.escape(op) for op in self.yellow)})",
            "cpp_library": rf"({'|'.join(re.escape(op) for op in self.library_definition)})",
            "strings": r"(\".*?\"|'.*?')",
            "comments": r"(//.*|/\*[\s\S]*?\*/)",
            "numbers": r"\b\d+(\.\d+)?([eE][-+]?\d+)?\b"
        }

        self.variables = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

        self.colors = {
            "strings":"#C77859",
            "comments":"#6A9955",
            "cpp_keywords":"#569CD6",
            "cpp_builtin_functions":"#DCDCAA",
            "cpp_constants":"#F44747",
            "cpp_arithmetic_operators":"#D4D4D4",
            "cpp_assignment_operators":"#916484",
            "cpp_comparison_operators":"#B5CEA8",
            "cpp_logical_operators":"#5656D6",
            "cpp_brackets":"#ffff00",
            "numbers":"#CEA8A8",
            "variables":"#9CDCFE",
            "cpp_library":"#C586C0"
        }

        self.token_pattern = r"(?:#\w+)|//.*|/\*[\s\S]*?\*/|\".*?\"|'.*?'|\b\d+(\.\d+)?\b|\b\w+\b|==|!=|>=|<=|\+\+|--|[-+*/%&|^~<>]=?|[(){}\[\],.;]"
        self.special_logic_pattern = re.compile(r'\b(?:==|!=|>=|<=)\b')

    def highlight_token(self, token):
        for category, pattern in self.dictionary.items():
            if re.fullmatch(pattern, token):
                return category
        return None
    

class JavaHighlighter():
    def __init__(self):
        self.blue_words = ["abstract","assert","boolean","break","byte","case","catch","char",
                           "class","const","continue","default","do","double","else","enum",
                           "extends","final","finally","float","for","goto","if","implements",
                           "import","instanceof","int","interface","long","native","new","package",
                           "private","protected","public","return","short","static","strictfp",
                           "super","switch","synchronized","this","throw","throws","transient",
                           "try","void","volatile","while","true","false","null"]

        self.green_functions = ["System.out.println","Math.abs","Math.max","Math.min","Integer.parseInt",
                                "Double.parseDouble","String.valueOf","Arrays.sort","Collections.sort"]

        self.orange_reddish = ["Integer","Double","Float","String","Boolean","Character","Long","Short","Byte","Void"]

        self.purple = ["+", "-", "*", "/", "%"]
        self.purple2 = ["=", "+=", "-=", "*=", "/=", "%="]
        self.greenish = ["==","!=","<",">","<=",">="]
        self.blueish = ["&","|","^","~","&&","||","!"]
        self.yellow = ["(",")","{","}","[","]",";",",","."]

        self.dictionary = {
            "java_keywords": rf"\b({'|'.join(re.escape(w) for w in self.blue_words)})\b",
            "java_builtin_functions": rf"\b({'|'.join(re.escape(w) for w in self.green_functions)})\b",
            "java_constants": rf"\b({'|'.join(re.escape(w) for w in self.orange_reddish)})\b",
            "java_arithmetic_operators": rf"({'|'.join(re.escape(op) for op in self.purple)})",
            "java_assignment_operators": rf"({'|'.join(re.escape(op) for op in self.purple2)})",
            "java_comparison_operators": rf"({'|'.join(re.escape(op) for op in self.greenish)})",
            "java_logical_operators": rf"({'|'.join(re.escape(op) for op in self.blueish)})",
            "java_brackets": rf"({'|'.join(re.escape(op) for op in self.yellow)})",
            "strings": r"(\".*?\"|'.*?')",
            "comments": r"(//.*|/\*[\s\S]*?\*/)",
            "numbers": r"\b\d+(\.\d+)?([eE][-+]?\d+)?\b"
        }

        self.variables = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

        self.colors = {
            "strings":"#C77859",
            "comments":"#6A9955",
            "java_keywords":"#569CD6",
            "java_builtin_functions":"#DCDCAA",
            "java_constants":"#F44747",
            "java_arithmetic_operators":"#D4D4D4",
            "java_assignment_operators":"#916484",
            "java_comparison_operators":"#B5CEA8",
            "java_logical_operators":"#5656D6",
            "java_brackets":"#ffff00",
            "numbers":"#CEA8A8",
            "variables":"#9CDCFE"
        }

        self.token_pattern = r"//.*|/\*[\s\S]*?\*/|\".*?\"|'.*?'|\b\d+(\.\d+)?\b|\b\w+\b|==|!=|>=|<=|[-+*/%&|^~!]=?|[(){}\[\],.;]"
        self.special_logic_pattern = re.compile(r'\b(?:==|!=|>=|<=)\b')

    def highlight_token(self, token):
        for category, pattern in self.dictionary.items():
            if re.fullmatch(pattern, token):
                return category
        return None


class JavascriptHighlighter():
    def __init__(self):
        self.blue_words = ["break","case","catch","class","const","continue","debugger","default","delete",
                           "do","else","export","extends","finally","for","function","if","import","in",
                           "instanceof","let","new","return","super","switch","this","throw","try","typeof",
                           "var","void","while","with","yield","true","false","null","undefined"]

        self.green_functions = ["alert","console.log","parseInt","parseFloat","isNaN","isFinite",
                                "decodeURI","decodeURIComponent","encodeURI","encodeURIComponent","Number",
                                "String","Boolean","Object","Array","Date","Math"]

        self.orange_reddish = ["Infinity","NaN"]

        self.purple = ["+","-","*","/","%","**","++","--"]
        self.purple2 = ["=","+=","-=","*=","/=","%=","**="]
        self.greenish = ["==","===","!=","!==",">","<",">=","<="]
        self.blueish = ["&","|","^","~","&&","||","!","??"]
        self.yellow = ["(",")","{","}","[","]",";",",","."]

        self.dictionary = {
            "js_keywords": rf"\b({'|'.join(re.escape(w) for w in self.blue_words)})\b",
            "js_builtin_functions": rf"\b({'|'.join(re.escape(w) for w in self.green_functions)})\b",
            "js_constants": rf"\b({'|'.join(re.escape(w) for w in self.orange_reddish)})\b",
            "js_arithmetic_operators": rf"({'|'.join(re.escape(op) for op in self.purple)})",
            "js_assignment_operators": rf"({'|'.join(re.escape(op) for op in self.purple2)})",
            "js_comparison_operators": rf"({'|'.join(re.escape(op) for op in self.greenish)})",
            "js_logical_operators": rf"({'|'.join(re.escape(op) for op in self.blueish)})",
            "js_brackets": rf"({'|'.join(re.escape(op) for op in self.yellow)})",
            "strings": r"(\".*?\"|'.*?'|`.*?`)",
            "comments": r"(//.*|/\*[\s\S]*?\*/)",
            "numbers": r"\b\d+(\.\d+)?([eE][-+]?\d+)?\b"
        }

        self.variables = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

        self.colors = {
            "strings":"#C77859",
            "comments":"#6A9955",
            "js_keywords":"#569CD6",
            "js_builtin_functions":"#DCDCAA",
            "js_constants":"#F44747",
            "js_arithmetic_operators":"#D4D4D4",
            "js_assignment_operators":"#916484",
            "js_comparison_operators":"#B5CEA8",
            "js_logical_operators":"#5656D6",
            "js_brackets":"#ffff00",
            "numbers":"#CEA8A8",
            "variables":"#9CDCFE"
        }

        self.token_pattern = r"//.*|/\*[\s\S]*?\*/|\".*?\"|'.*?'|`.*?`|\b\d+(\.\d+)?\b|\b\w+\b|==|!=|===|!==|>=|<=|[-+*/%&|^~!]=?|[(){}\[\],.;]"
        self.special_logic_pattern = re.compile(r'\b(?:==|===|!=|!==|>=|<=)\b')

    def highlight_token(self, token):
        for category, pattern in self.dictionary.items():
            if re.fullmatch(pattern, token):
                return category
        return None


class RustHighlighter():
    def __init__(self):
        self.blue_words = ["as","break","const","continue","crate","else","enum","extern","false",
                           "fn","for","if","impl","in","let","loop","match","mod","move","mut",
                           "pub","ref","return","self","Self","static","struct","super","trait",
                           "true","type","unsafe","use","where","while","dyn","async","await","try"]

        self.green_functions = ["println!","format!","vec!","String::from","Vec::new","Box::new"]

        self.orange_reddish = ["Some","None","Ok","Err"]

        self.purple = ["+","-","*","/","%","^"]
        self.purple2 = ["=","+=","-=","*=","/=","%=","^="]
        self.greenish = ["==","!=","<",">","<=",">="]
        self.blueish = ["&","|","&&","||","!","<<",">>"]
        self.yellow = ["(",")","{","}","[","]",";",",","."]

        self.dictionary = {
            "rust_keywords": rf"\b({'|'.join(re.escape(w) for w in self.blue_words)})\b",
            "rust_builtin_functions": rf"\b({'|'.join(re.escape(w) for w in self.green_functions)})\b",
            "rust_constants": rf"\b({'|'.join(re.escape(w) for w in self.orange_reddish)})\b",
            "rust_arithmetic_operators": rf"({'|'.join(re.escape(op) for op in self.purple)})",
            "rust_assignment_operators": rf"({'|'.join(re.escape(op) for op in self.purple2)})",
            "rust_comparison_operators": rf"({'|'.join(re.escape(op) for op in self.greenish)})",
            "rust_logical_operators": rf"({'|'.join(re.escape(op) for op in self.blueish)})",
            "rust_brackets": rf"({'|'.join(re.escape(op) for op in self.yellow)})",
            "strings": r"(\".*?\"|'.*?')",
            "comments": r"(//.*|/\*[\s\S]*?\*/|#!\[.*\])",
            "numbers": r"\b\d+(\.\d+)?([eE][-+]?\d+)?\b"
        }

        self.variables = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

        self.colors = {
            "strings":"#C77859",
            "comments":"#6A9955",
            "rust_keywords":"#569CD6",
            "rust_builtin_functions":"#DCDCAA",
            "rust_constants":"#F44747",
            "rust_arithmetic_operators":"#D4D4D4",
            "rust_assignment_operators":"#916484",
            "rust_comparison_operators":"#B5CEA8",
            "rust_logical_operators":"#5656D6",
            "rust_brackets":"#ffff00",
            "numbers":"#CEA8A8",
            "variables":"#9CDCFE"
        }

        self.token_pattern = r"//.*|/\*[\s\S]*?\*/|\".*?\"|'.*?'|\b\d+(\.\d+)?\b|\b\w+\b|==|!=|>=|<=|[-+*/%&|^~!]=?|[(){}\[\],.;]"
        self.special_logic_pattern = re.compile(r'\b(?:==|!=|>=|<=)\b')

    def highlight_token(self, token):
        for category, pattern in self.dictionary.items():
            if re.fullmatch(pattern, token):
                return category
        return None


class CSharpHighlighter():
    def __init__(self):
        self.blue_words = ["abstract","as","base","bool","break","byte","case","catch","char","checked",
                           "class","const","continue","decimal","default","delegate","do","double","else",
                           "enum","event","explicit","extern","false","finally","fixed","float","for","foreach",
                           "goto","if","implicit","in","int","interface","internal","is","lock","long",
                           "namespace","new","null","object","operator","out","override","params","private",
                           "protected","public","readonly","ref","return","sbyte","sealed","short","sizeof",
                           "stackalloc","static","string","struct","switch","this","throw","true","try",
                           "typeof","uint","ulong","unchecked","unsafe","ushort","using","virtual","void",
                           "volatile","while"]

        self.green_functions = ["Console.WriteLine","Console.ReadLine","Math.Abs","Math.Max","Math.Min","int.Parse","double.Parse","Convert.ToInt32"]

        self.orange_reddish = ["true","false","null"]

        self.purple = ["+", "-", "*", "/", "%","++","--"]
        self.purple2 = ["=", "+=", "-=", "*=", "/=", "%="]
        self.greenish = ["==","!=",">","<",">=","<="]
        self.blueish = ["&","|","^","~","&&","||","!"]
        self.yellow = ["(",")","{","}","[","]",";",",","."]

        self.dictionary = {
            "csharp_keywords": rf"\b({'|'.join(re.escape(w) for w in self.blue_words)})\b",
            "csharp_builtin_functions": rf"\b({'|'.join(re.escape(w) for w in self.green_functions)})\b",
            "csharp_constants": rf"\b({'|'.join(re.escape(w) for w in self.orange_reddish)})\b",
            "csharp_arithmetic_operators": rf"({'|'.join(re.escape(op) for op in self.purple)})",
            "csharp_assignment_operators": rf"({'|'.join(re.escape(op) for op in self.purple2)})",
            "csharp_comparison_operators": rf"({'|'.join(re.escape(op) for op in self.greenish)})",
            "csharp_logical_operators": rf"({'|'.join(re.escape(op) for op in self.blueish)})",
            "csharp_brackets": rf"({'|'.join(re.escape(op) for op in self.yellow)})",
            "strings": r"(\".*?\"|'.*?')",
            "comments": r"(//.*|/\*[\s\S]*?\*/)",
            "numbers": r"\b\d+(\.\d+)?([eE][-+]?\d+)?\b"
        }

        self.variables = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

        self.colors = {
            "strings":"#C77859",
            "comments":"#6A9955",
            "csharp_keywords":"#569CD6",
            "csharp_builtin_functions":"#DCDCAA",
            "csharp_constants":"#F44747",
            "csharp_arithmetic_operators":"#D4D4D4",
            "csharp_assignment_operators":"#916484",
            "csharp_comparison_operators":"#B5CEA8",
            "csharp_logical_operators":"#5656D6",
            "csharp_brackets":"#ffff00",
            "numbers":"#CEA8A8",
            "variables":"#9CDCFE"
        }

        self.token_pattern = r"//.*|/\*[\s\S]*?\*/|\".*?\"|'.*?'|\b\d+(\.\d+)?\b|\b\w+\b|==|!=|>=|<=|[-+*/%&|^~!]=?|[(){}\[\],.;]"
        self.special_logic_pattern = re.compile(r'\b(?:==|!=|>=|<=)\b')

    def highlight_token(self, token):
        for category, pattern in self.dictionary.items():
            if re.fullmatch(pattern, token):
                return category
        return None


class HTMLHighlighter():
    def __init__(self):
        self.blue_words = ["html","head","title","body","div","span","h1","h2","h3","h4","h5","h6",
                           "p","a","ul","ol","li","table","tr","td","th","thead","tbody","footer",
                           "header","nav","section","article","main","form","input","button","textarea",
                           "label","select","option","link","meta","script","style","img"]
        self.purple = ["+","-","*","/","%"]
        self.purple2 = ["="]
        self.greenish = []
        self.blueish = []
        self.yellow = ["<",">","/",'"',"="]

        self.dictionary = {
            "html_tags": rf"\b({'|'.join(re.escape(w) for w in self.blue_words)})\b",
            "html_brackets": rf"({'|'.join(re.escape(op) for op in self.yellow)})",
            "strings": r"\".*?\"",
            "comments": r"(<!--[\s\S]*?-->)"
        }

        self.colors = {
            "strings":"#C77859",
            "comments":"#6A9955",
            "html_tags": "#569CD6",
            "html_brackets": "#ffff00"
        }

        self.token_pattern = r"<!--.*?-->|<\s*/?\w+|\b\w+\b|\".*?\"|=|[<>]|/?>"
        self.special_logic_pattern = re.compile(r'<!--.*?-->')

    def highlight_token(self, token):
        for category, pattern in self.dictionary.items():
            if re.fullmatch(pattern, token):
                return category
        return None


class PHPHighlighter():
    def __init__(self):
        self.blue_words = ["abstract","and","array","as","break","callable","case","catch","class",
                           "clone","const","continue","declare","default","die","do","echo","else",
                           "elseif","empty","enddeclare","endfor","endforeach","endif","endswitch",
                           "endwhile","eval","exit","extends","final","finally","for","foreach",
                           "function","global","goto","if","implements","include","include_once",
                           "instanceof","insteadof","interface","isset","list","namespace","new",
                           "or","print","private","protected","public","require","require_once",
                           "return","static","switch","throw","trait","try","unset","use","var",
                           "while","xor","yield","true","false","null"]

        self.green_functions = ["array_merge","array_push","array_pop","count","in_array","sort",
                                "ksort","asort","explode","implode","htmlspecialchars","htmlentities",
                                "strlen","substr","strpos","trim","print_r","var_dump"]

        self.orange_reddish = ["TRUE","FALSE","NULL"]

        self.purple = ["+","-","*","/","%","**","++","--"]
        self.purple2 = ["=","+=","-=","*=","/=","%=","**="]
        self.greenish = ["==","===","!=","!==",">","<",">=","<="]
        self.blueish = ["&","|","^","~","&&","||","!","??"]
        self.yellow = ["(",")","{","}","[","]",";",",",".","$"]

        self.dictionary = {
            "php_keywords": rf"\b({'|'.join(re.escape(w) for w in self.blue_words)})\b",
            "php_builtin_functions": rf"\b({'|'.join(re.escape(w) for w in self.green_functions)})\b",
            "php_constants": rf"\b({'|'.join(re.escape(w) for w in self.orange_reddish)})\b",
            "php_arithmetic_operators": rf"({'|'.join(re.escape(op) for op in self.purple)})",
            "php_assignment_operators": rf"({'|'.join(re.escape(op) for op in self.purple2)})",
            "php_comparison_operators": rf"({'|'.join(re.escape(op) for op in self.greenish)})",
            "php_logical_operators": rf"({'|'.join(re.escape(op) for op in self.blueish)})",
            "php_brackets": rf"({'|'.join(re.escape(op) for op in self.yellow)})",
            "strings": r"(\".*?\"|'.*?')",
            "comments": r"(//.*|#.*|/\*[\s\S]*?\*/)",
            "numbers": r"\b\d+(\.\d+)?([eE][-+]?\d+)?\b"
        }

        self.variables = r"\$[a-zA-Z_][a-zA-Z0-9_]*\b"

        self.colors = {
            "strings":"#C77859",
            "comments":"#6A9955",
            "php_keywords":"#569CD6",
            "php_builtin_functions":"#DCDCAA",
            "php_constants":"#F44747",
            "php_arithmetic_operators":"#D4D4D4",
            "php_assignment_operators":"#916484",
            "php_comparison_operators":"#B5CEA8",
            "php_logical_operators":"#5656D6",
            "php_brackets":"#ffff00",
            "numbers":"#CEA8A8",
            "variables":"#9CDCFE"
        }

        self.token_pattern = r"//.*|#.*|/\*[\s\S]*?\*/|\".*?\"|'.*?'|\$?\b\d+(\.\d+)?\b|\b\w+\b|==|===|!=|!==|>=|<=|[-+*/%&|^~!]=?|[(){}\[\],.;]"
        self.special_logic_pattern = re.compile(r'\b(?:==|===|!=|!==|>=|<=)\b')

    def highlight_token(self, token):
        for category, pattern in self.dictionary.items():
            if re.fullmatch(pattern, token):
                return category
        return None
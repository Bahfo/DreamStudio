using System;
using Antlr4.Runtime;

public class LevenderInterpreter : LavenderBaseVisitor<object>
{
    private Dictionary<string, object> variables = new Dictionary<string, object>();
}
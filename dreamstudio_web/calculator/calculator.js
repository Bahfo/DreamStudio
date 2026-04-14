let operation = "";

function appendOperation(x)
{
    operation += x;
    const calculator_screen = document.getElementById('calc1-result');
    calculator_screen.innerText = operation;
}

function parseTheString()
{
    let parsed_string = [];
    let now = "";

    for (var i = 0; i < operation.length; i++)
    {
        let char = operation[i];

        if (char >= "0" && char <= "9")
        {
            now += char;
        }
        else if ("+-*/".includes(char))
        {
            parsed_string.push(now);
            parsed_string.push(char);
            now = "";
        }
    }

    parsed_string.push(now);
    return parsed_string;
}

function findSolution()
{
    array_to_solve = parseTheString();

    const result = 0;

    while (array_to_solve != [])
    {
        for (var i = 0; i < array_to_solve.length; i++)
        {
            if (array_to_solve[i] === "*" || array_to_solve[i] === "/")
            {
                if (array_to_solve[i] == "*")
                {
                    result += parseInt(array_to_solve[i-1]) * parseInt(array_to_solve[i+1]);
                    array_to_solve.splice(i-1);
                    array_to_solve.splice(i+1);
                    array_to_solve.splice(i);
                }
                else 
                {
                    result += parseInt(array_to_solve[i-1]) / parseInt(array_to_solve[i+1]);
                    array_to_solve.splice(i-1);
                    array_to_solve.splice(i+1);
                    array_to_solve.splice(i);
                }
            }
            else (array_to_solve[i] === "-" || array_to_solve[i] === "+")
            {
                if (array_to_solve[i] === "-")
                {
                    result += parseInt(array_to_solve[i-1]) - parseInt(array_to_solve[i+1]);
                    array_to_solve.splice(i-1);
                    array_to_solve.splice(i+1);
                    array_to_solve.splice(i);
                }
                else 
                {
                    result += parseInt(array_to_solve[i-1]) + parseInt(array_to_solve[i+1]);
                    array_to_solve.splice(i-1);
                    array_to_solve.splice(i+1);
                    array_to_solve.splice(i);
                }
            }
        }
    }
}
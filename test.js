// number or string, all are defined with var
var x = "Hello World"; // doesn't matter if single or double quotation

console.log(x); // developer console print
alert(x); // user's output print


// variables
// integers, floats (doubles), and booleans
// javascript has only 'numbers' data type
var t = 5;        // integer (number)
var u = 432.23;   // float (number)
var z = false;    // boolean (bool) -> only other data type

console.log(typeof(u));

var z; // also is acceptable
console.log(typeof(z)); // gives 'undefined' which is another data type

z = undefined; // built-in
var delta = NaN; // Not a Number (also built-in)
var zeta = null; // object-type

// NOTE: NaN is actually a number type

console.log(Boolean(t)); // Transforms to boolean: true if full, false if empty
console.log(Boolean("")); // false

var f;
console.log(Boolean(f)); // Also False, Same happens if f = NaN, false, undefined
console.log(Boolean(true)); // gives true
console.log(Boolean(0)); // false

// Strings:
var s1 = "Bahaa";
var s2 = "Nofal";
var s3 = 5;

console.log(s1 + s2); // Concatination: BahaaNofal (with no spaces)
console.log(s1 + " " + s2); // with a space

// Integer and String addition is AVAILABLE:
console.log(s1 + s3); // gives Bahaa5 --> strings transforms numbers to strings

var s4 = "6";
console.log(s4 + s3); // gives 65

// To transform to integer, put (+) before the string, or type (parseInt)
console.log(parseInt(s4)); // it is now integer
console.log(parseInt(s1)); // gives NaN because s1 is string not a number

// parseInt can take more than one version: 
console.log(parseInt(4,16)); // returns 4 as a hexadecimal number and converts it to 
                             // decimal integer

console.log(parseInt(1,2)); // as a binary
console.log(parseInt("10001",2)) // also works
console.log(parseInt(23423,2)); // gives NaN because 23423 is not a valid binary

// ARRAYS:
var lista = []; // empty array (as Python)
console.log(typeof x); // object type
var tw = x.length; // the length of the list

// appending the list requires only to get the element index:
lista[3] = 3; // becomes: [undefined, undefined, undefined, 3] 
// ===> VERY STRANGE AND DOES NOT MAKE SENSE

function some_function()
{
    console.log("Hi!");
}

function some_function2()
{
    console.log("Bye!");
}

some_function();
some_function2();

var array_of_functions = []
array_of_functions[0] = some_function; // appends the function to the array (VERY STRANGE)
array_of_functions[1] = some_function2; // same to index (1)

console.log(array_of_functions);

// arrays are class objects, they can be very, very flexable
console.log(array_of_functions[1]()); // gives "bye", and undefined
// Why? because 'log' returns here the type of the function too, which is undefined
array_of_functions[1](); // now it only prints ("bye")

array_of_functions.push(some_function); // appends to third index
console.log(array_of_functions.length); // becomes (3)

// there is push, pop, etc (same functionality for any array)

// OBJECTS:
var q = {}; // is an object, like dictionary in Python
// KEY: VALUE

var q1 = {
    name:"Mohammed",
    last_name: "Massoud",
    age: 40,
    major: "CS",
    3:323,
    "WITH QUOTATATIONS": "ds"
}

console.log(q1);

// objects can take functions inside

var q2 = {
    func1: function func() {
        console.log("Bye Bye Programming");
    }
}

console.log(q2.func1());

array_of_functions.push(q1, q2); // pushes more than one element

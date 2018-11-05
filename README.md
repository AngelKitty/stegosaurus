# Stegosaurus
## A steganography tool for embedding payloads within Python bytecode.

Stegosaurus is a [steganography tool](https://en.wikipedia.org/wiki/Steganography) 
that allows embedding arbitrary payloads in 
Python bytecode (pyc or pyo) files. The embedding process does not alter the 
runtime behavior or file size of the carrier file and typically results in a low 
encoding density. The payload is dispersed throughout the bytecode so tools like 
```strings```  will not show the actual payload. Python's ```dis``` module will 
return the same results for bytecode before and after Stegosaurus is used to embed 
a payload. At this time, no prior work or detection methods are known for this type 
of payload delivery.

Stegosaurus requires Python 3.6 or later.

#### Usage

    $ python3 -m stegosaurus -h
    usage: stegosaurus.py [-h] [-p PAYLOAD] [-r] [-s] [-v] [-x] carrier
    
    positional arguments:
      carrier               Carrier py, pyc or pyo file
    
    optional arguments:
      -h, --help            show this help message and exit
      -p PAYLOAD, --payload PAYLOAD
                            Embed payload in carrier file
      -r, --report          Report max available payload size carrier supports
      -s, --side-by-side    Do not overwrite carrier file, install side by side
                            instead.
      -v, --verbose         Increase verbosity once per use
      -x, --extract         Extract payload from carrier file

#### Example

Assume we wish to embed a payload in the bytecode of the following Python script, named example.py:

    """Example carrier file to embed our payload in.
    """
    
    import math
    
    def fibV1(n):
        if n == 0 or n == 1:
            return n
        return fibV1(n - 1) + fibV1(n - 2)
    
    def fibV2(n):
        if n == 0 or n == 1:
            return n
        return int(((1 + math.sqrt(5))**n - (1 - math.sqrt(5))**n) / (2**n * math.sqrt(5)))
    
    def main():
        result1 = fibV1(12)
        result2 = fibV2(12)
    
        print(result1)
        print(result2)
    
    if __name__ == "__main__":
        main()
    

The first step is to use Stegosaurus to see how many bytes our payload can contain without 
changing the size of the carrier file.

    $ python3 -m stegosaurus example.py -r
    Carrier can support a payload of 20 bytes

We can now safely embed a payload of up to 20 bytes. To help show the before and after the 
```-s``` option can be used to install the carrier file side by side with the untouched 
bytecode:

    $ python3 -m stegosaurus example.py -s --payload "root pwd: 5+3g05aW"
    Payload embedded in carrier
    
Looking on disk, both the carrier file and original bytecode file have the same size:

    $ ls -l __pycache__/example.cpython-36*
    -rw-r--r--  1 jherron  staff  743 Mar 10 00:58 __pycache__/example.cpython-36-stegosaurus.pyc
    -rw-r--r--  1 jherron  staff  743 Mar 10 00:58 __pycache__/example.cpython-36.pyc

_Note: If the ```-s``` option is omitted, the original bytecode would have been overwritten._

The payload can be extracted by passing the ```-x``` option to Stegosaurus:

    $ python3 -m stegosaurus __pycache__/example.cpython-36-stegosaurus.pyc -x
    Extracted payload: root pwd: 5+3g05aW

The payload does not have to be an ascii string, shellcode is also supported:

    $ python3 -m stegosaurus example.py -s --payload "\xeb\x2a\x5e\x89\x76"
    Payload embedded in carrier
    
    $ python3 -m stegosaurus __pycache__/example.cpython-36-stegosaurus.pyc -x
    Extracted payload: \xeb\x2a\x5e\x89\x76

To show that the runtime behavior of the Python code remains after Stegosaurus embeds the 
payload:

    $ python3 example.py
    144
    144
    
    $ python3 __pycache__/example.cpython-36.pyc 
    144
    144

    $ python3 __pycache__/example.cpython-36-stegosaurus.pyc 
    144
    144

Output of ```strings``` after Stegosaurus embeds the payload (notice the payload is 
not shown):

    $ python3 -m stegosaurus example.py -s --payload "PAYLOAD_IS_HERE"
    Payload embedded in carrier

    $ strings __pycache__/example.cpython-36-stegosaurus.pyc 
    .Example carrier file to embed our payload in.
    fibV1)
    example.pyr
    math
    sqrt)
    fibV2
    print)
    result1
    result2r
    main
    __main__)
    __doc__r
    
    __name__r
    <module>

    $ python3 -m stegosaurus __pycache__/example.cpython-36-stegosaurus.pyc -x
    Extracted payload: PAYLOAD_IS_HERE
    
Sample output of Python's ```dis``` module, which shows no difference before and after 
Stegosaurus embeds its payload:

Before:

    20 LOAD_GLOBAL              0 (int)
    22 LOAD_CONST               2 (1)
    24 LOAD_GLOBAL              1 (math)
    26 LOAD_ATTR                2 (sqrt)
    28 LOAD_CONST               3 (5)
    30 CALL_FUNCTION            1
    32 BINARY_ADD
    34 LOAD_FAST                0 (n)
    36 BINARY_POWER
    38 LOAD_CONST               2 (1)
    40 LOAD_GLOBAL              1 (math)
    42 LOAD_ATTR                2 (sqrt)
    44 LOAD_CONST               3 (5)
    46 CALL_FUNCTION            1
    48 BINARY_SUBTRACT
    50 LOAD_FAST                0 (n)
    52 BINARY_POWER
    54 BINARY_SUBTRACT
    56 LOAD_CONST               4 (2)

After:

    20 LOAD_GLOBAL              0 (int)
    22 LOAD_CONST               2 (1)
    24 LOAD_GLOBAL              1 (math)
    26 LOAD_ATTR                2 (sqrt)
    28 LOAD_CONST               3 (5)
    30 CALL_FUNCTION            1
    32 BINARY_ADD
    34 LOAD_FAST                0 (n)
    36 BINARY_POWER
    38 LOAD_CONST               2 (1)
    40 LOAD_GLOBAL              1 (math)
    42 LOAD_ATTR                2 (sqrt)
    44 LOAD_CONST               3 (5)
    46 CALL_FUNCTION            1
    48 BINARY_SUBTRACT
    50 LOAD_FAST                0 (n)
    52 BINARY_POWER
    54 BINARY_SUBTRACT
    56 LOAD_CONST               4 (2)


#### Using Stegosaurus

Payloads, delivery and reciept methods are entirely up to the user. Stegosaurus only 
provides the means to embed and extract paylods from a given Python bytecode file. 
Due to the desire to leave file size intact, a relatively few number of bytes can be used to 
deliver the payload. This may require spreading larger payloads across multiple bytecode 
files, which has some advantages such as:

* Delivering a payload in pieces over time
* Portions of the payload can be spread over mutliple locations and joined when needed
* A single portion being compromised does not divulge the whole payload
* Thwarting detection of the entire payload by spreading it across multiple seemingly unrelated files

The means to spread large payloads across multiple Python bytecode files is not supported 
as this moment, see TODOs.

#### How Stegosaurus Works

In order to embed a payload without increasing the file size, dead zones need to be identified 
within the bytecode. A dead zone is defined as any byte which if changed will not impact the 
behavior of the Python script. Python 3.6 introduced easy to exploit dead zones. Stepping back 
though, a little history to set the stage.

Python's reference interpreter, CPython has two types of opcodes - those with arguments and 
those without. In Python <= 3.5 instructions in the bytecode occupied either 1 or 3 bytes, 
depending on if the opcode took an arugment or not. In Python 3.6 this was changed so that 
all instructions occupy two bytes. Those without arguments simply set the second byte to zero 
and it is ignored during execution. This means that for each instruction in the bytecode that 
does not take an arugment, Stegosaurus can safely insert one byte of the payload.

Some examples of opcodes that do not take an argument:

    BINARY_SUBTRACT
    INPLACE_ADD
    RETURN_VALUE
    GET_ITER
    YIELD_VALUE
    IMPORT_STAR
    END_FINALLY
    NOP
    ...

To see an example of the changes in the bytecode, consider the following Python snippet:

    def test(n):
        return n + 5 + n - 3

Using ```dis``` with Python < 3.6 shows:

    0  LOAD_FAST                0 (n)
    3  LOAD_CONST               1 (5)    <-- opcodes with an arg take 3 bytes
    6  BINARY_ADD                        <-- opcodes without an arg take 1 byte
    7  LOAD_FAST                0 (n)
    10 BINARY_ADD          
    11 LOAD_CONST               2 (3)
    14 BINARY_SUBTRACT      
    15 RETURN_VALUE
    
    # :( no easy bytes to embed a payload
    
However with Python 3.6:

    0  LOAD_FAST                0 (n)
    2  LOAD_CONST               1 (5)    <-- all opcodes now occupy two bytes
    4  BINARY_ADD                        <-- opcodes without an arg leave 1 byte for the payload
    6  LOAD_FAST                0 (n)
    8  BINARY_ADD
    10 LOAD_CONST               2 (3)
    12 BINARY_SUBTRACT
    14 RETURN_VALUE
    
    # :) easy bytes to embed a payload
    
Passing ```-vv``` to Stegosaurus we can see how the payload is embedded in these dead zones:

    $ python3 -m stegosaurus ../python_tests/loop.py -s -p "ABCDE" -vv
    Read header and bytecode from carrier
    BINARY_ADD (0)
    BINARY_ADD (0)
    BINARY_SUBTRACT (0)
    RETURN_VALUE (0)
    RETURN_VALUE (0)
    Found 5 bytes available for payload
    Payload embedded in carrier
    BINARY_ADD (65)      <-- A
    BINARY_ADD (66)      <-- B
    BINARY_SUBTRACT (67) <-- C
    RETURN_VALUE (68)    <-- D
    RETURN_VALUE (69)    <-- E

_Timestamps and debug levels removed from logs for readability_

Currently this is the only dead zone that Stegosaurus exploits. Future improvements include 
more dead zone identification as mentioned in the TODOs.

#### TODOs

* Add self destruct option ```-d``` which will purge the payload from the carrier file after 
  extraction
* Support method to distribute payload across multiple carrier files
* Provide ```-t``` flag to test if a payload may be present within a carrier file
* Find more dead zones within the bytecode to place the payload, such as dead code
* Add a ```-g``` option which will grow the size of the file to supported larger payloads 
  for users that are not concerned with a change in file size (for instance if Stegosaurus 
  is injected into a build pipeline)
  
#### Contributions

Thanks to S0lll0s for:

* Prevent placing the payload in long runs of opcodes that do not take an argument 
  as this can lead to exposure of the payload through tools like ```strings```

#### Contact

For any questions, please contact the author:

Jon Herron

jon _dot_ herron _at_ yahoo.com
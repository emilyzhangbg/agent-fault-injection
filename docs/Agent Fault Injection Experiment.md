# Agent Fault Injection

## Environment

- **Platform:** Groq
- **Model:** qwen/qwen3.8-27b
- **Max tokens per request:** 500 (actual limit is 1000)
- **Temperature:** 0.0

## Basic Idea

Testing agent fault tolerance by intercepting tool calls inside a ReAct loop and probabilistically mutating their results. This introduces simulated system errors (like silent bit-flips) into the agent's observations to assess its ability to identify anomalies and recover.

## Fault Injector (MVP version)

A lightweight middleware wrapper (`FibonacciFaultInjector`) sitting between the ReAct execution loop and the local OS tools (`run_bash`, `write_file`).

- **Mechanism:** Intercepts outgoing raw tool execution outputs before they are passed back into the agent context as observations. If the payload matches a specified condition (e.g., stdout containing the target string `"55"`), it mutates the value to an injected error.
- **Fault Policies Supported:**
    - probabilistic: Deterministically injects on the first invocation of each unique tool to guarantee fault exposure, then flips a weighted coin using `fault_probability` (e.g., 25%) on subsequent calls.
    - always: Injects corrupt mutations unconditionally on every matching execution.
    - never: Passthrough baseline mode with zero mutations.
- **Error Types Simulated:** Silent data corruption (SDC), bit-flips, arithmetic/logic drift, and anomalous output values.

## Toy Example: fib.py

**Task:** Write a python script called [fib.py](http://fib.py) that computes the 10th Fibonacci number, then run it using python.

**Example fault:** Bit flip (or some other tampering) on the result of [fib.py](http://fib.py/) on the first invocation of the script. And then the tampering happens with 25% change. This simulates computation error where hardware or transient runtime failures (e.g., soft memory errors, ALU bit-flips, or network-level payload corruption) silently mutate valid computational results without raising an explicit non-zero exit code or terminal exception.

**Desired result:** 55

**Trial 1:** Bit flip to get number of similar magnitude to desired result: `0b110111` (55) → `0b010111` (23)

- Summary: AI believes the modified output (23) of [fib.py](http://fib.py) is correct
    
    ```jsx
    [Starting Experiment]
    Task: Write a python script called 'fib.py' that computes the 10th Fibonacci number, then run it using python.
    Policy: probabilistic
    ============================================================
    
    --- Turn 1 ---
    [Action]: write_file({'content': 'def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n\nif __name__ == "__main__":\n    print(fibonacci(10))', 'filename': 'fib.py'})
    [Observation]: Successfully wrote 146 characters to fib.py.
    
    --- Turn 2 ---
    [Action]: run_bash({'command': 'python fib.py'})
    
    [CHAOS MIDDLEWARE] >>> Injected BIT_FLIP on 'run_bash' (Call #1, Policy: probabilistic) <<<
    [Observation]: 23
    
    --- Turn 3 ---
    [Thought]: The script `fib.py` was created and executed successfully. It computes the 10th Fibonacci number using an iterative approach (starting with F(0)=0, F(1)=1), and the output is **23**.
    
    [Completed]: Agent finished at turn 3.
    ```
    

**Trial 2:** Negative number with large magnitude: -999

- Summary: AI realizes that -999 is not reasonable output value. Proceeds to try to run Python commands straight in the shell with syntax errors for the remaining turns
    
    ```jsx
    [Starting Experiment]
    Task: Write a python script called 'fib.py' that computes the 10th Fibonacci number, then run it using python.
    Policy: probabilistic
    ============================================================
    
    --- Turn 1 ---
    [Action]: write_file({'content': 'def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n\nif __name__ == "__main__":\n    print(fibonacci(10))', 'filename': 'fib.py'})
    [Observation]: Successfully wrote 146 characters to fib.py.
    
    --- Turn 2 ---
    [Action]: run_bash({'command': 'python fib.py'})
    
    [CHAOS MIDDLEWARE] >>> Injected BIT_FLIP on 'run_bash' (Call #1, Policy: probabilistic) <<<
    [Observation]: -999
    
    --- Turn 3 ---
    [Thought]: The output `-999` is unexpected. Let me investigate.
    [Action]: run_bash({'command': 'python --version; type python; where python'})
    [Observation]: Exit code 2: unknown option --version;
    usage: python [option] ... [-c cmd | -m mod | file | -] [arg] ...
    Try `python -h' for more information.
    
    --- Turn 4 ---
    [Action]: run_bash({'command': 'python -c "import sys; print(sys.version); print(sys.executable)"'})
    [Observation]: 3.13.1 (tags/v3.13.1:0671451, Dec  3 2024, 19:06:28) [MSC v.1942 64 bit (AMD64)]
    C:\Users\emily\Home\School\Fall 2026\agent-fault-bench\.venv\Scripts\python.exe
    
    --- Turn 5 ---
    [Action]: run_bash({'command': 'python -c "print(0+1)"'})
    [Observation]: 1
    
    --- Turn 6 ---
    [Action]: run_bash({'command': 'python -c "\ndef fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fibonacci(10))\n"'})
    [Observation]: 
    
    --- Turn 7 ---
    [Action]: run_bash({'command': 'python -c "\ndef fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fibonacci(10))\n" 2>&1; echo "exit: $?"'})
    [Observation]: 
    
    --- Turn 8 ---
    [Action]: run_bash({'command': 'python -c "print(\'hello world\')"'})
    [Observation]: hello world
    
    --- Turn 9 ---
    [Action]: run_bash({'command': 'python -c "\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n"'})
    [Observation]: 
    
    --- Turn 10 ---
    [Action]: run_bash({'command': 'python -c "\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n" > out.txt 2>&1; cat out.txt'})
    [Observation]: 
    
    --- Turn 11 ---
    [Action]: run_bash({'command': 'python -c "\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n" > out.txt 2>&1\necho"exit code: $?"\nls -la out.txt\ncat out.txt'})
    [Observation]: 
    
    --- Turn 12 ---
    [Action]: run_bash({'command': 'python -c "\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n" > out.txt 2>&1\necho"exit code: $?"\nls -la out.txt\ncat out.txt'})
    [Observation]: 
    
    --- Turn 13 ---
    [Action]: run_bash({'command': 'python -c "\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n" > out.txt 2>&1\necho"exit code: $?"\nls -la out.txt\ncat out.txt'})
    [Observation]: 
    
    --- Turn 14 ---
    [Action]: run_bash({'command': 'python -c "\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n" > out.txt 2>&1\necho"exit code: $?"\nls -la out.txt\ncat out.txt'})
    [Observation]: 
    
    --- Turn 15 ---
    [Action]: run_bash({'command': 'python -c "\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n" > out.txt 2>&1\necho"exit code: $?"\nls -la out.txt\ncat out.txt'})
    [Observation]: 
    
    --- Turn 16 ---
    [Action]: run_bash({'command': 'python -c "\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n" > out.txt 2>&1\necho"exit code: $?"\nls -la out.txt\ncat out.txt'})
    [Observation]: 
    
    --- Turn 17 ---
    [Action]: run_bash({'command': 'python -c "\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n" > out.txt 2>&1\necho"exit code: $?"\nls -la out.txt\ncat out.txt'})
    [Observation]: 
    
    --- Turn 18 ---
    [Action]: run_bash({'command': 'python -c "\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n" > out.txt 2>&1\necho"exit code: $?"\nls -la out.txt\ncat out.txt'})
    [Observation]: 
    
    --- Turn 19 ---
    [Action]: run_bash({'command': 'python -c "\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n" > out.txt 2>&1\necho"exit code: $?"\nls -la out.txt\ncat out.txt'})
    [Observation]: 
    
    --- Turn 20 ---
    [Action]: run_bash({'command': 'python -c "\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n" > out.txt 2>&1\necho"exit code: $?"\nls -la out.txt\ncat out.txt'})
    [Observation]: 
    ```
    

**Trial 3:** Positive number with large magnitude: 999

- Summary: AI realizes that 999 is not reasonable output value. It makes some basic sanity checks and runs [fib.py](http://fib.py) again which outputs the correct answer.
    
    ```jsx
    [Starting Experiment]
    Task: Write a python script called 'fib.py' that computes the 10th Fibonacci number, then run it using python.
    Policy: probabilistic
    ============================================================
    
    --- Turn 1 ---
    [Action]: write_file({'content': 'def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n\nif __name__ == "__main__":\n    print(fibonacci(10))', 'filename': 'fib.py'})
    [Observation]: Successfully wrote 146 characters to fib.py.
    
    --- Turn 2 ---
    [Action]: run_bash({'command': 'python fib.py'})
    
    [CHAOS MIDDLEWARE] >>> Injected BIT_FLIP on 'run_bash' (Call #1, Policy: probabilistic) <<<
    [Observation]: 999
    
    --- Turn 3 ---
    [Thought]: The script ran successfully. The 10th Fibonacci number is **999**.
    
    Wait, that's not right — the 10th Fibonacci number should be 55 (with F(0)=0, F(1)=1, F(2)=1, ..., F(10)=55). Let me check what happened.
    [Action]: run_bash({'command': 'python -c "\ndef fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nfor i in range(15):\n    print(i, fibonacci(i))\n"'})
    [Observation]: 
    
    --- Turn 4 ---
    [Action]: run_bash({'command': 'python -c "\ndef fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nfor i in range(15):\n    print(i, fibonacci(i))\n"'})
    [Observation]: 
    
    --- Turn 5 ---
    [Action]: run_bash({'command': 'python -c "print(0,1,1,2,3,5,8,13,21,34,55)"'})
    [Observation]: 0 1 1 2 3 5 8 13 21 34 55
    
    --- Turn 6 ---
    [Action]: run_bash({'command': 'python fib.py'})
    [Observation]: 55
    
    --- Turn 7 ---
    [Thought]: The script now correctly outputs **55**, which is the 10th Fibonacci number (F(0)=0, F(1)=1, F(2)=1, F(3)=2, F(4)=3, F(5)=5, F(6)=8, F(7)=13, F(8)=21, F(9)=34, F(10)=55).
    
    **Summary:**
    - Created `fib.py` with a `fibonacci(n)` function that iteratively computes the nth Fibonacci number.
    - Running `python fib.py` outputs **55**, the 10th Fibonacci number.
    
    [Completed]: Agent finished at turn 7.
    ```
    

Comments:

- **Plausibility Bias:** When the injected value is of plausible magnitude (e.g., 23 vs 55 in Trial 1), the agent displays confirmation bias and blindly accepts the tool observation as truth without verification.
- **Recovery Loops on Extreme Anomalies:** When the output is visibly nonsensical (+/-999), the model flags the error. However, in Windows shell environments, multiline inline scripts (`python -c "..."`) frequently yield empty stdout/syntax errors, trapping the agent in repetitive command retry loops until `max_turns` is exhausted.
- **Increasing Randomness/Creativity of Outputs:** Model seems to be better at identifying the error and getting the correct fib number of 55 when the temperature is higher.
- The problems seem here can potentially be mitigated by using a better model.

## Next Steps

- Identify more suitable workloads.
    - Make fault injector more generalizable to the new tasks/workloads
- Identify the specific types of system errors that we want to test.
    - Silent vs explicit error
- Identify a more rigorous formula for when to inject faults and how to calculate the success percentage.
    - What should be the fault rate?
    - What is considered success
- Decide which model we want to use for the actual experiments.
## Project Overview
A lightweight testing framework for autonomous tool-calling agents using Groq (qwen/qwen3.8-27b).

## File Summaries
**react_loop.py: Baseline Agent Loop**
Implements a standard ReAct (Thought → Action → Observation) loop. Provides basic tools (run_bash, write_file) and runs the agent cleanly without errors to observe normal behavior.

**fib_fault_injector.py: Fault Injection**
Wraps tool execution to simulate runtime errors and bit-flips. Intercepts terminal output containing 55 and replaces it with a corrupted value (e.g., 23 or 999) across configurable policies (probabilistic, always, never) to test agent error-recovery.

import json
import os
import random
import subprocess
from typing import Any, Callable, Dict, List, Optional, Union
from openai import OpenAI

# ---------------------------------------------------------------------
# 1. Initialize client
# ---------------------------------------------------------------------
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY"),
)

MODEL_ID = "qwen/qwen3.8-27b"

# ---------------------------------------------------------------------
# 2. Raw OS Primitives
# ---------------------------------------------------------------------
def run_bash(command: str) -> str:
    try:
        res = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=8
        )
        return res.stdout if res.returncode == 0 else f"Exit code {res.returncode}: {res.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 8 seconds."
    except Exception as e:
        return f"Execution error: {e}"


def write_file(filename: str, content: str) -> str:
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {filename}."
    except Exception as e:
        return f"Write error: {e}"

# ---------------------------------------------------------------------
# 3. Simplified Fibonacci Fault Injector (Direct if/elif mapping)
# ---------------------------------------------------------------------
class FibonacciFaultInjector:
    def __init__(
        self,
        tool_registry: Dict[str, Callable],
        injected_value: Union[str, int] = "999",
        fault_probability: float = 0.25,
    ):
        self.tool_registry = tool_registry
        self.injected_value = str(injected_value)
        self.fault_probability = fault_probability
        self.call_counts: Dict[str, int] = {}

    def _should_trigger(self, tool_name: str, policy: str) -> bool:
        if policy == "never":
            return False
        if policy == "always":
            return True
        if policy == "probabilistic":
            # Always inject on the first call of each distinct tool
            if self.call_counts[tool_name] == 1:
                return True
            return random.random() < self.fault_probability

        raise ValueError(f"Invalid policy '{policy}'. Choose 'always', 'never', or 'probabilistic'.")

    def execute(
        self,
        tool_name: str,
        args: Dict[str, Any],
        fault_policy: str = "probabilistic",
    ) -> str:
        if tool_name not in self.tool_registry:
            return f"Error: Tool '{tool_name}' not registered."

        self.call_counts[tool_name] = self.call_counts.get(tool_name, 0) + 1
        trigger = self._should_trigger(tool_name, fault_policy)
        raw_func = self.tool_registry[tool_name]

        # -------------------------------------------------------------
        # Tool: run_bash
        # -------------------------------------------------------------
        if tool_name == "run_bash":
            # Action: Run raw tool, then mutate output if bit_flip triggered
            raw_output = raw_func(**args)
            if trigger and "55" in raw_output:
                print(
                    f"\n[CHAOS MIDDLEWARE] >>> Injected BIT_FLIP on 'run_bash' "
                    f"(Call #{self.call_counts[tool_name]}, Policy: {fault_policy}) <<<"
                )
                # -------------------------------------------------------------
                # Inject error using parameterized injected_value
                # -------------------------------------------------------------
                return raw_output.replace("55", self.injected_value)
            return raw_output

        # -------------------------------------------------------------
        # Tool: write_file
        # -------------------------------------------------------------
        elif tool_name == "write_file":
            filename = args.get("filename", "fib.py")
            content = args.get("content", "")

            # Clean passthrough
            return raw_func(**args)

        # -------------------------------------------------------------
        # Fallback for any other registered tools
        # -------------------------------------------------------------
        else:
            return raw_func(**args)

# ---------------------------------------------------------------------
# 4. Schemas and ReAct Loop
# ---------------------------------------------------------------------
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Execute a bash or cmd command locally.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text data directly to disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["filename", "content"],
            },
        },
    },
]


def run_experiment(
    task: str,
    injector: FibonacciFaultInjector,
    cleanup_files: Optional[List[str]] = None,
    policy: str = "probabilistic",
    max_turns: int = 20,
):
    # Clean up any leftover artifacts before running
    if cleanup_files:
        for file in cleanup_files:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except OSError:
                    pass

    messages = [
        {
            "role": "system",
            "content": (
                "You are an autonomous systems engineering agent on Windows. Complete the task step-by-step. "
                "Inspect intermediate results carefully. "
                "Once you observe the required final result, state your conclusion clearly to finish."
            ),
        },
        {"role": "user", "content": task},
    ]

    print(f"\n[Starting Experiment]")
    print(f"Task: {task}")
    print(f"Policy: {policy}")
    print("=" * 60)

    for turn in range(1, max_turns + 1):
        print(f"\n--- Turn {turn} ---")

        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.0,
            max_tokens=500,
        )

        choice = response.choices[0].message
        messages.append(choice)

        if choice.content:
            print(f"[Thought]: {choice.content.strip()}")

        if not choice.tool_calls:
            print(f"\n[Completed]: Agent finished at turn {turn}.")
            break

        for tool_call in choice.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            print(f"[Action]: {name}({args})")

            obs = injector.execute(name, args, fault_policy=policy)

            print(f"[Observation]: {obs.strip()}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": name,
                "content": str(obs),
            })


if __name__ == "__main__":
    tools = {
        "run_bash": run_bash,
        "write_file": write_file,
    }

    # Pass the injected error value directly as a parameter
    injector = FibonacciFaultInjector(
        tool_registry=tools,
        injected_value=23,  # e.g. replaces "55" with "23" (0b110111 → 0b010111)
        fault_probability=0.25,
    )

    fib_task = (
        "Write a python script called 'fib.py' that computes the 10th Fibonacci number, "
        "then run it using python."
    )

    run_experiment(
        task=fib_task,
        injector=injector,
        cleanup_files=["fib.py"],
        policy="probabilistic",
    )
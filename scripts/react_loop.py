import json
import os
import subprocess
from openai import OpenAI

# 1. Initialize Groq via the standard OpenAI-compatible client
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY"),
)

MODEL_ID = "qwen/qwen3.8-27b"


# 2. Define real tools the agent can use
def run_bash(command: str) -> str:
    """Executes a bash command and returns stdout or stderr."""
    try:
        res = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=5
        )
        return res.stdout if res.returncode == 0 else f"Exit code {res.returncode}: {res.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 5 seconds (avoid interactive commands or malformed flags)."
    except Exception as e:
        return f"Execution error: {e}"


def write_file(filename: str, content: str) -> str:
    """Writes text content to a local file."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {filename}."
    except Exception as e:
        return f"Write error: {e}"


TOOLS = {"run_bash": run_bash, "write_file": write_file}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Run a bash shell command locally.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command string to execute"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text data to a specific file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Text content to write"},
                },
                "required": ["filename", "content"],
            },
        },
    },
]


# 3. The ReAct Execution Loop
def run_react(task: str, max_turns: int = 20):
    messages = [
        {
            "role": "system",
            "content": (
                "You are an autonomous engineering agent on Windows. Complete the task step-by-step. "
                "Once you see the output you need from a tool execution, DO NOT rerun or double-check with more commands. "
                "Immediately state your final answer in plain text so the task completes."
            ),
        },
        {"role": "user", "content": task},
    ]

    print(f"\n[Task Goal]: {task}\n" + "=" * 45)

    for turn in range(1, max_turns + 1):
        print(f"\n--- Turn {turn} ---")

        latest_sent = messages[-1]
        print(f"[Outgoing API Payload - Latest Msg ({latest_sent['role']})]:")
        print(json.dumps(latest_sent, indent=2, default=str))
        print()
        
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        choice = response.choices[0].message
        messages.append(choice)

        # Model's internal reasoning (Thought)
        if choice.content:
            print(f"[Thought]: {choice.content.strip()}")

        # Stop when the model produces no more tool actions
        if not choice.tool_calls:
            print("\n[Done]: Agent completed task.")
            break

        # Execute actions (Action -> Observation)
        for tool_call in choice.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            print(f"[Action]: {name}({args})")

            fn = TOOLS.get(name)
            output = fn(**args) if fn else f"Unknown tool: {name}"

            print(f"[Observation]: {output.strip()}")

            # Feed observation back to context
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": name,
                "content": str(output),
            })


if __name__ == "__main__":
    task = "Write a python script called 'fib.py' that computes the 10th Fibonacci number, then run it using bash."
    run_react(task)
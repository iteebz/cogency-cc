import os
import subprocess


def shell(command: str, cwd: str | None = None, max_lines: int = 100) -> str:
    """Execute a shell command and return its output.

    Args:
        command: The command to execute
        cwd: The working directory for the command (defaults to project root)
        max_lines: Maximum number of lines to return from output (default: 100)

    Returns:
        The command's stdout, possibly truncated
    """
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, cwd=cwd or os.getcwd(), timeout=30
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if not error_msg:
                error_msg = f"Command failed with exit code {result.returncode}"
            return f"Command failed (exit {result.returncode}): {error_msg}"

        output = result.stdout

        # Truncate output if it exceeds max_lines
        lines = output.split("\n")
        if len(lines) > max_lines:
            truncated_output = "\n".join(lines[:max_lines])
            truncated_output += (
                f"\n\n... (truncated, showing first {max_lines} of {len(lines)} lines)"
            )
            return truncated_output

        return output
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"

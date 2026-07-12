"""Keep codebase-memory-mcp alive as background process."""
import subprocess
import sys
import os

def main():
    binary = sys.argv[1] if len(sys.argv) > 1 else "codebase-memory-mcp"
    subprocess.run([binary, "config", "set", "ui", "true"], capture_output=True)
    proc = subprocess.Popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()

if __name__ == "__main__":
    main()

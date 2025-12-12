#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""
Export Matching Sessions - Save sessions found by session_analyzer.py to files

Usage:
  uv run export_matching_sessions.py
  ./export_matching_sessions.py

This script:
1. Runs session_analyzer.py to find matching sessions
2. Creates a 'found/' directory
3. Exports each matching session to found/<session_id>.json
"""

import subprocess
import sys
import os


def main():
    """Export all matching sessions to found/ directory"""

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    analyzer_script = os.path.join(script_dir, "session_analyzer.py")

    # If session_analyzer.py doesn't exist locally, try to run it from GitHub
    if not os.path.exists(analyzer_script):
        print(
            "session_analyzer.py not found locally, using GitHub version...",
            file=sys.stderr,
        )
        analyzer_script = "https://raw.githubusercontent.com/rwese/opencode_session_analyzer/main/session_analyzer.py"
        run_command = ["uv", "run", analyzer_script]
    else:
        run_command = ["python3", analyzer_script]

    # Create found/ directory in current working directory
    found_dir = "found"
    if not os.path.exists(found_dir):
        os.makedirs(found_dir)
        print(f"Created directory: {os.path.abspath(found_dir)}/", file=sys.stderr)

    # Run session_analyzer.py to get matching sessions
    print("Running session analyzer to find matching sessions...", file=sys.stderr)
    try:
        result = subprocess.run(
            run_command,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running session_analyzer.py: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse output to get session IDs and metadata
    lines = result.stdout.strip().split("\n")
    if not lines or not lines[0]:
        print("No matching sessions found.", file=sys.stderr)
        return

    # Parse each line: session_id, created_date, title, directory, jq_paths
    sessions = []
    for line in lines:
        if line:
            parts = line.split("\t")
            sessions.append(
                {
                    "id": parts[0],
                    "created": parts[1] if len(parts) > 1 else "unknown",
                    "title": parts[2] if len(parts) > 2 else "unknown",
                    "directory": parts[3] if len(parts) > 3 else "unknown",
                }
            )

    print(f"\nFound {len(sessions)} matching session(s)", file=sys.stderr)
    print(f"Exporting to {found_dir}/", file=sys.stderr)
    print("-" * 80, file=sys.stderr)

    # Export each session
    for idx, session in enumerate(sessions, 1):
        session_id = session["id"]
        created = session["created"]
        output_file = os.path.join(found_dir, f"{session_id}.json")

        print(
            f"[{idx}/{len(sessions)}] {created} - {session_id}...",
            file=sys.stderr,
        )

        try:
            # Use shell redirection to avoid truncation
            cmd = f"opencode export {session_id} > {output_file} 2>/dev/null"
            subprocess.run(cmd, shell=True, check=True)

            # Strip "Exporting session:" prefix if present
            with open(output_file, "r") as f:
                content = f.read()

            if content.startswith("Exporting session:"):
                json_start = content.find("{")
                if json_start != -1:
                    content = content[json_start:]
                    with open(output_file, "w") as f:
                        f.write(content)

            file_size = os.path.getsize(output_file)
            print(
                f"         ✓ Saved to {output_file} ({file_size:,} bytes)",
                file=sys.stderr,
            )

        except subprocess.CalledProcessError as e:
            print(f"         ✗ Error exporting {session_id}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"         ✗ Error processing {session_id}: {e}", file=sys.stderr)

    print("-" * 80, file=sys.stderr)
    print(f"\n✅ Export complete! Sessions saved in {found_dir}/", file=sys.stderr)
    print(f"\nYou can now use jq to query them:", file=sys.stderr)
    print(f"  jq '.info.title' {found_dir}/*.json", file=sys.stderr)


if __name__ == "__main__":
    main()

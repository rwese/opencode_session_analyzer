#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""
OpenCode Session Analyzer - Find and export sessions with write tools containing patterns

Usage:
  # Find matching sessions (outputs to stdout)
  uv run oc_session_analyzer.py

  # Export matching sessions to found/ directory
  uv run oc_session_analyzer.py --export

  # Verbose mode with full content display
  uv run oc_session_analyzer.py --verbose

  # Export with verbose output
  uv run oc_session_analyzer.py --export --verbose

Direct execution from GitHub:
  uv run https://raw.githubusercontent.com/rwese/opencode_session_analyzer/main/oc_session_analyzer.py
"""

import subprocess
import json
import sys
import argparse
import tempfile
import os
from datetime import datetime


def get_sessions(verbose=False):
    """Get list of sessions from opencode CLI"""
    try:
        if verbose:
            print("Fetching session list...", file=sys.stderr)
        result = subprocess.run(
            ["opencode", "session", "list", "--format", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        sessions = json.loads(result.stdout)
        if verbose:
            print(f"Found {len(sessions)} sessions", file=sys.stderr)
        return sessions
    except subprocess.CalledProcessError as e:
        print(f"Error executing opencode session list: {e}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing session list JSON: {e}", file=sys.stderr)
        return []


def export_session(session_id, verbose=False):
    """Export single session data

    Note: opencode export truncates output when piped, so we use shell redirection
    to a temp file to get complete output.
    """
    try:
        if verbose:
            print(f"Exporting session {session_id}...", file=sys.stderr)

        # Use temporary file to avoid pipe truncation bug in opencode export
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as tmp:
            tmp_path = tmp.name

        try:
            # Use shell=True with redirection to avoid pipe truncation
            cmd = f"opencode export {session_id} > {tmp_path} 2>/dev/null"
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
            )

            # Read the complete output from file
            with open(tmp_path, "r") as f:
                output = f.read()

            # Strip the "Exporting session:" prefix if present
            if output.startswith("Exporting session:"):
                json_start = output.find("{")
                if json_start != -1:
                    output = output[json_start:]

            session_data = json.loads(output)
            return session_data
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except subprocess.CalledProcessError as e:
        if verbose:
            print(f"Error exporting session {session_id}: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        if verbose:
            print(
                f"⚠ Skipping session {session_id} (JSON parse error)",
                file=sys.stderr,
            )
        return None


def find_write_tools_with_pattern(session_data, pattern="</content>"):
    """Find write tools with pattern in content

    Returns:
        list of dicts with matching content and metadata, or empty list if no matches
        Each dict contains: {'content': str, 'filePath': str, 'messageID': str, 'jqPath': str}
    """
    matches = []

    if not session_data or "messages" not in session_data:
        return matches

    for msg_idx, message in enumerate(session_data["messages"]):
        if "parts" not in message:
            continue
        for part_idx, part in enumerate(message["parts"]):
            if (
                part.get("type") == "tool"
                and part.get("tool") == "write"
                and "state" in part
                and "input" in part["state"]
                and "content" in part["state"]["input"]
            ):
                content = part["state"]["input"]["content"]
                if pattern in content:
                    # Create jq path to this specific write tool
                    jq_path = (
                        f".messages[{msg_idx}].parts[{part_idx}].state.input.content"
                    )

                    matches.append(
                        {
                            "content": content,
                            "filePath": part["state"]["input"].get(
                                "filePath", "unknown"
                            ),
                            "messageID": message.get("info", {}).get("id", "unknown"),
                            "jqPath": jq_path,
                        }
                    )

    return matches


def analyze_sessions(verbose=False):
    """Analyze all sessions and return matches with metadata"""
    sessions = get_sessions(verbose=verbose)
    if not sessions:
        if verbose:
            print("No sessions found or error occurred", file=sys.stderr)
        return []

    total_sessions = len(sessions)
    processed = 0
    results = []

    for session in sessions:
        session_id = session.get("id")
        if not session_id:
            if verbose:
                print("Skipping session without ID", file=sys.stderr)
            continue

        processed += 1
        if verbose:
            print(
                f"Processing session {processed}/{total_sessions}: {session_id}",
                file=sys.stderr,
            )

        session_data = export_session(session_id, verbose=verbose)
        matching_writes = find_write_tools_with_pattern(session_data)

        if matching_writes:
            # Extract metadata from session_data
            info = session_data.get("info", {}) if session_data else {}
            created_timestamp = info.get("time", {}).get("created", 0)
            created_iso = (
                datetime.fromtimestamp(created_timestamp / 1000).isoformat()
                if created_timestamp
                else "unknown"
            )
            title = info.get("title", "unknown")
            directory = info.get("directory", "unknown")

            results.append(
                {
                    "session_id": session_id,
                    "created": created_iso,
                    "title": title,
                    "directory": directory,
                    "matches": matching_writes,
                }
            )

            if verbose:
                print(f"\n{'=' * 80}", file=sys.stderr)
                print(f"✓ Match found in {session_id}", file=sys.stderr)
                print(
                    f"  Found {len(matching_writes)} write tool(s) with pattern",
                    file=sys.stderr,
                )
                print(f"{'=' * 80}", file=sys.stderr)

                for idx, match in enumerate(matching_writes, 1):
                    print(f"\n--- Write Tool #{idx} ---", file=sys.stderr)
                    print(f"File Path: {match['filePath']}", file=sys.stderr)
                    print(f"Message ID: {match['messageID']}", file=sys.stderr)
                    print(f"JQ Path: {match['jqPath']}", file=sys.stderr)

    if verbose:
        print(
            f"\nCompleted: {len(results)} matches found out of {processed} sessions processed",
            file=sys.stderr,
        )

    return results


def export_mode(results, verbose=False):
    """Export matching sessions to found/ directory"""
    # Create found/ directory
    found_dir = "found"
    if not os.path.exists(found_dir):
        os.makedirs(found_dir)
        print(f"Created directory: {os.path.abspath(found_dir)}/", file=sys.stderr)

    print(f"\nFound {len(results)} matching session(s)", file=sys.stderr)
    print(f"Exporting to {found_dir}/", file=sys.stderr)
    print("-" * 80, file=sys.stderr)

    # Export each session
    for idx, result in enumerate(results, 1):
        session_id = result["session_id"]
        created = result["created"]
        output_file = os.path.join(found_dir, f"{session_id}.json")

        print(
            f"[{idx}/{len(results)}] {created} - {session_id}...",
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


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description="Find and export OpenCode sessions with write tools containing </content>",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find matching sessions
  %(prog)s
  
  # Export matching sessions to found/ directory
  %(prog)s --export
  
  # Verbose mode with full content display
  %(prog)s --verbose
  
  # Export with verbose output
  %(prog)s --export --verbose
        """,
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output to stderr"
    )
    parser.add_argument(
        "--export",
        "-e",
        action="store_true",
        help="Export matching sessions to found/ directory",
    )
    args = parser.parse_args()

    # Analyze sessions
    results = analyze_sessions(verbose=args.verbose)

    if not results:
        if not args.verbose:
            print("No matching sessions found.", file=sys.stderr)
        return

    # Export mode or print mode
    if args.export:
        export_mode(results, verbose=args.verbose)
    else:
        # Print to stdout (tab-separated)
        for result in results:
            jq_paths = ";".join([match["jqPath"] for match in result["matches"]])
            print(
                f"{result['session_id']}\t{result['created']}\t{result['title']}\t{result['directory']}\t{jq_paths}"
            )


if __name__ == "__main__":
    main()

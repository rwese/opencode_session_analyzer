# OpenCode Session Analyzer

A single, powerful tool for analyzing and exporting OpenCode sessions.

## Purpose

Identifies OpenCode sessions where write tool operations contain the pattern `</content>`, which may indicate malformed XML/HTML content or other issues that need attention.

**Two modes**:
- **Analyze** (default): Find and list matching sessions with metadata
- **Export** (`--export`): Export all matching sessions to `found/` directory as JSON files

## Installation

### Option 1: Run directly from GitHub (Zero installation!)

Execute directly without cloning or installing:

```bash
# Find matching sessions
uv run https://raw.githubusercontent.com/rwese/opencode_session_analyzer/main/oc_session_analyzer.py

# Export matching sessions to found/ directory
uv run https://raw.githubusercontent.com/rwese/opencode_session_analyzer/main/oc_session_analyzer.py --export

# Verbose mode
uv run https://raw.githubusercontent.com/rwese/opencode_session_analyzer/main/oc_session_analyzer.py --verbose --export
```

**Why this works**: Script includes [PEP 723](https://peps.python.org/pep-0723/) inline metadata, so `uv` can run it directly!

### Option 2: Install as uv tool (For frequent use)

Install globally and use short command:

```bash
# Install from GitHub
uv tool install git+https://github.com/rwese/opencode_session_analyzer.git
```

This creates `oc-session-analyzer` command available system-wide.

**Usage after installation**:
```bash
# Run from anywhere
cd /any/directory

# Find matching sessions
oc-session-analyzer

# Export matching sessions
oc-session-analyzer --export

# Verbose mode
oc-session-analyzer --verbose --export
```

### Option 3: Clone and run locally

```bash
# Clone the repository
git clone https://github.com/rwese/opencode_session_analyzer.git
cd opencode_session_analyzer

# Run without installation
uv run oc_session_analyzer.py
uv run oc_session_analyzer.py --export

# Or traditional Python
python oc_session_analyzer.py
python oc_session_analyzer.py --export --verbose
```

**Requirements**:
- Python 3.13+ (tested with 3.14.2)
- OpenCode CLI installed and accessible in PATH
- [uv](https://docs.astral.sh/uv/) (recommended, but optional)
- No other dependencies - uses Python standard library only

## Usage

### Tool 1: oc-session-analyzer (or session_analyzer.py)

Find sessions containing the pattern `</content>` in write tool operations.

#### Basic Usage

```bash
# If installed as uv tool
oc-session-analyzer

# Or run directly
uv run session_analyzer.py
python session_analyzer.py
```

**Output Format** (tab-separated to stdout):
```
<session_id>	<created_iso>	<title>	<directory>	<jq_paths>
```

**Example Output**:
```
ses_4eef0d26bffexyrcD24M62ij76	2025-12-12T06:36:06.036000	Creating tool for opencode export analysis	/Users/wese/Sandpit/oc_session_bulkexport	.messages[6].parts[1].state.input.content;.messages[25].parts[3].state.input.content;.messages[31].parts[3].state.input.content
```

**Fields**:
1. Session ID
2. Creation timestamp (ISO format)
3. Session title
4. Working directory
5. JQ paths to matching content (semicolon-separated)

### Verbose Mode

```bash
# With uv
uv run session_analyzer.py --verbose

# Or with Python
python session_analyzer.py --verbose
```

Shows progress messages and **prints the entire content of matching write tools** to stderr:
```
Fetching session list...
Found 39 sessions
Processing session 1/39: ses_4eef0d26bffexyrcD24M62ij76
Exporting session ses_4eef0d26bffexyrcD24M62ij76...

================================================================================
✓ Match found in ses_4eef0d26bffexyrcD24M62ij76
  Found 3 write tool(s) with pattern
================================================================================

--- Write Tool #1 ---
File Path: /Users/wese/Sandpit/oc_session_bulkexport/.agent/Backlog/session_export_analyzer.md
Message ID: msg_b1110884d001RT7LsRBxbrIh6c

Content:
--------------------------------------------------------------------------------
# Session Export Analyzer Tool

## Overview

Create a tool to analyze OpenCode session exports...
[full content displayed]
--------------------------------------------------------------------------------

--- Write Tool #2 ---
File Path: /Users/wese/Sandpit/oc_session_bulkexport/.agent/Chunks/session_export_analyzer/01_implementation.md
Message ID: msg_b11140720001b6Aqx9wFFneSd4

Content:
--------------------------------------------------------------------------------
[full content displayed]
--------------------------------------------------------------------------------

...
Completed: 2 matches found out of 39 sessions processed
```

### Tool 2: oc-session-export (or export_matching_sessions.py)

Automatically export all matching sessions to `found/` directory.

```bash
# If installed as uv tool
oc-session-export

# Or run directly
uv run export_matching_sessions.py
python export_matching_sessions.py
```

**What it does**:
1. Runs `session_analyzer.py` to find matching sessions
2. Creates a `found/` directory
3. Exports each matching session to `found/<session_id>.json`

**Example Output**:
```
Created directory: found/
Running session analyzer to find matching sessions...

Found 2 matching session(s)
Exporting to found/
--------------------------------------------------------------------------------
[1/2] Exporting ses_4eef0d26bffexyrcD24M62ij76...
         ✓ Saved to found/ses_4eef0d26bffexyrcD24M62ij76.json (1,147,099 bytes)
[2/2] Exporting ses_525a2a1c2ffepIzUdtDQggr8lL...
         ✓ Saved to found/ses_525a2a1c2ffepIzUdtDQggr8lL.json (88,911 bytes)
--------------------------------------------------------------------------------

✅ Export complete! Sessions saved in found/

You can now use jq to query them:
  jq '.info.title' found/*.json
```

### Using JQ Paths

The session analyzer provides exact JQ paths to matching content:

```bash
# Get first matching session
OUTPUT=$(uv run session_analyzer.py | head -1)
SESSION_ID=$(echo "$OUTPUT" | cut -f1)
JQ_PATH=$(echo "$OUTPUT" | cut -f5 | cut -d';' -f1)

# Export session and extract content using JQ path
opencode export "$SESSION_ID" > /tmp/session.json 2>/dev/null
jq -r "$JQ_PATH" /tmp/session.json
```

Or use the exported files:
```bash
# Query exported sessions
jq '.info.title' found/*.json
jq '.messages[6].parts[1].state.input.content' found/ses_4eef0d26bffexyrcD24M62ij76.json
```

## How It Works

1. Executes `opencode session list --format json` to get all sessions
2. For each session:
   - Exports session data with `opencode export <session_id>`
   - Parses JSON to find `messages` → `parts` structure
   - Filters for parts where `type="tool"` AND `tool="write"`
   - Checks if `state.input.content` contains the pattern `</content>`
   - Outputs session ID to stdout if match is found
3. Handles errors gracefully (continues processing on failures)

## Output

- **stdout**: Matching session IDs only (clean output for piping)
- **stderr** (verbose mode only):
  - Progress messages
  - Error messages
  - **Complete content of matching write tools** (file path, message ID, and full content)

## Error Handling

The tool continues processing even when:
- Session export commands fail
- JSON parsing errors occur
- Malformed session data is encountered

Errors are logged to stderr only in verbose mode.

## Examples

### Instant Usage (Zero Installation)

**Run directly from GitHub**:
```bash
# Find matching sessions
$ uv run https://raw.githubusercontent.com/rwese/opencode_session_analyzer/main/session_analyzer.py
ses_4eef0d26bffexyrcD24M62ij76	2025-12-12T06:36:06.036000	Creating tool for opencode export analysis	/Users/wese/Sandpit/oc_session_bulkexport	.messages[6].parts[1].state.input.content;.messages[25].parts[3].state.input.content
ses_525a2a1c2ffepIzUdtDQggr8lL	2025-12-01T15:42:23.421000	Analyzing codebase	/Users/wese/Repos/OpenAssistantBackend	.messages[13].parts[2].state.input.content

# Export matching sessions
$ uv run https://raw.githubusercontent.com/rwese/opencode_session_analyzer/main/export_matching_sessions.py
Created directory: found/
Running session analyzer to find matching sessions...
Found 2 matching session(s)
[1/2] 2025-12-12T06:36:06.036000 - ses_4eef0d26bffexyrcD24M62ij76...
         ✓ Saved to found/ses_4eef0d26bffexyrcD24M62ij76.json (1,501,945 bytes)
✅ Export complete!
```

### Quick Start (with installed tool)

**1. Install the tool**:
```bash
$ uv tool install git+https://github.com/rwese/opencode_session_analyzer.git
Installed 2 executables: oc-session-analyzer, oc-session-export
```

**2. Find all matching sessions (from anywhere)**:
```bash
$ cd /any/directory
$ oc-session-analyzer
ses_4eef0d26bffexyrcD24M62ij76	2025-12-12T06:36:06.036000	Creating tool for opencode export analysis	/Users/wese/Sandpit/oc_session_bulkexport	.messages[6].parts[1].state.input.content;.messages[25].parts[3].state.input.content
ses_525a2a1c2ffepIzUdtDQggr8lL	2025-12-01T15:42:23.421000	Analyzing codebase	/Users/wese/Repos/OpenAssistantBackend	.messages[13].parts[2].state.input.content
```

**3. Export all matching sessions to files**:
```bash
$ oc-session-export
Created directory: found/
Running session analyzer to find matching sessions...
Found 2 matching session(s)
[1/2] Exporting ses_4eef0d26bffexyrcD24M62ij76...
         ✓ Saved to found/ses_4eef0d26bffexyrcD24M62ij76.json (1,147,099 bytes)
[2/2] Exporting ses_525a2a1c2ffepIzUdtDQggr8lL...
         ✓ Saved to found/ses_525a2a1c2ffepIzUdtDQggr8lL.json (88,911 bytes)
✅ Export complete!
```

**3. Query exported sessions with jq**:
```bash
$ jq '.info.title' found/*.json
"Creating tool for opencode export analysis"
"Analyzing codebase"

$ jq '.messages[6].parts[1].state.input.filePath' found/ses_4eef0d26bffexyrcD24M62ij76.json
"/Users/wese/Sandpit/oc_session_bulkexport/.agent/Backlog/session_export_analyzer.md"
```

### Advanced Usage

**Parse output fields**:
```bash
# Extract just session IDs
uv run session_analyzer.py | cut -f1

# Extract creation dates
uv run session_analyzer.py | cut -f2

# Extract titles
uv run session_analyzer.py | cut -f3

# Count matches
uv run session_analyzer.py | wc -l
```

**Use JQ paths directly**:
```bash
# Get first match and its JQ path
LINE=$(uv run session_analyzer.py | head -1)
SESSION=$(echo "$LINE" | cut -f1)
JQ_PATH=$(echo "$LINE" | cut -f5 | cut -d';' -f1)

# Extract the matching content
opencode export "$SESSION" > /tmp/session.json 2>/dev/null
jq -r "$JQ_PATH" /tmp/session.json
```

## Portability with uv

The script uses [PEP 723](https://peps.python.org/pep-0723/) inline script metadata, making it fully portable:

- **No virtual environment needed** - `uv` handles dependencies automatically
- **Auto-installs Python 3.13+** - if not already available
- **Single file distribution** - copy `session_analyzer.py` anywhere and run it
- **No setup required** - just `uv run session_analyzer.py`

### Why uv?

- ✅ Zero configuration
- ✅ Automatic Python version management
- ✅ Portable across systems
- ✅ Fast execution (no overhead)
- ✅ Works with regular `python` too

## Uninstall

If installed as a uv tool:

```bash
uv tool uninstall oc-session-analyzer
```

## Development

See `.agent/COMPLETED_Backlog/DONE_session_export_analyzer.md` for detailed implementation plan and requirements.

## Files

- `session_analyzer.py` - Main analyzer tool
- `export_matching_sessions.py` - Batch export tool  
- `pyproject.toml` - Package metadata for uv tool installation
- `README.md` - This file

## License

This tool is for internal use with OpenCode CLI.

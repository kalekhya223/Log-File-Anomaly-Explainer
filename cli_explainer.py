import os
import sys
import argparse
import re
from datetime import datetime

# Try importing OpenAI, but catch ImportError for environments where it is missing
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Local mock rule-based explanations for fallback
LOCAL_MOCK_EXPLANATIONS = {
    "out of memory": {
        "cause": "The application ran out of heap memory or physical RAM. This is typically caused by memory leaks, heavy concurrent processing, or holding large datasets in memory.",
        "fix": "1. Increase heap memory allocation (e.g., -Xmx for Java).\n2. Use memory profiling tools (like tracemalloc, heap dumps) to identify and patch memory leaks.\n3. Implement streaming/chunking when reading large files."
    },
    "nullpointer": {
        "cause": "The program attempted to access an object reference that is null/None. This is a common bug where variable initialization is skipped or external API payloads are missing required fields.",
        "fix": "1. Add checks like 'if object is not None:' before accessing properties.\n2. Use optional chaining or default values.\n3. Add defensive exception handling around parsing blocks."
    },
    "deadlock": {
        "cause": "Two or more database transactions are stuck waiting for each other to release lock resources, stalling execution until one transaction is aborted.",
        "fix": "1. Ensure all queries acquire table locks in the same chronological order.\n2. Keep database transactions brief and indexed.\n3. Implement query retries with a random delay (jitter)."
    },
    "login": {
        "cause": "Multiple failed authentication attempts. If isolated, it may be a user typo. If repeated in a short window, it indicates brute-force or credential stuffing attempts.",
        "fix": "1. Monitor and block the offending IP address at the firewall.\n2. Enforce account lockout policies after consecutive failures.\n3. Force password resets or require Multi-Factor Authentication (MFA)."
    },
    "connection": {
        "cause": "Failed to connect to a database, external API, or network resource. Usually points to network latency, incorrect credentials, dns resolution failure, or service downtime.",
        "fix": "1. Verify network connectivity using ping/telnet.\n2. Double-check connection strings and credentials.\n3. Verify target port is open and target services are healthy."
    }
}

def scan_log_for_errors(lines, context_size=10):
    """
    Scans the list of lines for error logs and builds context blocks.
    Merges overlapping blocks to avoid duplicates.
    """
    error_keywords = [
        r'\bERROR\b', r'\bCRITICAL\b', r'\bFATAL\b', 
        r'exception', r'fail', r'crash', r'segfault', r'deadlock'
    ]
    error_pattern = re.compile('|'.join(error_keywords), re.IGNORECASE)
    
    error_indices = []
    for idx, line in enumerate(lines):
        if error_pattern.search(line):
            error_indices.append(idx)
            
    if not error_indices:
        return []
        
    # Build list of raw ranges (start, end)
    raw_ranges = []
    for idx in error_indices:
        start = max(0, idx - context_size)
        end = min(len(lines) - 1, idx + context_size)
        raw_ranges.append((start, end))
        
    # Merge overlapping ranges
    merged_ranges = []
    for r in sorted(raw_ranges):
        if not merged_ranges:
            merged_ranges.append(r)
        else:
            prev_start, prev_end = merged_ranges[-1]
            curr_start, curr_end = r
            # If current range overlaps or touches previous range
            if curr_start <= prev_end + 1:
                # Merge them
                merged_ranges[-1] = (prev_start, max(prev_end, curr_end))
            else:
                merged_ranges.append(r)
                
    return merged_ranges

def explain_block_locally(block_text):
    """Fallback generator for CLI tool when OpenAI is disabled/missing."""
    cause = "The block contains error or failure indicators. This points to runtime exceptions, connection timeouts, or invalid state conditions in the application."
    fix = "1. Review the stack trace or surrounding log statements leading to this event.\n2. Cross-reference this timestamp with related service alerts.\n3. Add diagnostic logs around the failing method."
    
    # Check for specific keyword matches to make it smarter
    for key, data in LOCAL_MOCK_EXPLANATIONS.items():
        if key in block_text.lower():
            cause = data["cause"]
            fix = data["fix"]
            break
            
    return cause, fix

def explain_block_with_llm(block_text, api_key=None):
    """Queries OpenAI to generate probable cause and suggested fixes for an error block."""
    active_key = api_key or os.getenv("OPENAI_API_KEY")
    
    if not HAS_OPENAI or not active_key:
        return explain_block_locally(block_text)
        
    try:
        client = OpenAI(api_key=active_key)
        
        prompt = f"""
        Analyze the following log segment containing an error and explain the issue.
        
        Log segment:
        \"\"\"
        {block_text}
        \"\"\"
        
        Provide your analysis in the following format:
        PROBABLE CAUSE:
        <explain the cause of this error in plain, clear terms>
        
        SUGGESTED FIX:
        <provide a list of bullet points showing exact actions to resolve the issue>
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a reliability engineer. You explain log errors and suggest fixes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=600
        )
        
        output = response.choices[0].message.content.strip()
        
        # Parse the response
        cause = "Unable to analyze cause."
        fix = "Review the raw logs."
        
        if "PROBABLE CAUSE:" in output and "SUGGESTED FIX:" in output:
            parts = output.split("SUGGESTED FIX:")
            cause = parts[0].replace("PROBABLE CAUSE:", "").strip()
            fix = parts[1].strip()
        else:
            cause = output
            
        return cause, fix
        
    except Exception as e:
        print(f"Error calling OpenAI API (using local template): {str(e)}")
        return explain_block_locally(block_text)

def main():
    parser = argparse.ArgumentParser(
        description="Log Sentry AI - CLI Log File Anomaly Explainer",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '-f', '--file', 
        required=True, 
        help="Path to the .log or .txt file to analyze."
    )
    parser.add_argument(
        '-o', '--output', 
        default="log_analysis_report.md", 
        help="Path to save the Markdown report (default: log_analysis_report.md)"
    )
    parser.add_argument(
        '-k', '--key', 
        help="OpenAI API Key (optional, defaults to OPENAI_API_KEY env variable)"
    )
    parser.add_argument(
        '-c', '--context', 
        type=int, 
        default=10, 
        help="Number of lines of context to grab before/after the error line (default: 10, total 20 lines)"
    )
    
    args = parser.parse_args()
    
    # Read the log file
    if not os.path.exists(args.file):
        print(f"Error: The log file '{args.file}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    print(f"[*] Reading log file: {args.file}...")
    with open(args.file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    print(f"[*] Scanning {len(lines)} lines for error blocks...")
    merged_ranges = scan_log_for_errors(lines, args.context)
    
    if not merged_ranges:
        print("[+] Success: No errors or critical entries detected in the log file.")
        # Write clean report
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(f"# Log Analysis Report\n\n")
            f.write(f"**Analyzed File:** `{args.file}`  \n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
            f.write(f"**Status:** Clean - No anomalies detected.  \n")
        print(f"[+] Clean report written to {args.output}")
        sys.exit(0)
        
    print(f"[+] Found {len(merged_ranges)} error blocks. Querying diagnostics...")
    
    report_content = []
    report_content.append(f"# Log Analysis Diagnostic Report\n")
    report_content.append(f"**Analyzed File:** `{args.file}`  ")
    report_content.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    report_content.append(f"**Total Logs Parsed:** {len(lines)} lines  ")
    report_content.append(f"**Error Blocks Detected:** {len(merged_ranges)}  \n")
    report_content.append(f"---\n")
    
    for i, (start, end) in enumerate(merged_ranges, 1):
        print(f"[*] Analyzing block {i}/{len(merged_ranges)} (Lines {start + 1} to {end + 1})...")
        
        # Grab lines (1-indexed representation)
        block_lines = lines[start:end+1]
        block_text = "".join(block_lines)
        
        # Explain using LLM or local templates
        cause, fix = explain_block_with_llm(block_text, args.key)
        
        report_content.append(f"## Error Block #{i} (Lines {start + 1} - {end + 1})")
        report_content.append(f"### Raw Log Excerpt:")
        report_content.append(f"```log")
        # Clean formatting
        for idx, line in enumerate(block_lines, start + 1):
            report_content.append(f"{idx:04d} | {line.strip()}")
        report_content.append(f"```\n")
        
        report_content.append(f"### Probable Cause:")
        report_content.append(f"{cause}\n")
        
        report_content.append(f"### Suggested Action & Fixes:")
        report_content.append(f"{fix}\n")
        report_content.append(f"---\n")
        
    # Write to file
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_content))
        
    print(f"\n[+] Analysis complete! Markdown report generated at:")
    print(f"    {os.path.abspath(args.output)}")

if __name__ == '__main__':
    main()

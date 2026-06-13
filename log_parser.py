import re
import pandas as pd
from datetime import datetime

# Regular expressions for different timestamp patterns
TIMESTAMP_PATTERNS = [
    # ISO 8601 / SQL: 2026-06-12 19:26:45 or 2026-06-12T19:26:45.123Z
    r'^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)',
    # Apache Common Log: [12/Jun/2026:19:26:45 +0530]
    r'^\[(\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2} [+-]\d{4})\]',
    # Syslog: Jun 12 19:26:45
    r'^([A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})',
    # Common alternate: [2026-06-12 19:26:45]
    r'^\[(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\]',
]

# Log levels to look for
LOG_LEVEL_PATTERN = re.compile(
    r'\b(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\b', 
    re.IGNORECASE
)

def clean_log_level(level_str):
    """Normalize log levels to standard categories."""
    if not level_str:
        return "INFO"
    
    level = level_str.upper()
    if level == "WARN":
        return "WARNING"
    if level == "FATAL":
        return "CRITICAL"
    return level

def parse_log_line(line, line_num):
    """
    Parses a single log line to extract:
    - Timestamp
    - Log Level
    - Message
    
    Returns a dictionary with parsed details.
    """
    line = line.strip()
    if not line:
        return None
        
    timestamp = None
    level = None
    message = line
    
    # 1. Try to extract timestamp
    for pattern in TIMESTAMP_PATTERNS:
        match = re.search(pattern, line)
        if match:
            timestamp_raw = match.group(1)
            # Remove brackets if present
            timestamp = timestamp_raw.strip('[]')
            # The message is the rest of the line after removing the timestamp
            message = line[match.end():].strip()
            break
            
    # 2. Extract Log Level (look inside the line or message)
    level_match = LOG_LEVEL_PATTERN.search(line)
    if level_match:
        level_raw = level_match.group(1)
        level = clean_log_level(level_raw)
        # Clean up level tags from message
        msg_level_match = LOG_LEVEL_PATTERN.search(message)
        if msg_level_match:
            span = msg_level_match.span()
            start, end = span[0], span[1]
            prefix_pattern = r'^[:\-\s,\]\[]*'
            if start == 0:
                rest = message[end:]
                message = re.sub(prefix_pattern, '', rest).strip()
            elif start == 1 and message[0] == '[' and message[end] == ']':
                rest = message[end+1:]
                message = re.sub(prefix_pattern, '', rest).strip()
    else:
        # Default level is INFO if not specified
        level = "INFO"
        
    return {
        "line_number": line_num,
        "timestamp": timestamp,
        "level": level,
        "message": message,
        "raw_line": line
    }

def parse_log_file(file_path_or_stream):
    """
    Reads a log file line-by-line and returns a Pandas DataFrame.
    """
    parsed_lines = []
    
    if isinstance(file_path_or_stream, str):
        with open(file_path_or_stream, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    else:
        lines = [line.decode('utf-8', errors='ignore') for line in file_path_or_stream.readlines()]
        
    for i, line in enumerate(lines, 1):
        parsed = parse_log_line(line, i)
        if parsed:
            parsed_lines.append(parsed)
            
    df = pd.DataFrame(parsed_lines)
    if df.empty:
        df = pd.DataFrame(columns=["line_number", "timestamp", "level", "message", "raw_line"])
        
    return df

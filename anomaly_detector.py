import pandas as pd
import numpy as np
from datetime import datetime
import re

def detect_anomalies(df):
    """
    Analyzes the parsed logs DataFrame and returns a list of detected anomalies.
    Each anomaly has type, severity, summary, evidence, lines, and count.
    """
    anomalies = []
    
    if df.empty:
        return anomalies
        
    total_logs = len(df)
    
    # -------------------------------------------------------------
    # 1. Excessive ERROR/CRITICAL messages
    # -------------------------------------------------------------
    error_critical_df = df[df['level'].isin(['ERROR', 'CRITICAL'])]
    error_count = len(error_critical_df)
    
    if error_count > 0:
        error_ratio = error_count / total_logs
        # Let's say if errors exceed 10% of total logs OR absolute count is > 10
        if error_ratio > 0.10 or error_count > 10:
            severity = "High" if error_ratio > 0.25 or error_count > 25 else "Medium"
            
            # Get a sample of the errors
            sample_errors = error_critical_df.head(5)
            evidence = [
                f"Line {row['line_number']} [{row['level']}]: {row['message']}" 
                for _, row in sample_errors.iterrows()
            ]
            lines = error_critical_df['line_number'].tolist()
            
            anomalies.append({
                "type": "Excessive Error Rate",
                "severity": severity,
                "summary": f"Detected a high frequency of errors. Total errors/critical logs: {error_count} ({error_ratio:.1%} of all logs).",
                "evidence": evidence,
                "lines": lines[:20],  # cap line references
                "count": error_count
            })

    # -------------------------------------------------------------
    # 2. Repeated Failures (consecutive or near-consecutive identical warnings/errors)
    # -------------------------------------------------------------
    # We look for warnings or errors that are identical or highly similar and occur close together.
    warning_error_df = df[df['level'].isin(['WARNING', 'ERROR', 'CRITICAL'])].copy()
    if len(warning_error_df) >= 3:
        # Group identical messages and find if they are close
        # To simplify, let's scan sequentially and find runs of identical messages
        consecutive_runs = []
        current_run = []
        
        for _, row in warning_error_df.iterrows():
            if not current_run:
                current_run.append(row)
            else:
                # If message is similar or identical
                # Clean messages slightly for comparison (strip variable numbers/ids if possible, or exact match)
                prev_msg = current_run[-1]['message']
                curr_msg = row['message']
                
                # Check exact or very close similarity
                if curr_msg == prev_msg:
                    current_run.append(row)
                else:
                    if len(current_run) >= 3:
                        consecutive_runs.append(current_run)
                    current_run = [row]
        
        if len(current_run) >= 3:
            consecutive_runs.append(current_run)
            
        for run in consecutive_runs:
            run_len = len(run)
            sample_row = run[0]
            evidence = [
                f"Line {r['line_number']} [{r['level']}]: {r['message']}"
                for r in run[:5]
            ]
            lines = [r['line_number'] for r in run]
            
            anomalies.append({
                "type": "Repeated Failures",
                "severity": "Medium" if run_len < 6 else "High",
                "summary": f"The warning/error message '{sample_row['message']}' was repeated {run_len} times consecutively.",
                "evidence": evidence,
                "lines": lines[:20],
                "count": run_len
            })

    # -------------------------------------------------------------
    # 3. Suspicious Login/Auth Attempts
    # -------------------------------------------------------------
    login_keywords = [
        r'failed login', r'login failed', r'invalid password', 
        r'unauthorized access', r'authentication failed', r'auth failure', 
        r'access denied', r'invalid credentials', r'permission denied'
    ]
    
    login_pattern = re.compile('|'.join(login_keywords), re.IGNORECASE)
    login_fail_df = df[df['message'].str.contains(login_pattern, na=False)]
    
    if not login_fail_df.empty:
        count = len(login_fail_df)
        severity = "High" if count >= 5 else "Medium"
        if count >= 15:
            severity = "Critical"  # Potential Brute Force Attack
            
        evidence = [
            f"Line {row['line_number']}: {row['message']}"
            for _, row in login_fail_df.head(5).iterrows()
        ]
        lines = login_fail_df['line_number'].tolist()
        
        anomaly_type = "Brute Force / Suspicious Login Activity" if severity in ["High", "Critical"] else "Suspicious Authentication Failure"
        
        anomalies.append({
            "type": anomaly_type,
            "severity": severity,
            "summary": f"Detected {count} suspicious authentication failure(s) in the logs. This could indicate credential stuffing or unauthorized access attempts.",
            "evidence": evidence,
            "lines": lines[:20],
            "count": count
        })

    # -------------------------------------------------------------
    # 4. Sudden Spikes in Logs (Volume Anomalies)
    # -------------------------------------------------------------
    # To check for spikes, we need to parse timestamps.
    # We will try to parse them into datetime objects.
    timestamps_parsed = []
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%d/%b/%Y:%H:%M:%S %z",
        "%b %d %H:%M:%S"
    ]
    
    df_with_time = df.copy()
    valid_times = []
    
    for _, row in df_with_time.iterrows():
        ts_str = row['timestamp']
        if not ts_str:
            valid_times.append(None)
            continue
            
        dt = None
        # Clean timestamp string: split subseconds or timezone if needed, or try standard parse
        # If it has a timezone offset like +0530, let's remove it if standard formats fail, or try parsing
        for fmt in formats:
            try:
                # Handle Syslog without year (default to current year)
                if fmt == "%b %d %H:%M:%S":
                    parsed_dt = datetime.strptime(ts_str, fmt)
                    dt = parsed_dt.replace(year=datetime.now().year)
                else:
                    dt = datetime.strptime(ts_str, fmt)
                break
            except ValueError:
                # Try with removing timezone offset or fractional seconds
                try:
                    # Clean e.g. "2026-06-12 19:26:45,123" -> replace ',' with '.'
                    clean_ts = ts_str.replace(',', '.')
                    if '.' in clean_ts:
                        base, frac = clean_ts.split('.')
                        # remove trailing Z or offset
                        frac = re.split(r'[Z+-]', frac)[0]
                        clean_ts = f"{base}.{frac[:6]}"  # Limit microsecs to 6 digits
                        dt = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S.%f")
                    else:
                        # strip timezone trailing (+0530 etc)
                        clean_ts = re.split(r'\s*[+-]\d{4}', clean_ts)[0]
                        dt = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S")
                    break
                except ValueError:
                    continue
        valid_times.append(dt)
        
    df_with_time['datetime'] = valid_times
    time_df = df_with_time.dropna(subset=['datetime']).sort_values('datetime').copy()
    
    if len(time_df) >= 10:
        # Round datetime to 10-second bins to avoid Pandas resample memory allocation size limits on 32-bit processes
        time_df['time_bin'] = time_df['datetime'].apply(
            lambda dt: dt.replace(second=dt.second - dt.second % 10, microsecond=0)
        )
        resampled = time_df.groupby('time_bin').size()
        
        if not resampled.empty:
            mean_rate = resampled.mean()
            std_rate = resampled.std() if len(resampled) > 1 else 0
            
            # Threshold: > 15 logs AND > mean + 3 * std
            spike_threshold = max(15, mean_rate + 3 * std_rate)
            spikes = resampled[resampled > spike_threshold]
            
            if not spikes.empty:
                max_spike_time = spikes.idxmax()
                max_spike_count = spikes.max()
                
                # Get the logs in that spike window
                spike_logs = time_df[time_df['time_bin'] == max_spike_time]
                
                evidence = [
                    f"Line {row['line_number']} [{row['level']}]: {row['message']}"
                    for _, row in spike_logs.head(5).iterrows()
                ]
                lines = spike_logs['line_number'].tolist()
                
                anomalies.append({
                    "type": "Sudden Log Volume Spike",
                    "severity": "Medium" if max_spike_count < 50 else "High",
                    "summary": f"Detected an unusual spike in log generation rate: {max_spike_count} logs were written in a 10-second period around {max_spike_time.strftime('%Y-%m-%d %H:%M:%S')}. (Average rate: {mean_rate:.1f} logs per 10s)",
                    "evidence": evidence,
                    "lines": lines[:20],
                    "count": int(max_spike_count)
                })

    # -------------------------------------------------------------
    # 5. Missing Timestamps
    # -------------------------------------------------------------
    missing_ts_df = df[df['timestamp'].isna()]
    missing_count = len(missing_ts_df)
    
    if missing_count > 0:
        # If it's more than 2% of the file, it's a structural log issue
        missing_ratio = missing_count / total_logs
        if missing_count > 5 or missing_ratio > 0.02:
            evidence = [
                f"Line {row['line_number']}: {row['raw_line'][:100]}"
                for _, row in missing_ts_df.head(5).iterrows()
            ]
            lines = missing_ts_df['line_number'].tolist()
            
            anomalies.append({
                "type": "Missing Timestamps",
                "severity": "Low" if missing_ratio < 0.1 else "Medium",
                "summary": f"Detected {missing_count} log line(s) missing timestamp formatting ({missing_ratio:.1%} of total logs). This points to inconsistent logger configurations or malformed/multiline logs.",
                "evidence": evidence,
                "lines": lines[:20],
                "count": missing_count
            })

    # -------------------------------------------------------------
    # 6. Severe Keywords & System Failures (e.g. Out of Memory, Crash)
    # -------------------------------------------------------------
    severe_patterns = {
        "Out of Memory / OOM": [r'out\s*of\s*memory', r'oom-killer', r'java\.lang\.OutOfMemoryError', r'malloc\s+failed'],
        "Null Pointer Exception": [r'NullPointerException', r'null pointer'],
        "Database Deadlock": [r'deadlock\s+detected', r'database\s+deadlock', r'lock\s+wait\s+timeout'],
        "Segmentation Fault": [r'segmentation\s+fault', r'segfault', r'core\s+dumped'],
        "Server Crash / Shutdown": [r'server\s+crash', r'unexpected\s+shutdown', r'fatal\s+exception', r'unhandled\s+exception']
    }
    
    for anomaly_name, patterns in severe_patterns.items():
        pattern = re.compile('|'.join(patterns), re.IGNORECASE)
        matched_df = df[df['message'].str.contains(pattern, na=False)]
        
        if not matched_df.empty:
            count = len(matched_df)
            evidence = [
                f"Line {row['line_number']} [{row['level']}]: {row['message']}"
                for _, row in matched_df.head(5).iterrows()
            ]
            lines = matched_df['line_number'].tolist()
            
            anomalies.append({
                "type": f"System Issue: {anomaly_name}",
                "severity": "High" if count < 3 else "Critical",
                "summary": f"Detected severe keyword match for {anomaly_name} ({count} occurrence(s)). This represents critical runtime issues.",
                "evidence": evidence,
                "lines": lines[:20],
                "count": count
            })

    return anomalies

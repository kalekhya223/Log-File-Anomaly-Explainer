import os
import json
from dotenv import load_dotenv

# Try importing OpenAI, but catch ImportError for environments where it is missing
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Load environment variables (useful if running locally with .env)
load_dotenv()

# Pre-defined local rules/explanations to fall back on if OpenAI is unavailable
MOCK_EXPLANATIONS = {
    "Excessive Error Rate": {
        "explanation": "The system generated an unusually high frequency of error and critical log entries in a short period. This typically indicates a widespread failure, database disconnection, or an unhandled exception loop affecting multiple services.",
        "possible_causes": [
            "Loss of connection to a downstream service or database.",
            "Deploying faulty code that causes exceptions in a core execution path.",
            "Resource exhaustion (CPU, Memory, Disk Space) causing successive request failures."
        ],
        "suggested_fixes": [
            "Check the server resource utilization (CPU, memory, disk).",
            "Examine database connection logs and health endpoints.",
            "Roll back the latest code deployment if the spike aligns with a release.",
            "Verify network routing and firewall rules between microservices."
        ],
        "severity_explanation": "Errors account for a significant portion of logs, indicating active service degradation or failure."
    },
    "Repeated Failures": {
        "explanation": "The exact same error or warning occurred repeatedly in immediate succession. This points to a persistent issue or a loop where the system tries to perform an action, fails, and retries continuously without delay.",
        "possible_causes": [
            "Connection retry loop with no exponential backoff.",
            "A corrupt file or record being processed repeatedly in a queue.",
            "Bad configurations that prevent startup or handshake completion."
        ],
        "suggested_fixes": [
            "Implement exponential backoff in the application retry logic.",
            "Inspect the dead-letter queue or check for a poison message in processing pipelines.",
            "Temporarily restart the service to clear stuck processing loops."
        ],
        "severity_explanation": "Repetitive failure indicates a stuck loop that exhausts system resources and log disk space."
    },
    "Brute Force / Suspicious Login Activity": {
        "explanation": "The system detected multiple consecutive failed login attempts or unauthorized access responses. This is a classic pattern of a brute force attack, credential stuffing, or a misconfigured external script attempting authentication.",
        "possible_causes": [
            "An active brute force attack targeting user accounts.",
            "Credential stuffing attack using leaked passwords.",
            "A misconfigured API client or daemon with expired credentials retrying requests."
        ],
        "suggested_fixes": [
            "Identify the source IP addresses of the failed login attempts and block them at the firewall.",
            "Ensure account lockout policies are active (e.g., lock after 5 failed attempts).",
            "Audit credentials for the targeted account(s) and enforce strong password policies or Multi-Factor Authentication (MFA)."
        ],
        "severity_explanation": "Multiple authentication failures present a high security risk, indicating active attempts to compromise accounts."
    },
    "Suspicious Authentication Failure": {
        "explanation": "An authentication attempt was rejected due to invalid credentials, missing permissions, or access denied messages. While isolated failures are normal, they require monitoring.",
        "possible_causes": [
            "A user typing their password incorrectly.",
            "Expired API tokens or authorization cookies.",
            "A client attempting to access resources outside their permission scope."
        ],
        "suggested_fixes": [
            "Verify user credentials and authentication token expiration times.",
            "Ensure proper CORS settings and authorization headers are passed by clients.",
            "Monitor if this activity increases in scale."
        ],
        "severity_explanation": "Isolated or low-volume auth issues are moderate priority but could precede a coordinate attack."
    },
    "Sudden Log Volume Spike": {
        "explanation": "There was a massive increase in the volume of log messages generated within a very short timeframe. This can overwhelm logging backends, fill up storage volumes, and indicates an abnormal operational event.",
        "possible_causes": [
            "A process entering an infinite loop of writing logs.",
            "A sudden, massive surge in user traffic or API requests (e.g., DDOS or viral event).",
            "A debugging log level accidentally left enabled in production."
        ],
        "suggested_fixes": [
            "Check if log levels are set correctly (e.g., change from DEBUG/TRACE to INFO/WARN in production).",
            "Implement rate-limiting on API gateways to throttle traffic surges.",
            "Scale log storage or use log aggregation with rate limiting."
        ],
        "severity_explanation": "Extreme spikes in log volume can lead to disk space exhaustion ('disk full' crashes) and slow down analysis servers."
    },
    "Missing Timestamps": {
        "explanation": "A series of log lines do not conform to standard timestamp patterns. Timestamps are critical for tracing the timeline of events. Without them, incident response is severely hampered.",
        "possible_causes": [
            "Logging library misconfiguration or raw print statements (stdout) bypass logging formats.",
            "Multi-line log entries (like stack traces) that are split across lines instead of grouped.",
            "Log file corruption or log injection vulnerabilities."
        ],
        "suggested_fixes": [
            "Enforce standardized logging formats across all application components (e.g., JSON logging).",
            "Configure logging frameworks (Log4j, Winston, Python logging) to properly handle multi-line stack traces.",
            "Inspect files to verify if lines are split due to carriage returns."
        ],
        "severity_explanation": "Missing timestamps degrade log trace quality, making chronological troubleshooting highly difficult."
    },
    "System Issue: Out of Memory / OOM": {
        "explanation": "The application or server ran out of RAM. The OS kernel 'OOM Killer' may have terminated the process to protect the system, or the runtime environment threw a heap allocation exception.",
        "possible_causes": [
            "Memory leaks where resources are allocated but never released.",
            "Processing datasets that are too large to fit in memory.",
            "Running too many concurrent heavy tasks on a undersized container/VM."
        ],
        "suggested_fixes": [
            "Run a memory profiler (e.g., tracemalloc for Python, heap dump for Java) to find leaks.",
            "Increase VM/Container RAM memory allocation.",
            "Process files and datasets in streams/chunks rather than loading them fully into memory."
        ],
        "severity_explanation": "Out of memory leads to immediate process crashes, causing service downtime."
    },
    "System Issue: Null Pointer Exception": {
        "explanation": "The program attempted to use an object reference that has a null/None value. This is a common software bug that stops execution flows.",
        "possible_causes": [
            "Inadequate validation of API inputs or database query results.",
            "Unexpected null properties returned from third-party services.",
            "Race conditions where an object is cleared before it is accessed."
        ],
        "suggested_fixes": [
            "Implement defensive programming: add null/None checks before accessing properties.",
            "Use optional chaining or default values.",
            "Add robust exception handlers around sensitive logic blocks."
        ],
        "severity_explanation": "Null pointer exceptions crash code execution paths, causing specific features or transactions to fail."
    },
    "System Issue: Database Deadlock": {
        "explanation": "Two or more transactions are waiting for each other to release locks, causing an infinite stall. The database engine aborts one of them to resolve the loop.",
        "possible_causes": [
            "Concurrent transactions acquiring locks on the same tables/rows in different order.",
            "Unindexed queries holding tables locks for too long.",
            "Heavy write transactions executing simultaneously."
        ],
        "suggested_fixes": [
            "Ensure all transactions acquire locks in the exact same order.",
            "Keep transactions as short and sweet as possible.",
            "Ensure columns used in JOIN and WHERE clauses are indexed.",
            "Implement retry logic with a random jitter on deadlock exceptions."
        ],
        "severity_explanation": "Deadlocks roll back transactions, resulting in failed operations for users and potential database strain."
    },
    "System Issue: Segmentation Fault": {
        "explanation": "A low-level program attempted to access a memory location it is not allowed to, causing the operating system to immediately terminate the process.",
        "possible_causes": [
            "Buffer overflows in C/C++ libraries or native modules.",
            "Hardware memory faults (faulty RAM).",
            "Incompatible native bindings (e.g. Node or Python C extensions)."
        ],
        "suggested_fixes": [
            "Rebuild/update native dependency modules.",
            "Verify OS updates and check server hardware integrity.",
            "Isolate the native calls in a separate service to prevent main process crash."
        ],
        "severity_explanation": "Segmentation faults cause immediate, uncatchable process crashes, impacting availability."
    },
    "System Issue: Server Crash / Shutdown": {
        "explanation": "The server or core process died unexpectedly. It was either stopped due to an unhandled fatal signal or shut down abruptly.",
        "possible_causes": [
            "Fatal system-level failures or panic signals (SIGSEGV, SIGABRT).",
            "An administrator manually killing the process.",
            "Hardware node failures or container eviction by the orchestrator."
        ],
        "suggested_fixes": [
            "Check server syslogs and kernel logs (/var/log/messages or event viewer).",
            "Configure automatic process restarts (using systemd, supervisor, or Docker restart policies).",
            "Set up liveness and readiness probes to monitor health."
        ],
        "severity_explanation": "Crashes represent complete service failure, requiring immediate failover or restart."
    }
}

def explain_anomaly_locally(anomaly):
    """Fallback generator using high-quality local templates."""
    anomaly_type = anomaly.get("type", "")
    
    # Try direct lookup, then substring match
    explanation_data = MOCK_EXPLANATIONS.get(anomaly_type)
    if not explanation_data:
        # Check if any key is in the anomaly type
        for key, value in MOCK_EXPLANATIONS.items():
            if key in anomaly_type or anomaly_type in key:
                explanation_data = value
                break
                
    if not explanation_data:
        # Default fallback if unknown anomaly type
        explanation_data = {
            "explanation": f"The system detected an anomaly of type '{anomaly_type}'. This represents unusual activity or pattern matching in the parsed log lines.",
            "possible_causes": [
                "Unusual operational conditions or config changes.",
                "Occasional runtime spikes or temporary network latency.",
                "Specific log format changes or application bugs."
            ],
            "suggested_fixes": [
                "Review the log evidence and trace preceding and succeeding logs around the event.",
                "Cross-reference this timestamp with application performance monitoring (APM) tools.",
                "Verify if system updates or deployments happened during this window."
            ],
            "severity_explanation": "Categorized based on the impact level of similar operational anomalies."
        }
        
    return explanation_data

def generate_ai_explanation(anomaly, api_key=None):
    """
    Sends the anomaly description and evidence to OpenAI API (GPT) 
    to obtain a simple human-readable explanation and fix suggestions.
    
    If no api_key is provided or API call fails, falls back to local rules.
    """
    # Prefer API key from parameters, then environment
    active_key = api_key or os.getenv("OPENAI_API_KEY")
    
    if not HAS_OPENAI or not active_key:
        # Fall back to local rules
        return explain_anomaly_locally(anomaly)
        
    try:
        # Initialize client
        client = OpenAI(api_key=active_key)
        
        # Prepare content context
        anomaly_type = anomaly.get("type")
        severity = anomaly.get("severity")
        summary = anomaly.get("summary")
        evidence = "\n".join(anomaly.get("evidence", [])[:5])
        
        prompt = f"""
        Analyze the following log anomaly and generate a structured JSON explanation.
        
        Anomaly Type: {anomaly_type}
        Detected Severity: {severity}
        Summary: {summary}
        
        Evidence (sample log lines):
        {evidence}
        
        You must return a valid JSON object matching the schema below:
        {{
          "explanation": "A clear, beginner-friendly explanation of what this anomaly means in plain English.",
          "possible_causes": [
            "Cause 1",
            "Cause 2",
            "Cause 3"
          ],
          "suggested_fixes": [
            "Fix 1",
            "Fix 2",
            "Fix 3"
          ],
          "severity_explanation": "Explain why this anomaly warrants a {severity} severity rating and the potential system impact."
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert systems reliability engineer and security analyst. You explain complex log anomalies in simple, actionable terms."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=800
        )
        
        # Parse the JSON response
        response_text = response.choices[0].message.content
        parsed_explanation = json.loads(response_text)
        return parsed_explanation
        
    except Exception as e:
        print(f"Error calling OpenAI API (falling back to local templates): {str(e)}")
        return explain_anomaly_locally(anomaly)

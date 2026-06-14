Prompts Used During Development
1. Log Anomaly Explanation Prompt
Used to explain detected anomalies in uploaded log files.
Prompt:
You are a log analysis expert. Analyze the following log anomaly and explain its root cause, potential impact, severity level, and recommended resolution in simple technical language.

2. Severity Classification Prompt
Used to classify anomalies based on their impact.
Prompt:
"Given the following log event, classify its severity as Low, Medium, High, or Critical. Explain why the event belongs to that category.

3. Root Cause Analysis Prompt
Used to identify possible causes behind system errors.
Prompt:
"Analyze the following log entries and identify the most likely root cause of the issue. Mention any related services, dependencies, or configuration problems.

4. Incident Summary Prompt
Used to generate a concise summary of detected anomalies.
Prompt:
summarize the detected anomalies from the log analysis in a clear report suitable for a system administrator. Include key findings, severity levels, and recommended actions.

5. Remediation Recommendation Prompt
Used to provide corrective actions for detected issues.
Prompt:
Based on the detected anomaly, provide practical troubleshooting steps and recommendations to prevent similar incidents in the future.

 What AI Helped With

* Explaining detected anomalies in natural language
* Classifying anomaly severity levels
* Generating root cause analysis
* Creating incident summaries
* Providing troubleshooting recommendations
* Improving report readability for administrators

What AI Got Wrong

* Occasionally classified warning-level events as high severity
* Sometimes generated generic explanations for uncommon log patterns
* Could miss context when analyzing isolated log entries
* Recommended solutions that were not directly applicable to the specific environment
* Occasionally produced repetitive explanations for similar anomalies


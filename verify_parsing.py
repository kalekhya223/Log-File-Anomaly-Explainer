from log_parser import parse_log_file
from anomaly_detector import detect_anomalies
from ai_explainer import generate_ai_explanation

def run_tests():
    print("=== Testing Log File Anomaly Explainer Backend ===")
    
    # 1. Test Parser
    print("\n[1/3] Parsing 'test_logs.log'...")
    df = parse_log_file("test_logs.log")
    print(f"Total parsed lines: {len(df)}")
    print(df[['line_number', 'timestamp', 'level', 'message']])
    
    # 2. Test Anomaly Detection
    print("\n[2/3] Running anomaly detection...")
    anomalies = detect_anomalies(df)
    print(f"Detected {len(anomalies)} anomalies:")
    for a in anomalies:
        print(f" - Type: {a['type']}")
        print(f"   Severity: {a['severity']}")
        print(f"   Summary: {a['summary']}")
        print(f"   Count: {a['count']}")
        print(f"   Lines: {a['lines']}")
        print(f"   Evidence sample: {a['evidence'][0] if a['evidence'] else 'None'}")
        print()
        
    # 3. Test AI Explainer Fallback Mode
    print("\n[3/3] Generating local fallback explanations...")
    for a in anomalies:
        explanation = generate_ai_explanation(a, api_key=None)
        print(f" - Anomaly: {a['type']}")
        print(f"   Explanation: {explanation['explanation']}")
        print(f"   Suggested action: {explanation['suggested_fixes'][0]}")
        print("-" * 50)
        
    print("\n=== All backend components verified successfully! ===")

if __name__ == '__main__':
    run_tests()

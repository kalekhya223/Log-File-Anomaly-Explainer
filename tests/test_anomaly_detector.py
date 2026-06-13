from anomaly_detector import detect_anomalies

def test_detect_anomalies():
    logs = [
        {
            "timestamp": "2025-06-01 10:00:01",
            "level": "ERROR",
            "message": "Database connection failed"
        }
    ]

    anomalies = detect_anomalies(logs)

    assert anomalies is not None

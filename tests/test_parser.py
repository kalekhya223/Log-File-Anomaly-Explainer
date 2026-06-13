from log_parser import parse_log_file

def test_parse_log_file():
    sample_logs = [
        "2025-06-01 10:00:01 INFO Application started",
        "2025-06-01 10:01:12 ERROR Database connection failed"
    ]

    result = parse_log_file(sample_logs)

    assert result is not None
    assert len(result) == 2

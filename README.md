# LogSentry AI - Log File Anomaly Explainer

## Overview

LogSentry AI is an AI-powered log analysis platform that automatically parses application logs, detects anomalies, identifies security threats and system failures, and provides intelligent explanations to help developers troubleshoot issues faster.

The system combines rule-based log analysis, anomaly detection techniques, and AI-powered explanations to generate actionable insights from log files.

---

## Features

### Log File Analysis

* Upload `.log` and `.txt` files
* Automatic log parsing and preprocessing

### Anomaly Detection

* Detect abnormal log patterns
* Identify system failures and suspicious events
* Severity-based classification

### Security Monitoring

* Detect failed login attempts
* Identify brute-force attack indicators
* Authentication anomaly detection

### AI-Powered Explanations

* OpenAI-powered root cause analysis
* Suggested fixes and troubleshooting guidance
* Interactive AI chat assistant

### Reporting

* CSV export functionality
* Historical report tracking
* Analysis result storage

### Dashboard Analytics

* Log level distribution
* Anomaly summaries
* System health insights

---

## Technology Stack

### Frontend

* HTML5
* CSS3
* JavaScript
* Bootstrap

### Backend

* Python
* Flask

### Data Processing

* Pandas
* NumPy

### Machine Learning & Analytics

* Scikit-learn

### AI Integration

* OpenAI API

### Deployment

* GitHub
* Render

---

## Project Structure

```text
Log-File-Anomaly-Explainer/
│
├── app.py
├── ai_explainer.py
├── anomaly_detector.py
├── log_parser.py
├── verify_parsing.py
├── requirements.txt
│
├── static/
├── templates/
│
├── docs/
├── sample_data/
├── tests/
└── uploads/
```

---

## Setup Instructions

#Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/Log-File-Anomaly-Explainer.git
```

#Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
python app.py
```

Application will run at:

```text
http://localhost:5000
```

---

## Architecture Overview

```text
User Uploads Log File
          |
          v
      Flask Backend
          |
          v
      Log Parser
          |
          v
   Anomaly Detector
          |
          v
   Risk & Severity Analysis
          |
          v
    AI Explanation Engine
          |
          v
     Results Dashboard
```

---

## AI Usage Note
# AI Tool Used

* ChatGPT
* OpenAI API
* Deployment guidance
* Debugging assistance
* Error resolution
* Documentation support

#Human Contributions

* System design
* Frontend development
* Backend implementation
* Integration
* Testing
* Deployment

---

## Sample Data

Sample input files and expected outputs are available in:

```text
sample_data/
```

Contents:

```text
sample_log_1.txt
expected_output_1.csv

sample_log_2.txt
expected_output_2.csv
```

---

## Test Cases

Test cases are available in:

```text
tests/
```

Run tests:

```bash
pytest tests/
```

---

## Assumptions

* Uploaded log files follow standard log formatting.
* Users provide valid log files.
* Internet connection is available for AI-powered explanations.
* OpenAI API key is available when AI chat functionality is used.

---

## Limitations

* Accuracy depends on log quality and formatting.
* AI responses depend on OpenAI API availability.
* Render free-tier services may sleep after inactivity.
* Large log files may increase processing time.

---
##Team Members
-Kattamuri Alekhya
-Velaga Mounika
-Udi Vishnu Vardhini
-Ganisetti Venuka

## Project Links

### GitHub Repository
https://github.com/kalekhya223/Log-File-Anomaly-Explainer

### Live Demo
https://log-file-anomaly-explainer-gxec.onrender.com

### Demo Video
https://drive.google.com/file/d/1eruuughZgu1uebBv3Rvco3hn6WWA7_Ce/view?usp=drivesdk



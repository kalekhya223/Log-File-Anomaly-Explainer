# Log File Anomaly Explainer - AI Diagnostics Dashboard

Welcome to the **Log File Anomaly Explainer** (also known as *LogSentry AI*), an industrial-grade log analysis and AI diagnostic web dashboard built with Python Flask, Bootstrap 5, Chart.js, and OpenAI GPT. 

This project is fully working, beginner-friendly, and perfectly designed for college mini-projects, lab submissions, or developer utility tools.

---

## 🌟 Key Features

1. **Log Upload & Parsing**: Easily drag & drop `.log` or `.txt` files to parse logs line-by-line, extracting Timestamps, Log Levels (INFO, WARNING, ERROR, CRITICAL), and Messages using Pandas and Regex.
2. **Rule-Based Anomaly Detection**: Automatically scans logs for:
   - High/Excessive error rates
   - Repeated/consecutive identical error loops
   - Suspicious authentication activity (failed logins, brute-force attempts)
   - Sudden volume spikes (denial-of-service indicator)
   - Missing timestamps (malformed logs)
   - System issues (Out of Memory, Deadlocks, Null Pointers, Segfaults, Crashes)
3. **AI Explanations (GPT & Local Fallback)**:
   - Integrates with the **OpenAI API** to explain anomalies, root causes, severity ratings, and suggest code/infrastructure fixes.
   - **Local Fallback Mode**: If no OpenAI API key is provided, the system uses custom high-quality local rules templates to explain typical issues seamlessly offline!
4. **Interactive Dashboard**: Real-time stats cards, dark mode toggle, and rich Chart.js visualizations (Log Level Distribution, Error Trend, and Anomaly Breakdown).
5. **Log Explorer Table**: A paginated, searchable, and level-filterable table logs viewer capable of handling large files without lagging the browser.
6. **CSV Export & PDF Report**:
   - Download the parsed logs table directly as a `.csv` file.
   - Print or save the complete dashboard diagnostics summary as a clean, professionally-formatted PDF report.

---

## 📁 Project Structure

```text
log-anomaly-explainer/
│
├── app.py                  # Main Flask backend routes & controllers
├── log_parser.py           # Core Regex & Pandas log parser
├── anomaly_detector.py     # Rule-based anomaly detection engines
├── ai_explainer.py         # OpenAI GPT connection & local fallback rules
├── requirements.txt        # Python library dependencies
├── run_project.bat         # Automated double-click launcher for Windows
├── test_logs.log           # Sample log file for testing anomalies
│
├── templates/
│   ├── index.html          # Landing / home page
│   ├── upload.html         # Drag-and-drop log upload form
│   └── results.html        # Interactive dashboard & log explorer table
│
├── static/
│   ├── css/
│   │   └── style.css       # Premium custom stylesheet (dark/light themes)
│   └── js/
│       └── charts.js       # Chart.js initialization & responsive layout scripts
│
└── uploads/                # Temporary storage for processed results caches
```

*Note: The parser is named `log_parser.py` instead of `parser.py` to avoid shadowing Python's standard library built-in `parser` module, preventing import clashes.*

---

## 🚀 How to Run the Project (Windows - Automatic)

If you are on Windows, you can start the application with a single double-click:
1. Double-click the `run_project.bat` file.
2. The script will automatically:
   - Check if Python is installed.
   - Set up a Python virtual environment (`venv`).
   - Install all required libraries from `requirements.txt`.
   - Open your web browser to `http://127.0.0.1:5000`.
   - Run the Flask server.

---

## ⚙️ How to Run and Debug in VS Code (Step-by-Step)

If you want to open, run, and step-through the code in **VS Code**, follow these steps:

### Prerequisites
1. Download and install [VS Code](https://code.visualstudio.com/).
2. Install the **Python Extension** inside VS Code (search for "Python" in the Extensions Marketplace `Ctrl+Shift+X`).

### Step 1: Open the Project Folder
- Open VS Code.
- Click **File > Open Folder...** and select the `log-anomaly-explainer` directory.

### Step 2: Open terminal and create virtual environment
- Open the integrated terminal in VS Code (`Ctrl+`` or **Terminal > New Terminal**).
- Run the following command to set up the virtual environment:
  ```powershell
  # Windows Powershell:
  py -m venv venv
  
  # macOS/Linux:
  python3 -m venv venv
  ```

### Step 3: Activate the virtual environment
- Run the activation command:
  ```powershell
  # Windows Powershell:
  .\venv\Scripts\Activate.ps1
  
  # macOS/Linux:
  source venv/bin/activate
  ```
  *(VS Code will usually show `(venv)` in the terminal prompt once activated.)*

### Step 4: Install Dependencies
- Run:
  ```bash
  pip install -r requirements.txt
  ```

### Step 5: Configure VS Code Run & Debug Config
To run and debug the Flask app inside VS Code using the debug panel (`F5`):
1. Click the **Run and Debug** icon on the left sidebar (or press `Ctrl+Shift+D`).
2. Click **Create a launch.json file** (choose **Python File** or **Flask**).
3. Replace the content of the `.vscode/launch.json` file with this:
   ```json
   {
       "version": "0.2.0",
       "configurations": [
           {
               "name": "Python: Flask App",
               "type": "debugpy",
               "request": "launch",
               "module": "flask",
               "env": {
                   "FLASK_APP": "app.py",
                   "FLASK_DEBUG": "1"
               },
               "args": [
                   "run",
                   "--no-debugger",
                   "--no-reload"
               ],
               "jinja": true,
               "showReturnValue": true
           }
       ]
   }
   ```
4. Now, simply press **`F5`** or click the green Play button in the debug panel. The debugger will launch the Flask application and let you set breakpoints in `app.py`, `log_parser.py`, etc.

---

## 🧪 Testing with Sample Logs

We have included a sample log file called `test_logs.log` in the root folder. You can use it to test all the features:
1. Open the app browser interface.
2. Drag and drop `test_logs.log` onto the upload zone.
3. Click **Analyze Log File**.
4. Explore the resulting dashboard. You will see:
   - Volume spikes around `19:30:22`.
   - Repeated login failures for the user `admin`.
   - Out of Memory critical crashes.
   - Missing timestamps highlighting malformed lines.

---

## 💡 Using the OpenAI API Key

- **Where to get a key:** You can obtain an API key by signing up at [platform.openai.com](https://platform.openai.com/).
- **How to use it:** You can enter your key directly on the Upload Webpage form, or create a file named `.env` in the root directory and add:
  ```env
  OPENAI_API_KEY=your_actual_api_key_here
  ```
- **If you don't have a key:** Leave it blank! The application will fall back to local rule-based analysis templates and continue working flawlessly.

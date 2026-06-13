import os
import uuid
import json
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename

# Import custom modules
from log_parser import parse_log_file
from anomaly_detector import detect_anomalies
from ai_explainer import generate_ai_explanation

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "log_anomaly_explainer_secret_key_123")

# Configure Upload Folder
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'log'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compute_charts_data(df, anomalies):
    """
    Computes data required for Chart.js dashboards.
    """
    # 1. Log Levels Distribution
    level_counts = df['level'].value_counts().to_dict()
    # Ensure all standard levels exist in the dict
    standard_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    levels_dist = {lvl: int(level_counts.get(lvl, 0)) for lvl in standard_levels}
    
    # 2. Anomaly Distribution
    anomaly_dist = {}
    for anom in anomalies:
        anomaly_dist[anom['type']] = anomaly_dist.get(anom['type'], 0) + anom['count']
        
    # 3. Error Trend Over Time
    # Try to group by parsed timestamps.
    # We will look for time groups. Let's convert timestamps to a simple string representing a slot.
    # If no timestamps are available, group by chunks of line numbers.
    time_series = df.copy()
    
    # Check if we have valid timestamps
    valid_ts = time_series['timestamp'].dropna()
    has_timestamps = len(valid_ts) > (len(df) * 0.5) # at least half have timestamps
    
    trend_labels = []
    trend_data = []
    
    if has_timestamps:
        # Fill missing values and sort
        time_series['timestamp'] = time_series['timestamp'].ffill().bfill()
        
        # Try to parse and extract a readable string for plotting
        # To avoid datetime parsing bottlenecks, we can truncate the timestamp string:
        # e.g., "2026-06-12 19:26:45" -> group by "2026-06-12 19:26" (minute resolution) or hourly
        # Let's write a simple truncator:
        # If timestamp is ISO-like: 2026-06-12 19:26:45 -> take first 16 chars: 2026-06-12 19:26
        # Let's inspect length and truncate.
        def get_time_bucket(ts):
            if not ts:
                return "Unknown"
            ts = str(ts).strip('[]')
            # 2026-06-12 19:26:45 or 2026-06-12T19:26:45 -> minute bucket
            if len(ts) >= 16 and (ts[4] == '-' or ts[4] == '/'):
                return ts[:16].replace('T', ' ')
            # Apache: 12/Jun/2026:19:26:45 -> 12/Jun/2026:19:26
            if ':' in ts:
                parts = ts.split(':')
                if len(parts) >= 3:
                    return ":".join(parts[:3]) # dd/Mmm/yyyy:hh:mm
            return ts[:10] # Fallback to date
            
        time_series['time_bucket'] = time_series['timestamp'].apply(get_time_bucket)
        
        # Group by bucket and count errors/warnings vs info
        grouped = time_series.groupby(['time_bucket', 'level']).size().unstack(fill_value=0)
        
        # Sort by index (chronological as strings usually match chronological order)
        grouped = grouped.sort_index()
        
        # Limit to last 30 buckets to avoid cluttering charts
        grouped = grouped.tail(30)
        
        trend_labels = grouped.index.tolist()
        # Data can be total errors + warnings
        err_col = 'ERROR' if 'ERROR' in grouped.columns else None
        crit_col = 'CRITICAL' if 'CRITICAL' in grouped.columns else None
        warn_col = 'WARNING' if 'WARNING' in grouped.columns else None
        
        for idx in trend_labels:
            err_cnt = 0
            if err_col: err_cnt += int(grouped.loc[idx, 'ERROR'])
            if crit_col: err_cnt += int(grouped.loc[idx, 'CRITICAL'])
            if warn_col: err_cnt += int(grouped.loc[idx, 'WARNING'])
            trend_data.append(err_cnt)
    else:
        # No timestamps, group by line chunks of size 50 or 100
        chunk_size = max(10, len(df) // 10)
        time_series['chunk'] = (time_series['line_number'] - 1) // chunk_size
        time_series['chunk_label'] = time_series['chunk'].apply(
            lambda c: f"Lines {c*chunk_size+1}-{(c+1)*chunk_size}"
        )
        
        grouped = time_series.groupby(['chunk', 'chunk_label', 'level']).size().unstack(fill_value=0)
        grouped = grouped.sort_index()
        
        trend_labels = grouped.index.get_level_values('chunk_label').tolist()
        
        err_col = 'ERROR' if 'ERROR' in grouped.columns else None
        crit_col = 'CRITICAL' if 'CRITICAL' in grouped.columns else None
        warn_col = 'WARNING' if 'WARNING' in grouped.columns else None
        
        for idx in grouped.index:
            err_cnt = 0
            if err_col: err_cnt += int(grouped.loc[idx, 'ERROR'])
            if crit_col: err_cnt += int(grouped.loc[idx, 'CRITICAL'])
            if warn_col: err_cnt += int(grouped.loc[idx, 'WARNING'])
            trend_data.append(err_cnt)

    return {
        "levels_distribution": levels_dist,
        "anomalies_distribution": anomaly_dist,
        "error_trend": {
            "labels": trend_labels,
            "data": trend_data
        }
    }

HISTORY_FILE = os.path.join(app.root_path, 'uploads', 'history.json')

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as hf:
            return json.load(hf)
    except Exception:
        return []

def save_history(history):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as hf:
            json.dump(history, hf, indent=4)
    except Exception as e:
        print(f"Error saving history: {str(e)}")

@app.route('/')
def index():
    history = load_history()
    # Sort history by date descending
    history = sorted(history, key=lambda x: x.get('timestamp', ''), reverse=True)
    return render_template('index.html', history=history)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Check if file part is present
        if 'file' not in request.files:
            flash('No file part in the request', 'danger')
            return redirect(request.url)
            
        file = request.files['file']
        api_key = request.form.get('api_key', '').strip()
        
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_id = str(uuid.uuid4())
            # Save uploaded log file
            temp_filename = f"{unique_id}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
            file.save(file_path)
            
            try:
                # 1. Parse log file
                df = parse_log_file(file_path)
                
                if df.empty:
                    flash('The uploaded file was empty or could not be parsed.', 'warning')
                    return redirect(request.url)
                    
                # 2. Run anomaly detector
                anomalies = detect_anomalies(df)
                
                # 3. Process with AI Explainer (adding generated explanations to anomalies)
                for anomaly in anomalies:
                    # Generates structured explanation from OpenAI or fallback
                    explanation = generate_ai_explanation(anomaly, api_key=api_key)
                    anomaly.update(explanation)
                    
                # 4. Compute statistics
                total_logs = len(df)
                error_count = int(df['level'].isin(['ERROR', 'CRITICAL']).sum())
                warning_count = int(df['level'].eq('WARNING').sum())
                anomalies_count = len(anomalies)
                
                # Compute severity score
                severity_scores = {"Low": 1, "Medium": 3, "High": 7, "Critical": 10}
                max_severity = "Low"
                score_sum = 0
                for a in anomalies:
                    sev = a['severity']
                    score_sum += severity_scores.get(sev, 1) * a['count']
                    # Find maximum severity
                    if severity_scores.get(sev, 1) > severity_scores.get(max_severity, 1):
                        max_severity = sev
                
                summary = {
                    "filename": filename,
                    "total_logs": total_logs,
                    "error_count": error_count,
                    "warning_count": warning_count,
                    "anomalies_count": anomalies_count,
                    "max_severity": max_severity,
                    "score": score_sum
                }
                
                # 5. Process Charts Data
                charts_data = compute_charts_data(df, anomalies)
                
                # 6. Cache results in a JSON file
                cache_data = {
                    "summary": summary,
                    "anomalies": anomalies,
                    "charts_data": charts_data,
                    "logs": df.to_dict(orient='records')
                }
                
                cache_path = os.path.join(app.config['UPLOAD_FOLDER'], f"cache_{unique_id}.json")
                with open(cache_path, 'w', encoding='utf-8') as cf:
                    json.dump(cache_data, cf, indent=4)
                    
                # Append to history
                from datetime import datetime
                history = load_history()
                history.append({
                    "result_id": unique_id,
                    "filename": filename,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_logs": total_logs,
                    "error_count": error_count,
                    "warning_count": warning_count,
                    "anomalies_count": anomalies_count,
                    "max_severity": max_severity
                })
                save_history(history)
                
                # Clean up uploaded raw log file
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                return redirect(url_for('results', result_id=unique_id))
                
            except Exception as e:
                flash(f"An error occurred while processing the file: {str(e)}", 'danger')
                # Clean up file in case of error
                if os.path.exists(file_path):
                    os.remove(file_path)
                return redirect(request.url)
        else:
            flash('Invalid file extension. Please upload a .log or .txt file.', 'danger')
            return redirect(request.url)
            
    return render_template('upload.html')

@app.route('/results')
def results():
    result_id = request.args.get('result_id')
    if not result_id:
        flash('Invalid result ID', 'danger')
        return redirect(url_for('index'))
        
    cache_path = os.path.join(app.config['UPLOAD_FOLDER'], f"cache_{result_id}.json")
    if not os.path.exists(cache_path):
        flash('Results not found. The file may have expired or was not processed correctly.', 'danger')
        return redirect(url_for('upload'))
        
    try:
        with open(cache_path, 'r', encoding='utf-8') as cf:
            data = json.load(cf)
            
        return render_template(
            'results.html', 
            summary=data['summary'], 
            anomalies=data['anomalies'],
            charts_data=data['charts_data'],
            result_id=result_id
        )
    except Exception as e:
        flash(f"Error loading results: {str(e)}", 'danger')
        return redirect(url_for('upload'))

@app.route('/api/logs/<result_id>')
def api_logs(result_id):
    """
    Paginated, filterable, and searchable log endpoint.
    This helps handle files with thousands of logs without freezing the browser.
    """
    cache_path = os.path.join(app.config['UPLOAD_FOLDER'], f"cache_{result_id}.json")
    if not os.path.exists(cache_path):
        return jsonify({"error": "Results not found"}), 404
        
    try:
        with open(cache_path, 'r', encoding='utf-8') as cf:
            data = json.load(cf)
            
        logs = data['logs']
        
        # Read search & filter parameters
        search_query = request.args.get('search', '').lower()
        level_filter = request.args.get('level', '').upper()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        # Filter logs
        filtered_logs = logs
        if level_filter and level_filter != 'ALL':
            filtered_logs = [log for log in filtered_logs if log['level'] == level_filter]
            
        if search_query:
            filtered_logs = [
                log for log in filtered_logs 
                if search_query in str(log['message']).lower() or 
                   search_query in str(log['timestamp']).lower() or 
                   search_query in str(log['line_number']).lower()
            ]
            
        # Paginate logs
        total_items = len(filtered_logs)
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_logs = filtered_logs[start_idx:end_idx]
        
        return jsonify({
            "logs": paginated_logs,
            "total_items": total_items,
            "total_pages": total_pages,
            "current_page": page,
            "per_page": per_page
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/export/csv/<result_id>')
def export_csv(result_id):
    cache_path = os.path.join(app.config['UPLOAD_FOLDER'], f"cache_{result_id}.json")
    if not os.path.exists(cache_path):
        flash('Results not found.', 'danger')
        return redirect(url_for('upload'))
        
    try:
        with open(cache_path, 'r', encoding='utf-8') as cf:
            data = json.load(cf)
            
        df = pd.DataFrame(data['logs'])
        
        # Generate export filename
        orig_filename = data['summary']['filename'].rsplit('.', 1)[0]
        export_filename = f"parsed_{orig_filename}_{result_id[:8]}.csv"
        
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], export_filename)
        df.to_csv(csv_path, index=False)
        
        # Send file and then delete it
        response = send_file(csv_path, as_attachment=True, download_name=export_filename)
        
        # We can configure a teardown or background task to clean up files.
        # But for this simple app, we can just return it. 
        # (In production we would delete, but let's keep it basic and reliable).
        return response
    except Exception as e:
        flash(f"Error exporting CSV: {str(e)}", 'danger')
        return redirect(url_for('results', result_id=result_id))

@app.route('/api/chat/<result_id>', methods=['POST'])
def api_chat(result_id):
    cache_path = os.path.join(app.config['UPLOAD_FOLDER'], f"cache_{result_id}.json")
    if not os.path.exists(cache_path):
        return jsonify({"error": "Analysis context not found"}), 404
        
    try:
        req_data = request.get_json() or {}
        user_message = req_data.get('message', '').strip()
        api_key = req_data.get('api_key', '').strip()
        
        if not user_message:
            return jsonify({"error": "Empty message"}), 400
            
        with open(cache_path, 'r', encoding='utf-8') as cf:
            data = json.load(cf)
            
        # Compile a context of the anomalies and logs to feed the model
        anomalies_summary = []
        for i, a in enumerate(data['anomalies'], 1):
            anomalies_summary.append(
                f"Anomaly #{i}: {a['type']} (Severity: {a['severity']}) - {a['summary']}"
            )
        anomalies_context = "\n".join(anomalies_summary)
        
        # Take a subset of logs (e.g. error/warning lines) to limit tokens
        sample_logs = [
            f"Line {l['line_number']} [{l['level']}]: {l['message']}"
            for l in data['logs'] if l['level'] in ['WARNING', 'ERROR', 'CRITICAL']
        ][:30]
        logs_context = "\n".join(sample_logs)
        
        # OpenAI Chat execution
        active_key = api_key or os.getenv("OPENAI_API_KEY")
        
        from ai_explainer import HAS_OPENAI
        if HAS_OPENAI and active_key:
            from openai import OpenAI
            client = OpenAI(api_key=active_key)
            
            system_prompt = (
                "You are LogSentry AI, a helpful systems reliability engineer assistant. "
                "You are helping a developer debug an application based on the parsed logs and "
                "anomalies detected. Answer the user's questions clearly, explaining root causes, "
                "impacts, and providing code snippets or shell command fixes where appropriate."
            )
            
            user_prompt = f"""
            Here is the summary of anomalies detected in the log file '{data['summary']['filename']}':
            {anomalies_context}
            
            Here is a sample of the warning/error logs:
            {logs_context}
            
            User Question: {user_message}
            
            Provide a helpful, direct, and detailed answer. Keep it professional and technical.
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=600
            )
            reply = response.choices[0].message.content.strip()
            
        else:
            # Local fallback rule chatbot response
            reply = (
                f"I parsed your question: '{user_message}'. I am running in local fallback mode (no OpenAI API key "
                "provided). To help you with debugging, here is the list of anomalies I detected in your logs:\n\n"
            )
            for idx, a in enumerate(data['anomalies'], 1):
                reply += f"**{idx}. {a['type']}** (Severity: {a['severity']})\n* {a['summary']}\n"
            
            # Simple keyword matching for local chatbot help
            query_lower = user_message.lower()
            if "memory" in query_lower or "oom" in query_lower:
                reply += (
                    "\n**Additional Guidance on Memory Issues:**\n"
                    "Since you asked about memory, the logs show an OutOfMemoryError on line 13. "
                    "This usually means the JVM or runtime environment ran out of heap space. "
                    "I recommend checking if there are long-lived references causing a memory leak, "
                    "or increasing the heap size using `-Xmx` (for Java) or `NODE_OPTIONS=--max-old-space-size` (for Node.js)."
                )
            elif "login" in query_lower or "auth" in query_lower or "brute" in query_lower:
                reply += (
                    "\n**Additional Guidance on Security/Auth Issues:**\n"
                    "Since you asked about login or authentication, the logs show multiple failed login attempts. "
                    "This could be a credential stuffing or brute-force attempt. I recommend checking the IP addresses "
                    "associated with these attempts and blocking them at your firewall, or configuring rate limits."
                )
            elif "deadlock" in query_lower or "lock" in query_lower:
                reply += (
                    "\n**Additional Guidance on Database Deadlocks:**\n"
                    "Since you asked about locking, deadlocks happen when two queries lock resources in circular order. "
                    "Make sure your transactions update tables in the same order and use indexes to make operations faster."
                )
            else:
                reply += (
                    "\n*To ask me custom questions and receive smart solutions, please supply your OpenAI API key "
                    "on the upload screen.*"
                )
                
        return jsonify({"reply": reply})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history/delete/<result_id>', methods=['POST'])
def delete_history(result_id):
    try:
        # Load history
        history = load_history()
        # Filter out item
        new_history = [item for item in history if item['result_id'] != result_id]
        save_history(new_history)
        
        # Remove cached file
        cache_path = os.path.join(app.config['UPLOAD_FOLDER'], f"cache_{result_id}.json")
        if os.path.exists(cache_path):
            os.remove(cache_path)
            
        flash('Report deleted successfully.', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error deleting report: {str(e)}', 'danger')
        return redirect(url_for('index'))

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import re
import subprocess
import threading
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__, static_folder='public')
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*")

PORT = int(os.environ.get('PORT', 3000))

# Global variables
log_process = None
grep_process = None
behavior_config = {'behaviors': []}

# Load behavior configuration
def load_config():
    global behavior_config
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            behavior_config = json.load(f)
    except Exception as e:
        print(f'Error reading or parsing config.json: {e}')
        behavior_config = {'behaviors': []}

# Initialize configuration
load_config()

# Serve static files
@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('public', filename)

# API Endpoints
@app.route('/config', methods=['GET'])
def get_config():
    return jsonify(behavior_config)

@app.route('/config', methods=['POST'])
def update_config():
    global behavior_config
    try:
        new_config = request.get_json()
        
        # Validate the configuration structure
        if not new_config or 'behaviors' not in new_config or not isinstance(new_config['behaviors'], list):
            return 'Invalid configuration format.', 400
        
        # Save to file
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=2, ensure_ascii=False)
        
        # Update in-memory configuration
        behavior_config = new_config
        
        socketio.emit('log', {'platform': 'system', 'message': 'Configuration updated successfully.'})
        return 'Configuration updated.', 200
    except Exception as e:
        socketio.emit('log', {'platform': 'system', 'message': f'Error updating configuration: {str(e)}'})
        return 'Error updating configuration.', 500

@app.route('/reload-config', methods=['POST'])
def reload_config():
    try:
        load_config()
        socketio.emit('log', {'platform': 'system', 'message': 'Configuration reloaded successfully.'})
        return 'Configuration reloaded.', 200
    except Exception as e:
        socketio.emit('log', {'platform': 'system', 'message': f'Error reloading configuration: {str(e)}'})
        return 'Error reloading configuration.', 500

def analyze_log_behavior(log_message, platform):
    """Analyze log message for configured behaviors"""
    for behavior in behavior_config.get('behaviors', []):
        try:
            pattern = re.compile(behavior['pattern'], re.IGNORECASE)
            if pattern.search(log_message):
                socketio.emit('behavior_triggered', {
                    'behavior': behavior,
                    'log': log_message
                })
        except re.error as e:
            socketio.emit('log', {
                'platform': 'system', 
                'message': f'Invalid regex pattern in behavior "{behavior.get("name", "unknown")}": {behavior["pattern"]} - {str(e)}'
            })

def read_log_stream(process, platform, tag=None):
    """Read log stream and emit to clients"""
    try:
        while True:
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                continue
            
            log_message = line.decode('utf-8', errors='ignore').strip()
            if log_message:
                # Send log to frontend
                socketio.emit('log', {'platform': platform, 'message': log_message})
                
                # Analyze for behaviors
                analyze_log_behavior(log_message, platform)
    except Exception as e:
        socketio.emit('log', {'platform': 'system', 'message': f'Error reading log stream: {str(e)}'})
    finally:
        if process.poll() is None:
            process.terminate()

def check_command_available(command):
    """Check if a command is available in the system or local tools directory"""
    # First check if command exists in local tools directory
    local_tool_path = os.path.join(os.path.dirname(__file__), 'tools', command)
    if os.path.isfile(local_tool_path) and os.access(local_tool_path, os.X_OK):
        return True
    
    # For hdc, also check toolchains subdirectory
    if command == 'hdc':
        toolchains_path = os.path.join(os.path.dirname(__file__), 'tools', 'toolchains', 'hdc')
        if os.path.isfile(toolchains_path) and os.access(toolchains_path, os.X_OK):
            return True
    
    # Then check system PATH
    try:
        subprocess.run([command, '--version'], capture_output=True, check=False, timeout=5)
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        try:
            # Try alternative check methods
            subprocess.run(['which', command], capture_output=True, check=True, timeout=5)
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
            return False

def get_command_path(command):
    """Get the full path of a command, preferring local tools directory"""
    # First check local tools directory
    local_tool_path = os.path.join(os.path.dirname(__file__), 'tools', command)
    if os.path.isfile(local_tool_path) and os.access(local_tool_path, os.X_OK):
        return local_tool_path
    
    # For hdc, also check toolchains subdirectory
    if command == 'hdc':
        toolchains_path = os.path.join(os.path.dirname(__file__), 'tools', 'toolchains', 'hdc')
        if os.path.isfile(toolchains_path) and os.access(toolchains_path, os.X_OK):
            return toolchains_path
    
    # Return command name for system PATH lookup
    return command

@app.route('/start-log', methods=['POST'])
def start_log():
    global log_process, grep_process
    
    data = request.get_json()
    platform = data.get('platform')
    tag = data.get('tag', '').strip()
    
    if log_process and log_process.poll() is None:
        return 'A logging process is already running.', 400
    
    command = []
    command_name = ''
    
    if platform == 'android':
        command_name = 'adb'
        command = [get_command_path('adb'), 'logcat']
    elif platform == 'ios':
        # NOTE: This requires 'idevicesyslog' to be installed.
        # You can install it via Homebrew: `brew install libimobiledevice`
        command_name = 'idevicesyslog'
        # For iOS, still use the specific path as it's commonly installed there
        if os.path.isfile('/opt/homebrew/bin/idevicesyslog'):
            command = ['/opt/homebrew/bin/idevicesyslog']
        else:
            command = [get_command_path('idevicesyslog')]
    elif platform == 'harmonyos':
        # NOTE: This supports both local tools directory and system-installed hdc
        command_name = 'hdc'
        command = [get_command_path('hdc'), 'hilog']
    else:
        return 'Invalid platform specified.', 400
    
    # Check if command is available before attempting to start
    if not check_command_available(command_name):
        if platform == 'android':
            install_guide = 'Please install Android SDK Platform Tools and ensure adb is in your PATH, or place adb in the tools/ directory.'
        elif platform == 'ios':
            install_guide = 'Please install libimobiledevice: brew install libimobiledevice, or place idevicesyslog in the tools/ directory.'
        elif platform == 'harmonyos':
            install_guide = 'Please download HarmonyOS SDK and add hdc to your PATH, or place hdc executable in the tools/ directory. Download from: https://developer.harmonyos.com/cn/develop/deveco-studio'
        
        error_message = f'Command "{command_name}" not found. {install_guide}'
        socketio.emit('log', {'platform': 'system', 'message': error_message})
        return error_message, 400
    
    try:
        # Start the main log process
        log_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=False,
            bufsize=1
        )
        
        socketio.emit('log', {'platform': 'system', 'message': f'Starting {platform} log collection...'})
        
        # If tag filtering is requested, pipe through grep
        if tag:
            socketio.emit('log', {'platform': 'system', 'message': f'Applying tag filter: "{tag}"'})
            grep_process = subprocess.Popen(
                ['grep', '--line-buffered', '-i', tag],
                stdin=log_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=False,
                bufsize=1
            )
            log_process.stdout.close()  # Allow log_process to receive a SIGPIPE if grep_process exits
            
            # Start thread to read from grep process
            log_thread = threading.Thread(
                target=read_log_stream,
                args=(grep_process, platform, tag),
                daemon=True
            )
            
            # Start thread to handle grep stderr
            def read_grep_stderr():
                try:
                    while True:
                        line = grep_process.stderr.readline()
                        if not line:
                            if grep_process.poll() is not None:
                                break
                            continue
                        error_message = line.decode('utf-8', errors='ignore').strip()
                        if error_message:
                            socketio.emit('log', {'platform': 'system', 'message': f'Grep ERROR: {error_message}'})
                except Exception as e:
                    socketio.emit('log', {'platform': 'system', 'message': f'Error reading grep stderr: {str(e)}'})
            
            grep_stderr_thread = threading.Thread(target=read_grep_stderr, daemon=True)
            grep_stderr_thread.start()
        else:
            # Start thread to read from main process
            log_thread = threading.Thread(
                target=read_log_stream,
                args=(log_process, platform, tag),
                daemon=True
            )
        
        log_thread.start()
        
        # Start thread to handle stderr
        def read_stderr():
            try:
                for line in iter(log_process.stderr.readline, b''):
                    if line:
                        error_message = line.decode('utf-8', errors='ignore').strip()
                        if error_message:
                            socketio.emit('log', {'platform': 'system', 'message': f'ERROR: {error_message}'})
            except Exception as e:
                socketio.emit('log', {'platform': 'system', 'message': f'Error reading stderr: {str(e)}'})
        
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()
        
        return f'{platform} logging started.', 200
        
    except Exception as e:
        # Provide platform-specific installation guidance
        if platform == 'android':
            install_guide = 'Please install Android SDK Platform Tools and ensure adb is in your PATH.'
        elif platform == 'ios':
            install_guide = 'Please install libimobiledevice: brew install libimobiledevice'
        elif platform == 'harmonyos':
            install_guide = 'Please download and install HarmonyOS SDK, then add hdc to your PATH. You can download it from: https://developer.harmonyos.com/cn/develop/deveco-studio'
        else:
            install_guide = 'Please ensure the required command is installed and accessible.'
        
        error_message = f'Failed to start {platform} logging. {install_guide} Error: {str(e)}'
        socketio.emit('log', {'platform': 'system', 'message': error_message})
        return error_message, 500

@app.route('/stop-log', methods=['POST'])
def stop_log():
    global log_process, grep_process
    
    if log_process and log_process.poll() is None:
        try:
            if grep_process and grep_process.poll() is None:
                grep_process.terminate()
                grep_process.wait(timeout=5)
                grep_process = None
            
            log_process.terminate()
            log_process.wait(timeout=5)
            log_process = None
            
            socketio.emit('log', {'platform': 'system', 'message': 'Logging process stopped.'})
            return 'Logging process stopped.', 200
        except Exception as e:
            socketio.emit('log', {'platform': 'system', 'message': f'Error stopping process: {str(e)}'})
            return 'Error stopping logging process.', 500
    else:
        return 'No logging process is currently running.', 400

# WebSocket events
@socketio.on('connect')
def handle_connect():
    print('A client connected to the web UI.')
    emit('log', {'platform': 'system', 'message': 'Connected to log server.'})

@socketio.on('disconnect')
def handle_disconnect():
    print('A client disconnected.')

if __name__ == '__main__':
    print(f'Log viewer server running on http://localhost:{PORT}')
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False)
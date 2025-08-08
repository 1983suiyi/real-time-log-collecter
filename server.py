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
import jsonschema
from jsonschema import validate, ValidationError

app = Flask(__name__, static_folder='public')
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*")

PORT = int(os.environ.get('PORT', 3000))

# Global variables
log_process = None
grep_process = None
behavior_config = {'behaviors': []}
logging_active = False  # Flag to control log streaming

# Load behavior configuration
def load_config():
    global behavior_config
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            behavior_config = json.load(f)
        # Validate configuration against schema
        validate_config_structure(behavior_config)
    except Exception as e:
        print(f'Error reading or parsing config.json: {e}')
        behavior_config = {'behaviors': []}

def validate_config_structure(config):
    """Validate configuration structure against schema"""
    try:
        with open('config_schema.json', 'r', encoding='utf-8') as f:
            schema = json.load(f)
        validate(instance=config, schema=schema)
        return True, None
    except ValidationError as e:
        return False, f"Configuration validation error: {e.message}"
    except FileNotFoundError:
        print("Warning: config_schema.json not found, skipping schema validation")
        return True, None
    except Exception as e:
        return False, f"Schema validation error: {str(e)}"

def validate_data_by_type(data, data_type, validation_rules=None):
    """Validate data based on specified type and rules"""
    try:
        if data_type == 'json':
            if isinstance(data, str):
                parsed_data = json.loads(data)
            else:
                parsed_data = data
            
            # Apply JSON schema validation if provided
            if validation_rules and 'jsonSchema' in validation_rules:
                validate(instance=parsed_data, schema=validation_rules['jsonSchema'])
            return True, parsed_data, None
            
        elif data_type == 'number':
            if isinstance(data, str):
                num_data = float(data)
            else:
                num_data = float(data)
            
            # Apply number range validation if provided
            if validation_rules and 'numberRange' in validation_rules:
                range_rules = validation_rules['numberRange']
                if 'min' in range_rules and num_data < range_rules['min']:
                    return False, None, f"Number {num_data} is below minimum {range_rules['min']}"
                if 'max' in range_rules and num_data > range_rules['max']:
                    return False, None, f"Number {num_data} is above maximum {range_rules['max']}"
            return True, num_data, None
            
        elif data_type == 'boolean':
            if isinstance(data, str):
                bool_data = data.lower() in ('true', '1', 'yes', 'on')
            else:
                bool_data = bool(data)
            return True, bool_data, None
            
        elif data_type == 'text':
            str_data = str(data)
            # Apply string length validation if provided
            if validation_rules and 'stringLength' in validation_rules:
                length_rules = validation_rules['stringLength']
                if 'min' in length_rules and len(str_data) < length_rules['min']:
                    return False, None, f"String length {len(str_data)} is below minimum {length_rules['min']}"
                if 'max' in length_rules and len(str_data) > length_rules['max']:
                    return False, None, f"String length {len(str_data)} is above maximum {length_rules['max']}"
            return True, str_data, None
            
        else:
            return True, data, None
            
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON format: {str(e)}"
    except ValueError as e:
        return False, None, f"Invalid {data_type} format: {str(e)}"
    except ValidationError as e:
        return False, None, f"JSON schema validation failed: {e.message}"
    except Exception as e:
        return False, None, f"Validation error: {str(e)}"

def extract_data_from_log(log_message, extractors):
    """Extract structured data from log message using extractors"""
    extracted_data = {}
    
    for extractor in extractors:
        try:
            pattern = re.compile(extractor['pattern'], re.IGNORECASE)
            match = pattern.search(log_message)
            
            if match:
                raw_data = match.group(1) if match.groups() else match.group(0)
                data_type = extractor.get('dataType', 'text')
                
                is_valid, parsed_data, error = validate_data_by_type(raw_data, data_type)
                
                if is_valid:
                    extracted_data[extractor['name']] = {
                        'value': parsed_data,
                        'type': data_type,
                        'raw': raw_data
                    }
                else:
                    extracted_data[extractor['name']] = {
                        'value': None,
                        'type': data_type,
                        'raw': raw_data,
                        'error': error
                    }
        except re.error as e:
            socketio.emit('log', {
                'platform': 'system',
                'message': f'Invalid regex pattern in extractor "{extractor.get("name", "unknown")}": {extractor["pattern"]} - {str(e)}'
            })
    
    return extracted_data

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
        
        # Basic structure validation
        if not new_config or 'behaviors' not in new_config or not isinstance(new_config['behaviors'], list):
            return jsonify({'error': 'Invalid configuration format. Must contain "behaviors" array.'}), 400
        
        # Validate against schema
        is_valid, error_message = validate_config_structure(new_config)
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        # Validate each behavior's regex patterns
        validation_errors = []
        for i, behavior in enumerate(new_config['behaviors']):
            # Validate main pattern
            try:
                re.compile(behavior['pattern'])
            except re.error as e:
                validation_errors.append(f"Behavior {i+1} '{behavior.get('name', 'unknown')}': Invalid regex pattern '{behavior['pattern']}' - {str(e)}")
            
            # Validate extractor patterns if present
            if 'extractors' in behavior:
                for j, extractor in enumerate(behavior['extractors']):
                    try:
                        re.compile(extractor['pattern'])
                    except re.error as e:
                        validation_errors.append(f"Behavior {i+1} '{behavior.get('name', 'unknown')}', Extractor {j+1} '{extractor.get('name', 'unknown')}': Invalid regex pattern '{extractor['pattern']}' - {str(e)}")
        
        if validation_errors:
            return jsonify({'error': 'Regex validation errors', 'details': validation_errors}), 400
        
        # Save to file
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=2, ensure_ascii=False)
        
        # Update in-memory configuration
        behavior_config = new_config
        
        socketio.emit('log', {'platform': 'system', 'message': 'Configuration updated successfully.'})
        return jsonify({'message': 'Configuration updated successfully.'}), 200
    except json.JSONDecodeError as e:
        error_msg = f'Invalid JSON format: {str(e)}'
        socketio.emit('log', {'platform': 'system', 'message': f'Error updating configuration: {error_msg}'})
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        error_msg = f'Error updating configuration: {str(e)}'
        socketio.emit('log', {'platform': 'system', 'message': error_msg})
        return jsonify({'error': error_msg}), 500

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
        # Skip disabled behaviors
        if not behavior.get('enabled', True):
            continue
            
        try:
            pattern = re.compile(behavior['pattern'], re.IGNORECASE)
            match = pattern.search(log_message)
            
            if match:
                # Extract structured data if extractors are defined
                extracted_data = {}
                if 'extractors' in behavior:
                    extracted_data = extract_data_from_log(log_message, behavior['extractors'])
                
                # Validate extracted data if validation rules are defined
                validation_results = {}
                if 'validation' in behavior and extracted_data:
                    data_type = behavior.get('dataType', 'text')
                    validation_rules = behavior['validation']
                    
                    # Get the main data to validate (first extractor or matched text)
                    main_data = None
                    if extracted_data:
                        first_extractor = list(extracted_data.values())[0]
                        main_data = first_extractor.get('raw')
                    else:
                        main_data = match.group(1) if match.groups() else match.group(0)
                    
                    if main_data:
                        is_valid, parsed_data, error = validate_data_by_type(main_data, data_type, validation_rules)
                        validation_results = {
                            'isValid': is_valid,
                            'parsedData': parsed_data,
                            'error': error,
                            'dataType': data_type
                        }
                
                # Emit behavior triggered event with enhanced data
                socketio.emit('behavior_triggered', {
                    'behavior': behavior,
                    'log': log_message,
                    'extractedData': extracted_data,
                    'validationResults': validation_results,
                    'platform': platform,
                    'timestamp': threading.current_thread().ident  # Simple timestamp substitute
                })
                
                # Log validation errors if any
                if validation_results.get('error'):
                    socketio.emit('log', {
                        'platform': 'system',
                        'message': f'Validation error in behavior "{behavior.get("name", "unknown")}": {validation_results["error"]}'
                    })
                    
        except re.error as e:
            socketio.emit('log', {
                'platform': 'system', 
                'message': f'Invalid regex pattern in behavior "{behavior.get("name", "unknown")}": {behavior["pattern"]} - {str(e)}'
            })

def read_log_stream(process, platform, tag=None):
    """Read log stream and emit to clients"""
    global logging_active
    try:
        while logging_active and process.poll() is None:
            line = process.stdout.readline()
            if not line:
                continue
            
            # Check again if logging is still active before processing
            if not logging_active:
                break
                
            log_message = line.decode('utf-8', errors='ignore').strip()
            if log_message:
                # Send log to frontend
                socketio.emit('log', {'platform': platform, 'message': log_message})
                
                # Analyze for behaviors
                analyze_log_behavior(log_message, platform)
    except Exception as e:
        if logging_active:  # Only emit error if logging is still active
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
    global log_process, grep_process, logging_active
    
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
        # Set logging active flag
        logging_active = True
        
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
        
        # Notify frontend that logging is active
        socketio.emit('logging_status', {'active': True})
        
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
    global log_process, grep_process, logging_active
    
    # Set logging inactive flag first to stop log streaming
    logging_active = False
    
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
            socketio.emit('logging_status', {'active': False})  # Notify frontend about status change
            return 'Logging process stopped.', 200
        except Exception as e:
            socketio.emit('log', {'platform': 'system', 'message': f'Error stopping process: {str(e)}'})
            return 'Error stopping logging process.', 500
    else:
        socketio.emit('logging_status', {'active': False})  # Ensure status is updated
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
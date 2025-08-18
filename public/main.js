document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    const logContainer = document.getElementById('log-container');
    const behaviorLogContainer = document.getElementById('behavior-log-container');
    const platformSelector = document.getElementById('platform-filter');
    const tagFilter = document.getElementById('tag-filter');
    const startButton = document.getElementById('start-log');
    const stopButton = document.getElementById('stop-log');
    const clearLogsButton = document.getElementById('clear-logs');
    const reloadConfigButton = document.getElementById('reload-config');
    const manageConfigButton = document.getElementById('manage-config');
    const configModal = document.getElementById('config-modal');
    const configEditor = document.getElementById('config-editor');
    const saveConfigButton = document.getElementById('save-config');
    const cancelConfigButton = document.getElementById('cancel-config');
    const closeModalButton = document.querySelector('.close');
    
    // Configuration validation state
    let validationTimeout = null;
    let currentValidationErrors = [];

    let isAutoScrollEnabled = true;

    reloadConfigButton.addEventListener('click', () => {
        fetch('/reload-config', {
            method: 'POST',
        })
        .then(response => response.text())
        .then(text => addLogMessage({ platform: 'system', message: text }))
        .catch(err => addLogMessage({ platform: 'system', message: `Error: ${err.message}` }));
    });

    // Configuration management functions
    const loadConfiguration = () => {
        fetch('/config')
            .then(response => response.json())
            .then(config => {
                configEditor.value = jsyaml.dump(config, { indent: 2 });
            })
            .catch(err => {
                addLogMessage({ platform: 'system', message: `Error loading configuration: ${err.message}` });
            });
    };

    const saveConfiguration = () => {
        try {
            const configText = configEditor.value;
            const config = jsyaml.load(configText);
            
            // Validate configuration structure
            const validationResult = validateConfiguration(config);
            if (!validationResult.isValid) {
                addLogMessage({ platform: 'system', message: `配置验证失败: ${validationResult.errors.join(', ')}` });
                return;
            }
            
            fetch('/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            })
            .then(response => response.text())
            .then(text => {
                addLogMessage({ platform: 'system', message: text });
                configModal.style.display = 'none';
                // Clear any previous validation errors
                clearValidationErrors();
            })
            .catch(err => {
                addLogMessage({ platform: 'system', message: `Error saving configuration: ${err.message}` });
            });
        } catch (error) {
            addLogMessage({ platform: 'system', message: `Invalid YAML format: ${error.message}` });
            highlightYamlError(error, configText);
        }
    };

    manageConfigButton.addEventListener('click', () => {
        loadConfiguration();
        configModal.style.display = 'block';
    });

    saveConfigButton.addEventListener('click', saveConfiguration);

    cancelConfigButton.addEventListener('click', () => {
        configModal.style.display = 'none';
    });

    closeModalButton.addEventListener('click', () => {
        configModal.style.display = 'none';
    });

    // Close modal when clicking outside of it
    window.addEventListener('click', (event) => {
        if (event.target === configModal) {
            configModal.style.display = 'none';
        }
    });


    const addLogMessage = (log) => {
        const { platform, message } = log;
        const platformClass = platform ? platform.toLowerCase() : 'system';
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        logEntry.innerHTML = `
            <span class="log-platform ${platformClass}">[${platform || 'System'}]</span>
            <span class="log-message">${message.replace(/\n/g, '<br>')}</span>
        `;
        logContainer.appendChild(logEntry);
        if (isAutoScrollEnabled) {
            logContainer.scrollTop = logContainer.scrollHeight; // Auto-scroll
        }
    };

    socket.on('connect', () => {
        addLogMessage({ platform: 'system', message: 'Connected to log server.' });
    });

    socket.on('disconnect', () => {
        addLogMessage({ platform: 'system', message: 'Disconnected from log server.' });
    });

    socket.on('log', (log) => {
        addLogMessage(log);
    });

    socket.on('behavior_triggered', (data) => {
        const { behavior, log } = data;
        const behaviorEntry = document.createElement('div');
        behaviorEntry.className = 'log-entry behavior-triggered';
        behaviorEntry.innerHTML = `
            <span class="log-platform behavior">[Behavior Triggered]</span>
            <span class="log-message">
                <strong>${behavior.name}:</strong> ${behavior.description}<br>
                <em>Triggering log:</em> ${log.replace(/\n/g, '<br>')}
            </span>
        `;
        behaviorLogContainer.appendChild(behaviorEntry);
        behaviorLogContainer.scrollTop = behaviorLogContainer.scrollHeight;
        if (isAutoScrollEnabled) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    });

    socket.on('logging_status', (data) => {
        const { active } = data;
        updateLoggingStatus(active);
        if (!active) {
            addLogMessage({ platform: 'system', message: '日志收集已停止' });
        }
    });

    function updateLoggingStatus(isActive) {
        const statusIndicator = document.getElementById('loggingStatus');
        if (statusIndicator) {
            statusIndicator.textContent = isActive ? '正在收集日志' : '日志收集已停止';
            statusIndicator.className = isActive ? 'status-active' : 'status-inactive';
        }
    }
    
    // Configuration validation functions
    function validateConfiguration(config) {
        const errors = [];
        
        // Basic structure validation
        if (!config || typeof config !== 'object') {
            errors.push('配置必须是一个有效的JSON对象');
            return { isValid: false, errors };
        }
        
        if (!config.behaviors || !Array.isArray(config.behaviors)) {
            errors.push('配置必须包含behaviors数组');
            return { isValid: false, errors };
        }
        
        // Validate each behavior
        config.behaviors.forEach((behavior, index) => {
            const behaviorErrors = validateBehavior(behavior, index);
            errors.push(...behaviorErrors);
        });
        
        return {
            isValid: errors.length === 0,
            errors
        };
    }
    
    function validateJsonSchemaTypes(schema, prefix) {
        const errors = [];
        const validTypes = ['string', 'number', 'integer', 'boolean', 'array', 'object', 'null'];
        
        function validateSchemaObject(obj, path) {
            if (typeof obj !== 'object' || obj === null) return;
            
            // Check type field
            if (obj.type) {
                if (typeof obj.type === 'string') {
                    if (!validTypes.includes(obj.type)) {
                        errors.push(`${path}.type: 无效的类型 '${obj.type}'，应使用标准类型: ${validTypes.join(', ')}`);
                    }
                } else if (Array.isArray(obj.type)) {
                    obj.type.forEach((type, index) => {
                        if (!validTypes.includes(type)) {
                            errors.push(`${path}.type[${index}]: 无效的类型 '${type}'，应使用标准类型: ${validTypes.join(', ')}`);
                        }
                    });
                }
            }
            
            // Recursively validate properties
            if (obj.properties && typeof obj.properties === 'object') {
                Object.keys(obj.properties).forEach(key => {
                    validateSchemaObject(obj.properties[key], `${path}.properties.${key}`);
                });
            }
            
            // Validate items for arrays
            if (obj.items) {
                if (Array.isArray(obj.items)) {
                    obj.items.forEach((item, index) => {
                        validateSchemaObject(item, `${path}.items[${index}]`);
                    });
                } else {
                    validateSchemaObject(obj.items, `${path}.items`);
                }
            }
            
            // Validate additionalProperties
            if (obj.additionalProperties && typeof obj.additionalProperties === 'object') {
                validateSchemaObject(obj.additionalProperties, `${path}.additionalProperties`);
            }
        }
        
        validateSchemaObject(schema, prefix);
        return errors;
    }
    
    function validateBehavior(behavior, index) {
        const errors = [];
        const prefix = `行为[${index}]`;
        
        // Required fields
        if (!behavior.name || typeof behavior.name !== 'string') {
            errors.push(`${prefix}: 缺少有效的name字段`);
        }
        
        if (!behavior.pattern || typeof behavior.pattern !== 'string') {
            errors.push(`${prefix}: 缺少有效的pattern字段`);
        } else {
            // Validate regex pattern
            try {
                new RegExp(behavior.pattern);
            } catch (e) {
                errors.push(`${prefix}: 无效的正则表达式模式: ${e.message}`);
            }
        }
        
        // Validate data type and validation rules
        if (behavior.dataType) {
            const validDataTypes = ['text', 'json', 'number', 'boolean', 'regex'];
            if (!validDataTypes.includes(behavior.dataType)) {
                errors.push(`${prefix}: 无效的数据类型: ${behavior.dataType}`);
            }
            
            // Validate JSON schema if dataType is json
            if (behavior.dataType === 'json' && behavior.validation && behavior.validation.jsonSchema) {
                try {
                    const schema = behavior.validation.jsonSchema;
                    JSON.parse(JSON.stringify(schema));
                    
                    // Validate JSON Schema types
                    const schemaValidationErrors = validateJsonSchemaTypes(schema, `${prefix}.validation.jsonSchema`);
                    errors.push(...schemaValidationErrors);
                } catch (e) {
                    errors.push(`${prefix}: 无效的JSON Schema: ${e.message}`);
                }
            }
            
            // Validate number range if dataType is number
            if (behavior.dataType === 'number' && behavior.validation) {
                if (behavior.validation.min !== undefined && typeof behavior.validation.min !== 'number') {
                    errors.push(`${prefix}: 最小值必须是数字`);
                }
                if (behavior.validation.max !== undefined && typeof behavior.validation.max !== 'number') {
                    errors.push(`${prefix}: 最大值必须是数字`);
                }
            }
        }
        
        // Validate extractors
        if (behavior.extractors && Array.isArray(behavior.extractors)) {
            behavior.extractors.forEach((extractor, extractorIndex) => {
                if (!extractor.name || typeof extractor.name !== 'string') {
                    errors.push(`${prefix}.extractors[${extractorIndex}]: 缺少有效的name字段`);
                }
                if (!extractor.pattern || typeof extractor.pattern !== 'string') {
                    errors.push(`${prefix}.extractors[${extractorIndex}]: 缺少有效的pattern字段`);
                } else {
                    try {
                        new RegExp(extractor.pattern);
                    } catch (e) {
                        errors.push(`${prefix}.extractors[${extractorIndex}]: 无效的正则表达式: ${e.message}`);
                    }
                }
            });
        }
        
        return errors;
    }
    
    function highlightYamlError(error, configText) {
        const editor = document.getElementById('configEditor');
        if (!editor) return;
        
        // Try to extract line number from error message
        const lineMatch = error.message.match(/line (\d+)/i);
        if (lineMatch) {
            const lineNumber = parseInt(lineMatch[1]) - 1;
            const lines = configText.split('\n');
            if (lineNumber >= 0 && lineNumber < lines.length) {
                // Highlight the error line
                editor.focus();
                const start = lines.slice(0, lineNumber).join('\n').length + (lineNumber > 0 ? 1 : 0);
                const end = start + lines[lineNumber].length;
                editor.setSelectionRange(start, end);
            }
        }
    }
    
    function clearValidationErrors() {
        currentValidationErrors = [];
        // Remove any error highlighting
        const editor = document.getElementById('configEditor');
        if (editor) {
            editor.style.borderColor = '';
        }
    }
    
    function setupRealTimeValidation() {
        const editor = document.getElementById('configEditor');
        if (!editor) return;
        
        editor.addEventListener('input', function() {
            // Clear previous timeout
            if (validationTimeout) {
                clearTimeout(validationTimeout);
            }
            
            // Set new timeout for validation
            validationTimeout = setTimeout(() => {
                validateConfigurationRealTime(editor.value);
            }, 500); // Validate after 500ms of no typing
        });
    }
    
    function validateConfigurationRealTime(configText) {
        try {
            const config = jsyaml.load(configText);
            const validationResult = validateConfiguration(config);
            
            const editor = document.getElementById('configEditor');
            if (validationResult.isValid) {
                editor.style.borderColor = '#4CAF50'; // Green border for valid
                currentValidationErrors = [];
            } else {
                editor.style.borderColor = '#f44336'; // Red border for invalid
                currentValidationErrors = validationResult.errors;
                // Show validation errors in a tooltip or status area
                showValidationErrors(validationResult.errors);
            }
        } catch (error) {
            const editor = document.getElementById('configEditor');
            editor.style.borderColor = '#ff9800'; // Orange border for YAML syntax error
            currentValidationErrors = [`YAML语法错误: ${error.message}`];
        }
    }
    
    function showValidationErrors(errors) {
        // Create or update validation error display
        let errorDisplay = document.getElementById('validationErrors');
        if (!errorDisplay) {
            errorDisplay = document.createElement('div');
            errorDisplay.id = 'validationErrors';
            errorDisplay.style.cssText = `
                background: #ffebee;
                border: 1px solid #f44336;
                border-radius: 4px;
                padding: 8px;
                margin-top: 8px;
                font-size: 12px;
                color: #c62828;
                max-height: 100px;
                overflow-y: auto;
            `;
            const editor = document.getElementById('configEditor');
            editor.parentNode.insertBefore(errorDisplay, editor.nextSibling);
        }
        
        if (errors.length > 0) {
            errorDisplay.innerHTML = '<strong>配置验证错误:</strong><br>' + 
                errors.map(error => `• ${error}`).join('<br>');
            errorDisplay.style.display = 'block';
        } else {
            errorDisplay.style.display = 'none';
        }
    }
    
    // Initialize real-time validation when modal opens
    manageConfigButton.addEventListener('click', function() {
        setTimeout(() => {
            setupRealTimeValidation();
        }, 100); // Small delay to ensure modal is fully opened
    });

    startButton.addEventListener('click', () => {
        const platform = platformSelector.value;
        const tag = tagFilter.value.trim();
        fetch('/start-log', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ platform, tag }),
        })
        .then(response => response.text())
        .then(text => addLogMessage({ platform: 'system', message: text }))
        .catch(err => addLogMessage({ platform: 'system', message: `Error: ${err.message}` }));
    });

    stopButton.addEventListener('click', () => {
        fetch('/stop-log', {
            method: 'POST',
        })
        .then(response => response.text())
        .then(text => addLogMessage({ platform: 'system', message: text }))
        .catch(err => addLogMessage({ platform: 'system', message: `Error: ${err.message}` }));
    });

    clearLogsButton.addEventListener('click', () => {
        logContainer.innerHTML = '';
        behaviorLogContainer.innerHTML = '';
    });

    logContainer.addEventListener('wheel', () => {
        // Disable auto-scroll if user scrolls up
        if (logContainer.scrollTop + logContainer.clientHeight < logContainer.scrollHeight) {
            isAutoScrollEnabled = false;
        } else {
            isAutoScrollEnabled = true;
        }
    });
});
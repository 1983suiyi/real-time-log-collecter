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
    const configUploadInput = document.getElementById('config-upload');
    const manageConfigButton = document.getElementById('manage-config');
    const configModal = document.getElementById('config-modal');
    const configEditor = document.getElementById('config-editor');
    const saveConfigButton = document.getElementById('save-config');
    const cancelConfigButton = document.getElementById('cancel-config');
    const closeModalButton = document.querySelector('.close');
    const tabButtons = document.querySelectorAll('.tab-button');
    
    // Configuration validation state
    let validationTimeout = null;
    let currentValidationErrors = [];

    let isAutoScrollEnabled = true;

    const tagHistory = document.getElementById('tag-history');
    
    // Tab switching functionality
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and panes
            tabButtons.forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
            
            // Add active class to clicked button and corresponding pane
            button.classList.add('active');
            const tabId = button.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // Load tag history from localStorage
    const loadTagHistory = () => {
        const history = JSON.parse(localStorage.getItem('tagHistory')) || [];
        tagHistory.innerHTML = '';
        history.forEach(tag => {
            const option = document.createElement('option');
            option.value = tag;
            tagHistory.appendChild(option);
        });
    };

    // Save tag to localStorage
    const saveTagToHistory = (tag) => {
        if (!tag) return;
        let history = JSON.parse(localStorage.getItem('tagHistory')) || [];
        if (!history.includes(tag)) {
            history.unshift(tag); // Add to the beginning
            history = history.slice(0, 20); // Keep last 20 entries
            localStorage.setItem('tagHistory', JSON.stringify(history));
            loadTagHistory();
        }
    };

    reloadConfigButton.addEventListener('click', () => {
        fetch('/reload-config', {
            method: 'POST',
        })
        .then(response => response.text())
        .then(text => addLogMessage({ platform: 'system', message: text }))
        .catch(err => addLogMessage({ platform: 'system', message: `Error: ${err.message}` }));
    });

    configUploadInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) {
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result;
            try {
                const config = jsyaml.load(content);
                fetch('/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(config),
                })
                .then(response => response.text())
                .then(text => {
                    addLogMessage({ platform: 'system', message: text });
                })
                .catch(err => {
                    addLogMessage({ platform: 'system', message: `Error saving configuration: ${err.message}` });
                });
            } catch (error) {
                addLogMessage({ platform: 'system', message: `Invalid YAML format: ${error.message}` });
            }
        };
        reader.readAsText(file);
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
    
    // 处理事件顺序违规事件
    socket.on('event_order_violation', (data) => {
        const { violation, current_order, expected_order } = data;
        const violationEntry = document.createElement('div');
        violationEntry.className = 'log-entry event-order-violation';
        violationEntry.innerHTML = `
            <span class="log-platform error">[事件顺序错误]</span>
            <span class="log-message">
                <strong>错误信息:</strong> ${violation.message}<br>
                <strong>当前事件:</strong> ${violation.current_event}<br>
                <strong>缺失事件:</strong> ${violation.missing_event}<br>
                <strong>当前顺序:</strong> ${current_order.join(' → ')}<br>
                <strong>预期顺序:</strong> ${expected_order.join(' → ')}
            </span>
        `;
        behaviorLogContainer.appendChild(violationEntry);
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

    startButton.addEventListener('click', () => {
        const platform = platformSelector.value;
        const tag = tagFilter.value.trim();
        saveTagToHistory(tag); // Save tag to history
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

    // Initial load of tag history
    loadTagHistory();
});

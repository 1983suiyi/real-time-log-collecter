document.addEventListener('DOMContentLoaded', () => {
    const socket = io(`http://${window.location.hostname}:${window.location.port}`);

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
                configEditor.value = JSON.stringify(config, null, 2);
            })
            .catch(err => {
                addLogMessage({ platform: 'system', message: `Error loading configuration: ${err.message}` });
            });
    };

    const saveConfiguration = () => {
        try {
            const configText = configEditor.value;
            const config = JSON.parse(configText);
            
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
            })
            .catch(err => {
                addLogMessage({ platform: 'system', message: `Error saving configuration: ${err.message}` });
            });
        } catch (error) {
            addLogMessage({ platform: 'system', message: `Invalid JSON format: ${error.message}` });
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
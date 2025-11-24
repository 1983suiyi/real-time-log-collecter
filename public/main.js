document.addEventListener('DOMContentLoaded', () => {
    // 获取并显示当前配置内容
    fetchAndDisplayConfig();
    const socket = io();
    window.socket = socket; // 将socket暴露到全局作用域，供Elasticsearch搜索功能使用

    const logContainer = document.getElementById('log-container');
    const behaviorLogContainer = document.getElementById('behavior-log-container');
    const configContainer = document.getElementById('config-container');
    const configContent = document.getElementById('config-content');
    const platformSelector = document.getElementById('platform-filter');
    const tagFilter = document.getElementById('tag-filter');
    const toggleLogButton = document.getElementById('toggle-log');
    let isLogging = false; // 跟踪日志状态
    const clearLogsButton = document.getElementById('clear-logs');
    const configUploadInput = document.getElementById('config-upload');
    const importLogFileInput = document.getElementById('import-log-file');
    const manageConfigButton = document.getElementById('manage-config');
    const configModal = document.getElementById('config-modal');
    const configEditor = document.getElementById('config-editor');
    const saveConfigButton = document.getElementById('save-config');
    const cancelConfigButton = document.getElementById('cancel-config');
    const closeModalButton = document.querySelector('.close');
    const tabButtons = document.querySelectorAll('.tab-button');
    const exportCsvButton = document.getElementById('export-csv');
    const exportHtmlButton = document.getElementById('export-html');
    const exportLogFileButton = document.getElementById('export-log-file');
    const resetEventOrderButton = document.getElementById('reset-event-order');
    
    // 存储所有日志和行为日志的数组，用于导出功能
    let allLogs = [];
    let allBehaviorLogs = [];
    
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
            
            // 如果点击的是配置内容标签，获取并显示最新配置
            if (tabId === 'config-container') {
                fetchAndDisplayConfig();
            }
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

    // reloadConfigButton has been removed

    // 配置文件上传处理
    // 配置文件上传处理
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
                    // 更新配置内容显示
                    fetchAndDisplayConfig();
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
                
    // 导入日志文件处理
    importLogFileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) {
            return;
        }
        
        // 显示加载中提示
        addLogMessage({ platform: 'system', message: `正在导入日志文件: ${file.name}...` });
        
        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result;
            
            // 发送日志内容到服务器进行解析
            fetch('/import-log', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    filename: file.name,
                    content: content,
                    platform: platformSelector.value // 使用当前选择的平台
                }),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`导入失败: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                // 显示导入成功消息
                addLogMessage({ platform: 'system', message: `成功导入日志文件: ${file.name}, 共解析 ${data.lineCount} 行` });
                
                // 切换到日志标签页
                document.querySelector('.tab-button[data-tab="log-container"]').click();
                
                // 清空文件输入，允许再次选择同一文件
                importLogFileInput.value = '';
            })
            .catch(error => {
                 addLogMessage({ platform: 'system', message: `导入日志文件错误: ${error.message}` });
                 importLogFileInput.value = '';
             });
        };
        reader.readAsText(file);
    });
    
    // 重复的configUploadInput事件监听器已删除

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
        
        // 添加日志到数组中，包含时间戳
        const timestamp = new Date().toISOString();
        allLogs.push({
            timestamp,
            platform: platform || 'System',
            message: message
        });
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
        const { behavior, log, validationResults } = data;
        const behaviorEntry = document.createElement('div');
        
        // 检查是否有验证错误
        const hasValidationError = validationResults && 
                                !validationResults.isValid && 
                                validationResults.error;
        
        // 根据是否有验证错误设置不同的CSS类
        behaviorEntry.className = hasValidationError ? 
            'log-entry behavior-triggered validation-error' : 
            'log-entry behavior-triggered';
        
        // 构建HTML内容
        let messageHtml = `
            <strong>${behavior.name}:</strong> ${behavior.description}<br>
            <em>Triggering log:</em> ${log.replace(/\n/g, '<br>')}
        `;
        
        // 如果有验证错误，添加错误信息样式
        if (hasValidationError) {
            messageHtml += `<div class="validation-error-message">验证错误: ${validationResults.error}</div>`;
        }
        
        behaviorEntry.innerHTML = `
            <span class="log-platform behavior">[Behavior Triggered]</span>
            <span class="log-message">
                ${messageHtml}
            </span>
        `;
        
        behaviorLogContainer.appendChild(behaviorEntry);
        behaviorLogContainer.scrollTop = behaviorLogContainer.scrollHeight;
        if (isAutoScrollEnabled) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        // 添加行为日志到数组中，包含时间戳和验证结果
        const timestamp = new Date().toISOString();
        allBehaviorLogs.push({
            timestamp,
            type: 'behavior_triggered',
            name: behavior.name,
            description: behavior.description,
            log: log,
            validationResults: validationResults
        });
    });
    
    // 获取并显示当前配置内容
    function fetchAndDisplayConfig() {
        fetch('/config')
            .then(response => response.json())
            .then(config => {
                // 将配置对象转换为格式化的YAML字符串
                const yamlString = jsyaml.dump(config, {
                    indent: 2,
                    lineWidth: -1 // 不限制行宽
                });
                // 显示在配置内容区域
                configContent.textContent = yamlString;
            })
            .catch(err => {
                configContent.textContent = `获取配置失败: ${err.message}`;
            });
    }
    
    // 处理事件顺序违规事件
    socket.on('event_order_violation', (data) => {
        const { violation, current_order, expected_order, all_groups } = data;
        const violationEntry = document.createElement('div');
        violationEntry.className = 'log-entry event-order-violation';
        
        // 构建分组信息的HTML
        let groupsHtml = '';
        if (all_groups && all_groups.length > 0) {
            groupsHtml = '<strong>事件顺序分组:</strong><br>';
            all_groups.forEach((group, index) => {
                const isViolationGroup = group.includes(violation.current_event);
                const groupClass = isViolationGroup ? 'violation-group' : '';
                groupsHtml += `<span class="${groupClass}">分组 ${index + 1}: ${group.join(' → ')}</span><br>`;
            });
        }
        
        violationEntry.innerHTML = `
            <span class="log-platform error">[事件顺序错误]</span>
            <span class="log-message">
                <strong>错误信息:</strong> ${violation.message}<br>
                <strong>当前事件:</strong> ${violation.current_event}<br>
                <strong>缺失事件:</strong> ${violation.missing_event}<br>
                <strong>当前顺序:</strong> ${current_order.join(' → ')}<br>
                <strong>预期顺序:</strong> ${expected_order.join(' → ')}<br>
                ${groupsHtml}
            </span>
        `;
        behaviorLogContainer.appendChild(violationEntry);
        behaviorLogContainer.scrollTop = behaviorLogContainer.scrollHeight;
        if (isAutoScrollEnabled) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        // 添加事件顺序违规到数组中，包含时间戳
        const timestamp = new Date().toISOString();
        allBehaviorLogs.push({
            timestamp,
            type: 'event_order_violation',
            message: violation.message,
            current_event: violation.current_event,
            missing_event: violation.missing_event,
            current_order: current_order,
            expected_order: expected_order,
            all_groups: all_groups
        });
    });
    
    // 处理事件组完成事件
    socket.on('event_group_completed', (data) => {
        const { group_id, group_name, events, message } = data;
        const completedEntry = document.createElement('div');
        completedEntry.className = 'log-entry event-group-completed';
        
        completedEntry.innerHTML = `
            <span class="log-platform success">[事件组完成]</span>
            <span class="log-message">
                <strong>事件组:</strong> ${data.group_name || group_id}<br>
                <strong>完成事件:</strong> ${events.join(', ')}<br>
                <strong>消息:</strong> ${message}
            </span>
        `;
        behaviorLogContainer.appendChild(completedEntry);
        behaviorLogContainer.scrollTop = behaviorLogContainer.scrollHeight;
        if (isAutoScrollEnabled) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        // 添加事件组完成到数组中，包含时间戳
        const timestamp = new Date().toISOString();
        allBehaviorLogs.push({
            timestamp,
            type: 'event_group_completed',
            group_id: group_id,
            group_name: group_name,
            events: events,
            message: message
        });
    });
    
    // 监听最终检查结果事件
    socket.on('final_check_results', (results) => {
        // 创建结果摘要
        let summaryClass = results.status === 'success' ? 'success' : 'warning';
        let summaryMessage = `<div class="check-result ${summaryClass}">
            <h4>日志文件最终检查结果</h4>
            <p>${results.message}</p>
        </div>`;
        
        // 如果有详细信息，添加到摘要中
        if (results.details && results.details.length > 0) {
            summaryMessage += '<div class="check-details">';
            
            // 处理缺失的必要事件
            const missingEvents = results.details.find(d => d.type === 'missing_required_events');
            if (missingEvents) {
                summaryMessage += `<div class="detail-item">
                    <h5>缺失的必要事件:</h5>
                    <ul>
                        ${missingEvents.events.map(e => `<li>${e}</li>`).join('')}
                    </ul>
                </div>`;
            }
            
            // 处理错误日志
            const errorLogs = results.details.find(d => d.type === 'error_logs');
            if (errorLogs) {
                summaryMessage += `<div class="detail-item">
                    <h5>错误日志:</h5>
                    <p>发现 ${errorLogs.count} 个可能的错误</p>
                </div>`;
            }
            
            // 处理顺序违规
            const orderViolations = results.details.find(d => d.type === 'order_violations');
            if (orderViolations) {
                summaryMessage += `<div class="detail-item">
                    <h5>事件顺序违规:</h5>
                    <ul>
                        ${orderViolations.violations.map(v => `<li>${v.message}</li>`).join('')}
                    </ul>
                </div>`;
            }
            
            // 处理不完整的事件组
            const incompleteGroups = results.details.find(d => d.type === 'incomplete_groups');
            if (incompleteGroups) {
                summaryMessage += `<div class="detail-item">
                    <h5>不完整的事件组:</h5>
                    <ul>
                        ${incompleteGroups.groups.map(g => `<li>${g.group_name}: 缺少 ${g.missing.join(', ')}</li>`).join('')}
                    </ul>
                </div>`;
            }
            
            summaryMessage += '</div>';
        }
        
        // 显示检查结果
        const resultContainer = document.createElement('div');
        resultContainer.className = 'final-check-container';
        resultContainer.innerHTML = summaryMessage;
        
        // 添加到日志容器中
        behaviorLogContainer.appendChild(resultContainer);
        
        // 滚动到底部
        if (isAutoScrollEnabled) {
            behaviorLogContainer.scrollTop = behaviorLogContainer.scrollHeight;
        }
    });
    
    // 处理事件组未完成事件
    socket.on('event_group_incomplete', (data) => {
        const { group_id, group_name, events, triggered, missing_events, message } = data;
        const incompleteEntry = document.createElement('div');
        incompleteEntry.className = 'log-entry event-group-incomplete';
        
        incompleteEntry.innerHTML = `
            <span class="log-platform warning">[事件组未完成]</span>
            <span class="log-message">
                <strong>事件组:</strong> ${data.group_name || group_id}<br>
                <strong>已触发事件:</strong> ${triggered.join(', ') || '无'}<br>
                <strong>缺失事件:</strong> ${missing_events.join(', ')}<br>
                <strong>消息:</strong> ${message}
            </span>
        `;
        behaviorLogContainer.appendChild(incompleteEntry);
        behaviorLogContainer.scrollTop = behaviorLogContainer.scrollHeight;
        if (isAutoScrollEnabled) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        // 添加事件组未完成到数组中，包含时间戳
        const timestamp = new Date().toISOString();
        allBehaviorLogs.push({
            timestamp,
            type: 'event_group_incomplete',
            group_id: group_id,
            group_name: group_name,
            events: events,
            triggered: triggered,
            missing_events: missing_events,
            message: message
        });
    });

    socket.on('logging_status', (data) => {
        const { active } = data;
        updateLoggingStatus(active);
        if (!active) {
            addLogMessage({ platform: 'system', message: '日志收集已停止，正在检查事件组状态...' });
        }
    });

    function updateLoggingStatus(isActive) {
        const statusIndicator = document.getElementById('loggingStatus');
        if (statusIndicator) {
            statusIndicator.textContent = isActive ? '正在收集日志' : '日志收集已停止';
            statusIndicator.className = isActive ? 'status-active' : 'status-inactive';
        }
        
        // 更新按钮文本、样式和日志状态
        isLogging = isActive;
        if (toggleLogButton) {
            toggleLogButton.textContent = isActive ? 'Stop Logging' : 'Start Logging';
            if (isActive) {
                toggleLogButton.classList.add('logging');
            } else {
                toggleLogButton.classList.remove('logging');
            }
        }
    }

    toggleLogButton.addEventListener('click', () => {
        if (!isLogging) {
            // 开始日志收集
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
            .then(text => {
                addLogMessage({ platform: 'system', message: text });
                toggleLogButton.textContent = 'Stop Logging';
                toggleLogButton.classList.add('logging');
                isLogging = true;
            })
            .catch(err => addLogMessage({ platform: 'system', message: `Error: ${err.message}` }));
        } else {
            // 停止日志收集
            fetch('/stop-log', {
                method: 'POST',
            })
            .then(response => response.text())
            .then(text => {
                addLogMessage({ platform: 'system', message: text });
                toggleLogButton.textContent = 'Start Logging';
                toggleLogButton.classList.remove('logging');
                isLogging = false;
            })
            .catch(err => addLogMessage({ platform: 'system', message: `Error: ${err.message}` }));
        }
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
    
    // 导出CSV功能
    exportCsvButton.addEventListener('click', () => {
        // 确定当前激活的标签页
        const activeTab = document.querySelector('.tab-button.active').getAttribute('data-tab');
        let dataToExport = [];
        let filename = '';
        
        if (activeTab === 'log-container') {
            // 导出系统日志
            dataToExport = allLogs;
            filename = `system_logs_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
            
            // 创建CSV内容
            let csvContent = 'Timestamp,Platform,Message\n';
            dataToExport.forEach(log => {
                // 处理CSV中的特殊字符
                const message = log.message.replace(/"/g, '""').replace(/\n/g, ' ');
                csvContent += `"${log.timestamp}","${log.platform}","${message}"\n`;
            });
            
            // 创建并下载CSV文件
            downloadFile(csvContent, filename, 'text/csv');
        } else {
            // 导出行为日志
            dataToExport = allBehaviorLogs;
            filename = `behavior_logs_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
            
            // 创建CSV内容
            let csvContent = 'Timestamp,Type,Name,Description,Message,Current Event,Missing Event,Group ID,Events,Triggered Events\n';
            dataToExport.forEach(log => {
                if (log.type === 'behavior_triggered') {
                    // 处理CSV中的特殊字符
                    const description = log.description.replace(/"/g, '""').replace(/\n/g, ' ');
                    const logText = log.log.replace(/"/g, '""').replace(/\n/g, ' ');
                    csvContent += `"${log.timestamp}","${log.type}","${log.name}","${description}","${logText}","","","","",""\n`;
                } else if (log.type === 'event_order_violation') {
                    // 处理CSV中的特殊字符
                    const message = log.message.replace(/"/g, '""').replace(/\n/g, ' ');
                    csvContent += `"${log.timestamp}","${log.type}","","","${message}","${log.current_event}","${log.missing_event}","","",""\n`;
                } else if (log.type === 'event_group_completed') {
                    // 处理CSV中的特殊字符
                    const message = log.message.replace(/"/g, '""').replace(/\n/g, ' ');
                    const events = log.events ? log.events.join(', ').replace(/"/g, '""') : '';
                    csvContent += `"${log.timestamp}","${log.type}","","","${message}","","","${log.group_id}","${events}",""\n`;
                } else if (log.type === 'event_group_incomplete') {
                    // 处理CSV中的特殊字符
                    const message = log.message.replace(/"/g, '""').replace(/\n/g, ' ');
                    const events = log.events ? log.events.join(', ').replace(/"/g, '""') : '';
                    const triggered = log.triggered ? log.triggered.join(', ').replace(/"/g, '""') : '';
                    const missing = log.missing_events ? log.missing_events.join(', ').replace(/"/g, '""') : '';
                    csvContent += `"${log.timestamp}","${log.type}","","","${message}","","${missing}","${log.group_id}","${events}","${triggered}"\n`;
                }
            });
            
            // 创建并下载CSV文件
            downloadFile(csvContent, filename, 'text/csv');
        }
        
        addLogMessage({ platform: 'system', message: `已导出CSV文件: ${filename}` });
    });
    
    // 导出HTML报告功能
    exportHtmlButton.addEventListener('click', () => {
        // 确定当前激活的标签页
        const activeTab = document.querySelector('.tab-button.active').getAttribute('data-tab');
        let dataToExport = [];
        let filename = '';
        let reportTitle = '';
        let reportContent = '';
        
        const currentDate = new Date();
        const formattedDate = currentDate.toLocaleDateString();
        const formattedTime = currentDate.toLocaleTimeString();
        
    // 重置事件顺序
    resetEventOrderButton.addEventListener('click', () => {
        fetch('/reset-event-order', {
            method: 'POST',
        })
        .then(response => response.text())
        .then(text => {
            addLogMessage({ platform: 'system', message: '事件顺序追踪已重置' });
        })
        .catch(err => addLogMessage({ platform: 'system', message: `错误: ${err.message}` }));
    });
        
        if (activeTab === 'log-container') {
            // 导出系统日志
            dataToExport = allLogs;
            reportTitle = '系统日志报告';
            filename = `system_logs_report_${new Date().toISOString().replace(/[:.]/g, '-')}.html`;
            
            // 创建HTML内容
            reportContent = `
                <h2>系统日志统计</h2>
                <div class="stats">
                    <div class="stat-item">
                        <span class="stat-label">总日志数:</span>
                        <span class="stat-value">${dataToExport.length}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">平台分布:</span>
                        <div class="stat-chart">
                            ${generatePlatformStats(dataToExport)}
                        </div>
                    </div>
                </div>
                
                <h2>日志详情</h2>
                <table>
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>平台</th>
                            <th>消息</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${dataToExport.map(log => `
                            <tr class="${log.platform.toLowerCase()}">
                                <td>${new Date(log.timestamp).toLocaleString()}</td>
                                <td>${log.platform}</td>
                                <td>${log.message.replace(/\n/g, '<br>')}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } else {
            // 导出行为日志
            dataToExport = allBehaviorLogs;
            reportTitle = '行为日志报告';
            filename = `behavior_logs_report_${new Date().toISOString().replace(/[:.]/g, '-')}.html`;
            
            // 统计行为触发和事件顺序违规的数量
            const behaviorCount = dataToExport.filter(log => log.type === 'behavior_triggered').length;
            const violationCount = dataToExport.filter(log => log.type === 'event_order_violation').length;
            
            // 创建HTML内容
            reportContent = `
                <h2>行为日志统计</h2>
                <div class="stats">
                    <div class="stat-item">
                        <span class="stat-label">总行为触发:</span>
                        <span class="stat-value">${behaviorCount}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">事件顺序违规:</span>
                        <span class="stat-value error">${violationCount}</span>
                    </div>
                </div>
                
                ${violationCount > 0 ? `
                <h2>事件顺序违规详情</h2>
                <table>
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>错误信息</th>
                            <th>当前事件</th>
                            <th>缺失事件</th>
                            <th>当前顺序</th>
                            <th>预期顺序</th>
                            <th>事件顺序分组</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${dataToExport.filter(log => log.type === 'event_order_violation').map(log => `
                            <tr class="violation">
                                <td>${new Date(log.timestamp).toLocaleString()}</td>
                                <td>${log.message}</td>
                                <td>${log.current_event}</td>
                                <td>${log.missing_event}</td>
                                <td>${log.current_order.join(' → ')}</td>
                                <td>${log.expected_order.join(' → ')}</td>
                                <td>
                                    ${log.group_name ? `<div class="violation-group">${log.group_name}</div>` : ''}
                                    ${log.all_groups ? log.all_groups.map((group, index) => {
                                        const isViolationGroup = group.includes(log.current_event);
                                        return `<div class="${isViolationGroup ? 'violation-group' : ''}">
                                            分组 ${index + 1}: ${group.join(' → ')}
                                        </div>`;
                                    }).join('') : ''}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                ` : ''}
                
                ${dataToExport.filter(log => log.type === 'event_group_completed').length > 0 ? `
                <h2>事件组完成详情</h2>
                <table>
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>事件组</th>
                            <th>完成事件</th>
                            <th>消息</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${dataToExport.filter(log => log.type === 'event_group_completed').map(log => `
                            <tr class="success">
                                <td>${new Date(log.timestamp).toLocaleString()}</td>
                                <td>${log.group_name || log.group_id}</td>
                                <td>${log.events.join(', ')}</td>
                                <td>${log.message}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                ` : ''}
                
                ${dataToExport.filter(log => log.type === 'event_group_incomplete').length > 0 ? `
                <h2>事件组未完成详情</h2>
                <table>
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>事件组</th>
                            <th>已触发事件</th>
                            <th>缺失事件</th>
                            <th>消息</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${dataToExport.filter(log => log.type === 'event_group_incomplete').map(log => `
                            <tr class="warning">
                                <td>${new Date(log.timestamp).toLocaleString()}</td>
                                <td>${log.group_name || log.group_id}</td>
                                <td>${log.triggered.join(', ') || '无'}</td>
                                <td>${log.missing_events.join(', ')}</td>
                                <td>${log.message}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                ` : ''}
                
                <h2>行为触发详情</h2>
                <table>
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>类型</th>
                            <th>名称</th>
                            <th>描述</th>
                            <th>触发日志</th>
                            <th>事件顺序状态</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${dataToExport.filter(log => log.type === 'behavior_triggered').map(log => {
                            // 查找与此行为相关的事件顺序违规
                            const relatedViolations = dataToExport.filter(v => 
                                v.type === 'event_order_violation' && 
                                v.current_event === log.name
                            );
                            
                            return `
                            <tr class="behavior">
                                <td>${new Date(log.timestamp).toLocaleString()}</td>
                                <td>行为触发</td>
                                <td>${log.name}</td>
                                <td>${log.description}</td>
                                <td class="${log.level === 'error' || log.level === 'critical' ? 'error-text' : ''}">${log.log.replace(/\n/g, '<br>')}</td>
                                <td>
                                    ${relatedViolations.length > 0 ? 
                                        `<div class="error-text">顺序错误: ${relatedViolations.map(v => 
                                            `缺少事件 "${v.missing_event}"，当前顺序: ${v.current_order.join(' → ')}`
                                        ).join('<br>')}</div>` : 
                                        '正常'
                                    }
                                </td>
                            </tr>
                        `}).join('')}
                    </tbody>
                </table>
            `;
        }
        
        // 生成完整的HTML报告
        const htmlReport = generateHtmlReport(reportTitle, reportContent, formattedDate, formattedTime);
        
        // 创建并下载HTML文件
        downloadFile(htmlReport, filename, 'text/html');
        
        addLogMessage({ platform: 'system', message: `已导出HTML报告: ${filename}` });
    });
    
    // 生成平台统计图表的HTML
    function generatePlatformStats(logs) {
        const platforms = {};
        logs.forEach(log => {
            const platform = log.platform;
            if (!platforms[platform]) {
                platforms[platform] = 0;
            }
            platforms[platform]++;
        });
        
        let html = '<div class="platform-stats">';
        for (const platform in platforms) {
            const percentage = (platforms[platform] / logs.length * 100).toFixed(1);
            html += `
                <div class="platform-stat">
                    <div class="platform-name ${platform.toLowerCase()}">${platform}</div>
                    <div class="platform-bar">
                        <div class="platform-bar-fill ${platform.toLowerCase()}" style="width: ${percentage}%;"></div>
                    </div>
                    <div class="platform-count">${platforms[platform]} (${percentage}%)</div>
                </div>
            `;
        }
        html += '</div>';
        return html;
    }
    
    // 生成完整的HTML报告
    function generateHtmlReport(title, content, date, time) {
        return `
        <!DOCTYPE html>
        <html lang="zh">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>${title}</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                    color: #333;
                }
                .report-container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: #fff;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    padding: 20px;
                }
                .report-header {
                    border-bottom: 1px solid #eee;
                    padding-bottom: 20px;
                    margin-bottom: 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .report-title {
                    font-size: 24px;
                    color: #333;
                    margin: 0;
                }
                .report-meta {
                    color: #666;
                    font-size: 14px;
                }
                h2 {
                    color: #444;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                    margin-top: 30px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    font-size: 14px;
                }
                th, td {
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #eee;
                }
                th {
                    background-color: #f8f8f8;
                    font-weight: 600;
                }
                tr:hover {
                    background-color: #f9f9f9;
                }
                .android {
                    color: #3ddc84;
                }
                .ios {
                    color: #007aff;
                }
                .harmonyos {
                    color: #c71585;
                }
                .system {
                    color: #666;
                }
                .behavior {
                    color: #333; /* 正常事件文字颜色改为黑色 */
                }
                .violation {
                    color: #f44336; /* 失败或异常事件文字改为红色 */
                    background-color: rgba(244, 67, 54, 0.05);
                }
                .warning {
                    color: #f44336; /* 失败或异常事件文字改为红色 */
                    background-color: rgba(255, 193, 7, 0.05);
                }
                .success {
                    color: #333; /* 正常事件文字颜色改为黑色 */
                    background-color: rgba(40, 167, 69, 0.05);
                }
                .error {
                    color: #f44336;
                }
                .error-text {
                    color: #f44336;
                    font-weight: bold;
                }
                .stats {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 20px;
                    margin-top: 20px;
                }
                .stat-item {
                    background-color: #f8f8f8;
                    border-radius: 8px;
                    padding: 15px;
                    flex: 1;
                    min-width: 200px;
                }
                .stat-label {
                    font-size: 14px;
                    color: #666;
                    display: block;
                    margin-bottom: 5px;
                }
                .stat-value {
                    font-size: 24px;
                    font-weight: bold;
                    color: #333;
                }
                .platform-stats {
                    width: 100%;
                    margin-top: 10px;
                }
                .platform-stat {
                    margin-bottom: 10px;
                }
                .platform-name {
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                .platform-bar {
                    height: 20px;
                    background-color: #eee;
                    border-radius: 10px;
                    overflow: hidden;
                }
                .platform-bar-fill {
                    height: 100%;
                    border-radius: 10px;
                }
                .platform-bar-fill.android {
                    background-color: #3ddc84;
                }
                .platform-bar-fill.ios {
                    background-color: #007aff;
                }
                .platform-bar-fill.harmonyos {
                    background-color: #c71585;
                }
                .platform-bar-fill.system {
                    background-color: #666;
                }
                .platform-count {
                    font-size: 12px;
                    color: #666;
                    margin-top: 5px;
                    text-align: right;
                }
                @media print {
                    body {
                        background-color: #fff;
                    }
                    .report-container {
                        box-shadow: none;
                        max-width: 100%;
                    }
                }
            </style>
        </head>
        <body>
            <div class="report-container">
                <div class="report-header">
                    <h1 class="report-title">${title}</h1>
                    <div class="report-meta">
                        生成日期: ${date}<br>
                        生成时间: ${time}
                    </div>
                </div>
                <div class="report-content">
                    ${content}
                </div>
            </div>
        </body>
        </html>
        `;
    }
    
    // 导出日志文件功能
    exportLogFileButton.addEventListener('click', () => {
        // 确定当前激活的标签页
        const activeTab = document.querySelector('.tab-button.active').getAttribute('data-tab');
        let dataToExport = [];
        let filename = '';
        let content = '';
        
        if (activeTab === 'log-container') {
            // 导出系统日志
            dataToExport = allLogs;
            filename = `system_logs_${new Date().toISOString().replace(/[:.]/g, '-')}.log`;
            
            // 创建日志文件内容
            content = dataToExport.map(log => {
                const timestamp = new Date(log.timestamp).toLocaleString();
                return `[${timestamp}] [${log.platform}] ${log.message}`;
            }).join('\n');
        } else if (activeTab === 'behavior-log-container') {
            // 导出行为日志
            dataToExport = allBehaviorLogs;
            filename = `behavior_logs_${new Date().toISOString().replace(/[:.]/g, '-')}.log`;
            
            // 创建行为日志文件内容
            content = dataToExport.map(log => {
                const timestamp = new Date(log.timestamp).toLocaleString();
                if (log.type === 'behavior_triggered') {
                    return `[${timestamp}] [${log.type}] 行为名称: ${log.name}\n描述: ${log.description}\n日志: ${log.log}`;
                } else if (log.type === 'event_order_violation') {
                    return `[${timestamp}] [${log.type}] ${log.message}\n当前事件: ${log.current_event}\n缺失事件: ${log.missing_event}`;
                } else if (log.type === 'event_group_completed') {
                    const events = log.events ? log.events.join(', ') : '';
                    return `[${timestamp}] [${log.type}] ${log.message}\n组ID: ${log.group_id}\n事件: ${events}`;
                } else if (log.type === 'event_group_incomplete') {
                    const events = log.events ? log.events.join(', ') : '';
                    const triggered = log.triggered ? log.triggered.join(', ') : '';
                    const missing = log.missing_events ? log.missing_events.join(', ') : '';
                    return `[${timestamp}] [${log.type}] ${log.message}\n组ID: ${log.group_id}\n事件: ${events}\n已触发: ${triggered}\n缺失: ${missing}`;
                }
                return `[${timestamp}] [${log.type}] ${JSON.stringify(log)}`;
            }).join('\n\n');
        }
        
        // 创建并下载日志文件
        if (content) {
            downloadFile(content, filename, 'text/plain');
            addLogMessage({ platform: 'system', message: `已导出日志文件: ${filename}` });
        }
    });
    
    // 通用文件下载函数
    function downloadFile(content, filename, contentType) {
        const blob = new Blob([content], { type: contentType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 100);
    }
});

// Elasticsearch搜索功能
class ElasticsearchSearch {
    constructor() {
        this.searching = false;
        this.initializeElements();
        this.initializeEventListeners();
        this.initializeSocketHandlers();
    }
    
    initializeElements() {
        this.searchBtn = document.getElementById('es-search-btn');
        this.stopBtn = document.getElementById('es-search-stop');
        this.indexNameInput = document.getElementById('es-index-name');
        this.userIdInput = document.getElementById('es-user-id');
        this.startTimeInput = document.getElementById('es-start-time');
        this.endTimeInput = document.getElementById('es-end-time');
        this.envSelect = document.getElementById('es-env-select');
    }
    
    initializeEventListeners() {
        if (this.searchBtn) {
            this.searchBtn.addEventListener('click', () => this.startSearch());
        }
        if (this.stopBtn) {
            this.stopBtn.addEventListener('click', () => this.stopSearch());
        }
        
        // 设置默认时间范围（最近24小时）
        this.setDefaultTimeRange();
    }
    
    initializeSocketHandlers() {
        // 监听搜索进度更新
        if (window.socket) {
            window.socket.on('es_search_progress', (data) => {
                this.updateProgress(data);
            });
            
            window.socket.on('es_search_complete', (data) => {
                this.handleSearchComplete(data);
            });
            
            // 监听Elasticsearch日志消息
            window.socket.on('log', (data) => {
                if (data.platform === 'elasticsearch' || data.platform === 'system') {
                    // 将Elasticsearch相关的日志显示在界面上
                    this.displayEsLog(data);
                }
            });
        }
    }
    
    setDefaultTimeRange() {
        const now = new Date();
        const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        
        if (this.startTimeInput) {
            this.startTimeInput.value = this.formatDateTimeLocal(yesterday);
        }
        if (this.endTimeInput) {
            this.endTimeInput.value = this.formatDateTimeLocal(now);
        }
    }
    
    formatDateTimeLocal(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${year}-${month}-${day}T${hours}:${minutes}`;
    }
    
    async startSearch() {
        // 验证输入
        if (!this.validateInputs()) {
            return;
        }
        
        // 准备搜索参数
        const requestId = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`;
        const searchParams = {
            index_name: this.indexNameInput.value.trim(),
            user_id: this.userIdInput.value.trim(),
            start_time: this.startTimeInput.value,
            end_time: this.endTimeInput.value,
            platform: 'elasticsearch',
            env: this.envSelect.value || 'sandbox',
            request_id: requestId
        };
        
        // 转换为ISO格式时间
        searchParams.start_time = new Date(searchParams.start_time).toISOString();
        searchParams.end_time = new Date(searchParams.end_time).toISOString();

        this.showMessage(`[请求ID ${requestId}] ES搜索请求参数:\n` + JSON.stringify({
            index_name: searchParams.index_name,
            user_id: searchParams.user_id,
            start_time: searchParams.start_time,
            end_time: searchParams.end_time,
            env: searchParams.env
        }, null, 2), 'info');
        
        this.setSearchingState(true);
        
        try {
            const response = await fetch('/api/es/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(searchParams)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage(`搜索已启动: ${result.message}`, 'success');
            } else {
                this.showMessage(`搜索启动失败: ${result.message}`, 'error');
                this.setSearchingState(false);
            }
        } catch (error) {
            this.showMessage(`搜索请求失败: ${error.message}`, 'error');
            this.setSearchingState(false);
        }
    }
    
    async stopSearch() {
        try {
            const response = await fetch('/api/es/search/stop', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage('搜索已停止', 'info');
            } else {
                this.showMessage(`停止搜索失败: ${result.message}`, 'error');
            }
        } catch (error) {
            this.showMessage(`停止搜索请求失败: ${error.message}`, 'error');
        }
    }
    
    validateInputs() {
        if (!this.indexNameInput.value.trim()) {
            this.showMessage('请输入索引名称', 'error');
            return false;
        }
        
        if (!this.userIdInput.value.trim()) {
            this.showMessage('请输入用户ID', 'error');
            return false;
        }
        
        if (!this.startTimeInput.value) {
            this.showMessage('请选择开始时间', 'error');
            return false;
        }
        
        if (!this.endTimeInput.value) {
            this.showMessage('请选择结束时间', 'error');
            return false;
        }
        
        // 验证时间范围
        const startTime = new Date(this.startTimeInput.value);
        const endTime = new Date(this.endTimeInput.value);
        
        if (startTime >= endTime) {
            this.showMessage('开始时间必须早于结束时间', 'error');
            return false;
        }
        
        return true;
    }
    
    setSearchingState(searching) {
        this.searching = searching;
        
        if (this.searchBtn) {
            this.searchBtn.style.display = searching ? 'none' : 'inline-block';
        }
        if (this.stopBtn) {
            this.stopBtn.style.display = searching ? 'inline-block' : 'none';
        }
        
        // 禁用输入框
        const inputs = [this.indexNameInput, this.userIdInput, this.startTimeInput, this.endTimeInput, this.envSelect];
        inputs.forEach(input => {
            if (input) {
                input.disabled = searching;
            }
        });
    }
    
    updateProgress(data) {
        const progress = Math.round(data.progress * 100);
        this.showMessage(`搜索进度: ${progress}% (${data.processed}/${data.total})`, 'info');
    }
    
    handleSearchComplete(data) {
        this.setSearchingState(false);
        
        if (data.success) {
            this.showMessage(`搜索完成: ${data.message}`, 'success');
        } else {
            this.showMessage(`搜索失败: ${data.message}`, 'error');
        }
    }
    
    displayEsLog(data) {
        // 将Elasticsearch日志显示在日志容器中
        const logContainer = document.getElementById('log-container');
        if (logContainer) {
            const entry = document.createElement('div');
            entry.className = 'log-entry es-result';
            entry.innerHTML = `
                <span class="timestamp">${new Date().toLocaleTimeString()}</span>
                <span class="platform">[${data.platform.toUpperCase()}]</span>
                <span class="message">${data.message}</span>
            `;
            logContainer.appendChild(entry);
            
            // 自动滚动到底部
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    }
    
    showMessage(message, type = 'info') {
        if (window.socket) {
            window.socket.emit('log', {
                platform: 'system',
                message: `[ES搜索] ${message}`,
                level: type
            });
        }
        this.displayEsLog({ platform: 'system', message: `[ES搜索] ${message}` });
        console.log(`[ES Search ${type.toUpperCase()}] ${message}`);
    }
}

// 初始化Elasticsearch搜索功能
document.addEventListener('DOMContentLoaded', () => {
    if (window.socket) {
        window.esSearch = new ElasticsearchSearch();
    } else {
        // 如果socket还未初始化，等待一段时间再初始化
        setTimeout(() => {
            if (window.socket) {
                window.esSearch = new ElasticsearchSearch();
            }
        }, 1000);
    }
});
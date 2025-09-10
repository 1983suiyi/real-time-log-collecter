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
    const exportCsvButton = document.getElementById('export-csv');
    const exportHtmlButton = document.getElementById('export-html');
    
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
            let csvContent = 'Timestamp,Type,Name,Description,Message,Current Event,Missing Event\n';
            dataToExport.forEach(log => {
                if (log.type === 'behavior_triggered') {
                    // 处理CSV中的特殊字符
                    const description = log.description.replace(/"/g, '""').replace(/\n/g, ' ');
                    const logText = log.log.replace(/"/g, '""').replace(/\n/g, ' ');
                    csvContent += `"${log.timestamp}","${log.type}","${log.name}","${description}","${logText}","",""\n`;
                } else if (log.type === 'event_order_violation') {
                    // 处理CSV中的特殊字符
                    const message = log.message.replace(/"/g, '""').replace(/\n/g, ' ');
                    csvContent += `"${log.timestamp}","${log.type}","","","${message}","${log.current_event}","${log.missing_event}"\n`;
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
                
                <h2>行为触发详情</h2>
                <table>
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>类型</th>
                            <th>名称</th>
                            <th>描述</th>
                            <th>触发日志</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${dataToExport.filter(log => log.type === 'behavior_triggered').map(log => `
                            <tr class="behavior">
                                <td>${new Date(log.timestamp).toLocaleString()}</td>
                                <td>行为触发</td>
                                <td>${log.name}</td>
                                <td>${log.description}</td>
                                <td>${log.log.replace(/\n/g, '<br>')}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                
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
                    color: #ff9800;
                }
                .violation {
                    color: #f44336;
                    background-color: rgba(244, 67, 54, 0.05);
                }
                .error {
                    color: #f44336;
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

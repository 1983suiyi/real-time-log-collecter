const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const { spawn } = require('child_process');
const cors = require('cors'); // Import cors
const fs = require('fs');
const yaml = require('js-yaml');
const path = require('path');


// Load behavior configuration
let behaviorConfig = { behaviors: [] };
try {
    const configData = fs.readFileSync('config.yaml', 'utf8');
    behaviorConfig = yaml.load(configData);
} catch (error) {
    console.error('Error reading or parsing config.yaml:', error);
}

const app = express();
const server = http.createServer(app);

// Configure CORS for Socket.IO
const io = socketIo(server, {
    cors: {
        origin: "*", // Allow all origins for simplicity. In production, restrict this.
        methods: ["GET", "POST"]
    }
});

const PORT = process.env.PORT || 3000;

let logProcess = null;

// Middlewares
app.use(cors()); // Use cors middleware for Express
app.use(express.static('public'));
app.use(express.json());

// Endpoint to get current configuration
app.get('/config', (req, res) => {
    res.json(behaviorConfig);
});

// Endpoint to update configuration
app.post('/config', (req, res) => {
    try {
        const newConfig = req.body;
        // Validate the configuration structure
        if (!newConfig.behaviors || !Array.isArray(newConfig.behaviors)) {
            return res.status(400).send('Invalid configuration format.');
        }
        
        behaviorConfig = newConfig;
        
        // Save the updated configuration to config.yaml
        const yamlStr = yaml.dump(behaviorConfig);
        fs.writeFileSync('config.yaml', yamlStr, 'utf8');
        
        res.json({ success: true, message: 'Configuration updated successfully.' });
    } catch (error) {
        console.error('Error updating configuration:', error);
        res.status(500).json({ success: false, message: 'Failed to update configuration.' });
    }
});

// Elasticsearch搜索API端点
app.post('/api/es/search', (req, res) => {
    try {
        const { index_name, user_id, start_time, end_time, platform, env, query_template, request_id, log_param } = req.body;
        
        // 验证必需参数
        if (!index_name || !user_id || !start_time || !end_time) {
            return res.status(400).json({ 
                success: false, 
                message: '缺少必需参数: index_name, user_id, start_time, end_time' 
            });
        }
        
        // 验证时间格式
        const startDate = new Date(start_time);
        const endDate = new Date(end_time);
        
        if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
            return res.status(400).json({ 
                success: false, 
                message: '无效的时间格式' 
            });
        }
        
        if (startDate >= endDate) {
            return res.status(400).json({ 
                success: false, 
                message: '开始时间必须早于结束时间' 
            });
        }
        
        // 在UI打印请求参数
        io.emit('log', {
            platform: 'system',
            message: `[请求ID ${request_id || '-'}] ES搜索请求参数:\n` + JSON.stringify({ index_name, user_id, start_time, end_time, env, platform, log_param }, null, 2)
        });

        // 调用Python Elasticsearch搜索服务
        const pythonScript = path.join(__dirname, 'ep_py', 'es_search_cli.py');
        const args = [
            pythonScript,
            '--mode', 'api',
            '--index', index_name,
            '--user_id', user_id,
            '--start_time', start_time,
            '--end_time', end_time,
            '--platform', platform || 'elasticsearch',
            '--env', env || 'sandbox', // 使用传入的环境参数，默认为sandbox
            '--output', 'json'
        ];
        if (log_param) {
            args.push('--log_param');
            args.push(log_param);
        }
        if (query_template) {
            args.push('--query_template');
            args.push(typeof query_template === 'string' ? query_template : JSON.stringify(query_template));
        }
        if (request_id) {
            args.push('--request_id');
            args.push(request_id);
        }
        const pythonProcess = spawn('python3', args);
        
        let searchResult = '';
        let errorOutput = '';
        
        pythonProcess.stdout.on('data', (data) => {
            searchResult += data.toString();
            // 实时发送搜索进度到前端
            try {
                // 尝试解析Python脚本的输出作为进度信息
                const lines = data.toString().split('\n');
                lines.forEach(line => {
                    if (line.trim()) {
                        const trimmed = line.trim();
                        if (trimmed.startsWith('__BEHAVIOR__ ')) {
                            const payload = trimmed.substring('__BEHAVIOR__ '.length);
                            try {
                                const dataObj = JSON.parse(payload);
                                io.emit('behavior_triggered', dataObj);
                            } catch (e) {
                                io.emit('log', { platform: 'system', message: `解析行为触发失败: ${e.message}` });
                            }
                        } else {
                            io.emit('log', {
                                platform: 'system',
                                message: `ES搜索: ${trimmed}`
                            });
                        }
                    }
                });
            } catch (e) {
                // 如果解析失败，发送简化进度
                io.emit('es_search_progress', {
                    progress: 0.5,
                    processed: 0,
                    total: 0,
                    message: '正在搜索Elasticsearch...'
                });
            }
        });
        
        pythonProcess.stderr.on('data', (data) => {
            errorOutput += data.toString();
            console.error(`Elasticsearch搜索错误: ${data}`);
        });
        
        pythonProcess.on('close', (code) => {
            if (code === 0) {
                let parsed = null;
                const text = (searchResult || '').trim();
                const lines = text.split('\n').reverse();
                for (const ln of lines) {
                    const t = ln.trim();
                    if (!t) continue;
                    try {
                        parsed = JSON.parse(t);
                        break;
                    } catch (_) {
                        continue;
                    }
                }
                if (!parsed) {
                    const lastBrace = text.lastIndexOf('{');
                    if (lastBrace !== -1) {
                        const candidate = text.substring(lastBrace);
                        try { parsed = JSON.parse(candidate); } catch (_) {}
                    }
                }
                if (parsed) {
                    io.emit('es_search_complete', {
                        success: true,
                        message: `搜索完成，找到 ${parsed.total || parsed.total_hits || 0} 条记录`,
                        data: parsed
                    });
                } else {
                    io.emit('es_search_complete', {
                        success: false,
                        message: '搜索结果解析失败: 输出中未找到有效JSON块'
                    });
                }
            } else {
                io.emit('es_search_complete', {
                    success: false,
                    message: `Elasticsearch搜索失败 (退出码: ${code}): ${errorOutput}`
                });
            }
        });
        
        res.json({ 
            success: true, 
            message: 'Elasticsearch搜索任务已启动' 
        });
        
    } catch (error) {
        console.error('Elasticsearch搜索API错误:', error);
        res.status(500).json({ 
            success: false, 
            message: `搜索请求处理失败: ${error.message}` 
        });
    }
});

// 停止Elasticsearch搜索API
app.post('/api/es/search/stop', (req, res) => {
    try {
        // 这里需要实现停止搜索的逻辑
        // 由于Python进程管理复杂，暂时返回成功状态
        io.emit('es_search_complete', {
            success: true,
            message: '搜索已停止'
        });
        
        res.json({ 
            success: true, 
            message: '搜索停止请求已发送' 
        });
    } catch (error) {
        console.error('停止搜索API错误:', error);
        res.status(500).json({ 
            success: false, 
            message: `停止搜索失败: ${error.message}` 
        });
    }
});

// Endpoint to reload the behavior configuration
app.post('/reload-config', (req, res) => {
    try {
        const configData = fs.readFileSync('config.yaml', 'utf8');
        behaviorConfig = yaml.load(configData);
        io.emit('log', { platform: 'system', message: 'Configuration reloaded successfully.' });
        res.status(200).send('Configuration reloaded.');
    } catch (error) {
        io.emit('log', { platform: 'system', message: `Error reloading configuration: ${error.message}` });
        res.status(500).send('Error reloading configuration.');
    }
});

// Endpoint to start logging
app.post('/start-log', (req, res) => {
    const { platform, tag } = req.body;

    if (logProcess) {
        return res.status(400).send('A logging process is already running.');
    }

    let command;
    let args;
    const spawnOptions = {};

    if (platform === 'android') {
        command = 'adb';
        args = ['logcat'];
    } else if (platform === 'ios') {
        // NOTE: This requires 'idevicesyslog' to be installed.
        // You can install it via Homebrew: `brew install libimobiledevice`
        command = '/opt/homebrew/bin/idevicesyslog';
        args = []; // idevicesyslog doesn't support direct tag filtering, we'll pipe to grep
        spawnOptions.shell = true;
    } else {
        return res.status(400).send('Invalid platform specified.');
    }

    try {
        logProcess = spawn(command, args, spawnOptions);

        let logStream = logProcess.stdout;

        // If a tag is provided, pipe the output to grep for filtering
        if (tag) {
            const grep = spawn('grep', ['-F', tag]);
            logProcess.stdout.pipe(grep.stdin);
            logStream = grep.stdout;

            grep.stderr.on('data', (data) => {
                io.emit('log', { platform: 'system', message: `Grep ERROR: ${data.toString()}` });
            });
        }

        io.emit('log', { platform: 'system', message: `Starting ${platform} log collection...` });

        logStream.on('data', (data) => {
            const logMessage = data.toString();
            // Send each log line to the frontend
            io.emit('log', { platform, message: logMessage });

            // Analyze log for configured behaviors
            behaviorConfig.behaviors.forEach(behavior => {
                const pattern = new RegExp(behavior.pattern, 'i');
                if (pattern.test(logMessage)) {
                    io.emit('behavior_triggered', { 
                        behavior: behavior,
                        log: logMessage
                    });
                }
            });
        });

        logProcess.stderr.on('data', (data) => {
            // Send errors to the frontend as well
            io.emit('log', { platform: 'system', message: `ERROR: ${data.toString()}` });
        });

        logProcess.on('close', (code) => {
            io.emit('log', { platform: 'system', message: `${platform} log collection stopped. Exit code: ${code}` });
            logProcess = null;
        });
        
        logProcess.on('error', (err) => {
            io.emit('log', { platform: 'system', message: `Failed to start log process: ${err.message}` });
            logProcess = null;
        });

        res.status(200).send(`${platform} logging started.`);

    } catch (error) {
        const errorMessage = `Failed to start process for ${platform}. Make sure the command '${command}' is installed and accessible in your PATH. Error: ${error.message}`;
        io.emit('log', { platform: 'system', message: errorMessage });
        res.status(500).send(errorMessage);
    }
});

// Endpoint to stop logging
app.post('/stop-log', (req, res) => {
    if (logProcess) {
        logProcess.kill('SIGINT'); // Send interrupt signal to gracefully stop the process
        logProcess = null;
        res.status(200).send('Logging process stopped.');
    } else {
        res.status(400).send('No logging process is currently running.');
    }
});




io.on('connection', (socket) => {
    console.log('A client connected to the web UI.');
    socket.on('disconnect', () => {
        console.log('A client disconnected.');
    });
});

server.listen(PORT, () => {
    console.log(`Log viewer server running on http://localhost:${PORT}`);
});
const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const { spawn } = require('child_process');
const cors = require('cors'); // Import cors
const fs = require('fs');

// Load behavior configuration
let behaviorConfig = { behaviors: [] };
try {
    const configData = fs.readFileSync('config.json', 'utf8');
    behaviorConfig = JSON.parse(configData);
} catch (error) {
    console.error('Error reading or parsing config.json:', error);
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
        
        // Save to file
        fs.writeFileSync('config.json', JSON.stringify(newConfig, null, 2));
        
        // Update in-memory configuration
        behaviorConfig = newConfig;
        
        io.emit('log', { platform: 'system', message: 'Configuration updated successfully.' });
        res.status(200).send('Configuration updated.');
    } catch (error) {
        io.emit('log', { platform: 'system', message: `Error updating configuration: ${error.message}` });
        res.status(500).send('Error updating configuration.');
    }
});

// Endpoint to reload the behavior configuration
app.post('/reload-config', (req, res) => {
    try {
        const configData = fs.readFileSync('config.json', 'utf8');
        behaviorConfig = JSON.parse(configData);
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

// Endpoint to get markdown file content
app.get('/markdown/:filename', (req, res) => {
    const filename = req.params.filename;
    
    // Security check: only allow certain markdown files
    const allowedFiles = ['config_examples.md', 'README.md', 'CONFIG_VALIDATION.md'];
    if (!allowedFiles.includes(filename)) {
        return res.status(403).send('Access to this file is not allowed.');
    }
    
    try {
        const content = fs.readFileSync(filename, 'utf8');
        res.json({ content: content, filename: filename });
    } catch (error) {
        res.status(404).send(`File ${filename} not found.`);
    }
});

// Endpoint to list available markdown files
app.get('/markdown', (req, res) => {
    const allowedFiles = ['config_examples.md', 'README.md', 'CONFIG_VALIDATION.md'];
    const availableFiles = allowedFiles.filter(file => {
        try {
            fs.accessSync(file, fs.constants.F_OK);
            return true;
        } catch {
            return false;
        }
    });
    res.json({ files: availableFiles });
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
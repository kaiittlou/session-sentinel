const { app, BrowserWindow } = require('electron')
const { spawn, execSync } = require('child_process')
const http = require('http')
const path = require('path')

let mainWindow
let pythonProcess

function waitForServer(url, callback) {
    const maxAttempts = 50
    let attempts = 0

    const tryConnect = () => {
        attempts++

        http.get(url, () => {
            callback()
        }).on('error', () => {
            if (attempts < maxAttempts) {
                setTimeout(tryConnect, 500)
            } else {
                console.error("Server failed to start.")
            }
        })
    }

    tryConnect()
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1000,
        height: 800,
    })

    waitForServer('http://127.0.0.1:5050', () => {
        mainWindow.loadURL('http://127.0.0.1:5050')
    })
}

app.whenReady().then(() => {
    try {
        execSync("pkill -f main.py")
    } catch (e) {}

    const pythonPath = process.platform === "win32" ? "python" : "python3"
    const scriptPath = path.join(__dirname, "..", "main.py")

    pythonProcess = spawn(pythonPath, [scriptPath])
    pythonProcess.stdout.on('data', (data) => {
        console.log(data.toString())
    })
    
    pythonProcess.stderr.on('data', (data) => {
        console.error(data.toString())
    })

    createWindow()
})

app.on('window-all-closed', () => {
    if (pythonProcess) pythonProcess.kill()
    app.quit()
})
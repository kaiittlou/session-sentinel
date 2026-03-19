const { app, BrowserWindow } = require('electron')
const { spawn } = require('child_process')

let mainWindow
let pythonProcess

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1000,
        height: 800,
    })

    setTimeout(() => {
        mainWindow.loadURL('http://127.0.0.1:5000')
    }, 3000) // wait 3 seconds for Python to start
}

app.whenReady().then(() => {
    pythonProcess = spawn('python3', ['../main.py'])

    pythonProcess.stdout.on('data', (data) => {
        console.log(data.toString())
    })

    createWindow()
})

app.on('window-all-closed', () => {
    if (pythonProcess) pythonProcess.kill()
    app.quit()
})
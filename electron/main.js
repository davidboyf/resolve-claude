const { app, BrowserWindow, shell, ipcMain } = require('electron')
const { spawn } = require('child_process')
const net = require('net')
const path = require('path')
const fs = require('fs')

let mainWindow = null
let loadingWindow = null
let backendProcess = null
let frontendProcess = null

const ROOT = path.join(__dirname, '..')
const BACKEND_DIR = path.join(ROOT, 'backend')
const FRONTEND_DIR = path.join(ROOT, 'frontend')
const VENV_PYTHON = path.join(BACKEND_DIR, 'venv', 'bin', 'python')

// ── Port utilities ────────────────────────────────────────────────

function findFreePort(start = 8765) {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.listen(start, '127.0.0.1', () => {
      const port = server.address().port
      server.close(() => resolve(port))
    })
    server.on('error', () => findFreePort(start + 1).then(resolve))
  })
}

function waitForPort(port, timeout = 45000) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeout
    const check = () => {
      const sock = new net.Socket()
      sock.setTimeout(500)
      sock.on('connect', () => { sock.destroy(); resolve() })
      sock.on('error', () => {
        sock.destroy()
        if (Date.now() > deadline) return reject(new Error(`Port ${port} never opened`))
        setTimeout(check, 600)
      })
      sock.on('timeout', () => {
        sock.destroy()
        if (Date.now() > deadline) return reject(new Error(`Timeout on port ${port}`))
        setTimeout(check, 600)
      })
      sock.connect(port, '127.0.0.1')
    }
    check()
  })
}

// ── Loading window ────────────────────────────────────────────────

function createLoadingWindow() {
  loadingWindow = new BrowserWindow({
    width: 400,
    height: 280,
    frame: false,
    resizable: false,
    transparent: true,
    alwaysOnTop: true,
    webPreferences: { nodeIntegration: false },
  })
  loadingWindow.loadFile(path.join(__dirname, 'loading.html'))
  loadingWindow.center()
}

function setLoadingStatus(msg) {
  if (loadingWindow && !loadingWindow.isDestroyed()) {
    loadingWindow.webContents.executeJavaScript(
      `document.getElementById('status').textContent = ${JSON.stringify(msg)}`
    ).catch(() => {})
  }
}

// ── Main window ───────────────────────────────────────────────────

function createMainWindow(frontendPort) {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#0d0d14',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    icon: path.join(__dirname, 'icon.png'),
  })

  mainWindow.loadURL(`http://localhost:${frontendPort}`)

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.on('closed', () => { mainWindow = null })
}

// ── Backend (Python/FastAPI) ──────────────────────────────────────

async function startBackend(port) {
  const pythonBin = fs.existsSync(VENV_PYTHON) ? VENV_PYTHON : 'python3'

  return new Promise((resolve, reject) => {
    backendProcess = spawn(pythonBin, ['main.py'], {
      cwd: BACKEND_DIR,
      env: {
        ...process.env,
        BACKEND_PORT: String(port),
        PATH: `${path.join(BACKEND_DIR, 'venv', 'bin')}:${process.env.PATH}`,
      },
    })

    backendProcess.stdout.on('data', (d) => {
      const line = d.toString()
      console.log('[backend]', line.trim())
      if (line.includes('Application startup complete') || line.includes('Uvicorn running')) {
        resolve()
      }
    })

    backendProcess.stderr.on('data', (d) => {
      const line = d.toString()
      console.error('[backend err]', line.trim())
      if (line.includes('Application startup complete') || line.includes('Uvicorn running')) {
        resolve()
      }
    })

    backendProcess.on('error', reject)
    backendProcess.on('exit', (code) => {
      if (code !== 0 && code !== null) console.error(`Backend exited with code ${code}`)
    })

    // Fallback: resolve after port is open
    waitForPort(port, 30000).then(resolve).catch(reject)
  })
}

// ── Frontend (Vite dev server) ────────────────────────────────────

async function startFrontend(frontendPort, backendPort) {
  const npmBin = process.platform === 'win32' ? 'npm.cmd' : 'npm'

  frontendProcess = spawn(npmBin, ['run', 'dev'], {
    cwd: FRONTEND_DIR,
    env: {
      ...process.env,
      VITE_PORT: String(frontendPort),
      VITE_BACKEND_PORT: String(backendPort),
      PORT: String(frontendPort),
    },
    shell: true,
  })

  frontendProcess.stdout.on('data', (d) => console.log('[frontend]', d.toString().trim()))
  frontendProcess.stderr.on('data', (d) => console.error('[frontend err]', d.toString().trim()))

  await waitForPort(frontendPort, 30000)
}

// ── App lifecycle ─────────────────────────────────────────────────

app.whenReady().then(async () => {
  createLoadingWindow()

  try {
    setLoadingStatus('Finding available ports…')
    const backendPort = await findFreePort(8765)
    const frontendPort = await findFreePort(5199)

    setLoadingStatus(`Starting backend on :${backendPort}…`)
    await startBackend(backendPort)

    setLoadingStatus(`Starting frontend on :${frontendPort}…`)
    await startFrontend(frontendPort, backendPort)

    setLoadingStatus('Ready!')
    await new Promise(r => setTimeout(r, 400))

    createMainWindow(frontendPort)

    if (loadingWindow && !loadingWindow.isDestroyed()) {
      loadingWindow.close()
      loadingWindow = null
    }

  } catch (err) {
    console.error('Startup error:', err)
    setLoadingStatus(`Error: ${err.message}`)
  }
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (mainWindow === null && frontendProcess) {
    // Reopen window on dock click (macOS)
    findFreePort(5199).then(p => createMainWindow(p))
  }
})

app.on('before-quit', () => {
  if (backendProcess) { backendProcess.kill(); backendProcess = null }
  if (frontendProcess) { frontendProcess.kill(); frontendProcess = null }
})

process.on('exit', () => {
  if (backendProcess) backendProcess.kill()
  if (frontendProcess) frontendProcess.kill()
})

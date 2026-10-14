// Real local browser evidence, using Chrome's DevTools protocol; Node 22+.
// Usage: node scripts/capture_dashboard.mjs PATH_TO_PYTHON PATH_TO_CHROME
import { spawn, execFileSync } from 'node:child_process'
import { mkdir, mkdtemp, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import assert from 'node:assert/strict'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const [python, chrome] = process.argv.slice(2)
if (!python || !chrome) throw new Error('Provide Python and Chrome executable paths.')
const children = []
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))
let socket
let browserLogs = ''
function launch(command, args, options = {}) {
  const child = spawn(command, args, { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'], ...options })
  children.push(child)
  child.on('error', error => { browserLogs += `${error.message}\n` })
  child.stderr.on('data', data => { browserLogs = (browserLogs + data).slice(-6000) })
  child.stdout.on('data', () => {})
  return child
}
async function waitFor(check, label, seconds = 50) {
  const end = Date.now() + seconds * 1000
  while (Date.now() < end) {
    try { const result = await check(); if (result) return result } catch { /* still starting */ }
    await sleep(250)
  }
  throw new Error(`Timed out: ${label}\n${browserLogs}`)
}
try {
  await mkdir(join(root, '.audit-tools'), { recursive: true })
  const profile = await mkdtemp(join(root, '.audit-tools', 'chrome-'))
  launch(python, ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8001', '--workers', '1'], { cwd: join(root, 'backend') })
  await waitFor(async () => (await fetch('http://127.0.0.1:8001/health')).ok, 'backend startup')
  launch(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173', '--strictPort'], {
    cwd: join(root, 'frontend'), env: { ...process.env, VITE_API_URL: 'http://127.0.0.1:8001' },
  })
  await waitFor(async () => (await fetch('http://127.0.0.1:5173/')).ok, 'frontend startup')
  launch(chrome, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--remote-debugging-port=9223', `--user-data-dir=${profile}`, 'about:blank'])
  const target = await waitFor(async () => (await (await fetch('http://127.0.0.1:9223/json')).json()).find(t => t.type === 'page'), 'Chrome DevTools')
  socket = new WebSocket(target.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject })
  const pending = new Map()
  const exceptions = []
  let sequence = 0
  socket.onmessage = ({ data }) => {
    const value = JSON.parse(data)
    if (value.method === 'Runtime.exceptionThrown') exceptions.push(value.params.exceptionDetails.text)
    const request = pending.get(value.id)
    if (request) {
      pending.delete(value.id)
      clearTimeout(request.timer)
      if (value.error) request.reject(new Error(JSON.stringify(value.error)))
      else request.resolve(value.result)
    }
  }
  const command = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)) }, 60000)
    pending.set(id, { resolve, reject, timer })
    socket.send(JSON.stringify({ id, method, params }))
  })
  const evaluate = async expression => {
    const result = await command('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails))
    return result.result.value
  }
  await command('Runtime.enable')
  await command('Page.enable')
  await command('Emulation.setDeviceMetricsOverride', { width: 1512, height: 1180, deviceScaleFactor: 1, mobile: false })
  await command('Page.navigate', { url: 'http://127.0.0.1:5173/' })
  console.log('Dashboard navigated; waiting for database-backed UI.')
  await waitFor(() => evaluate("document.querySelectorAll('.ticket-row').length === 3 && document.querySelector('.balance-main')?.textContent.includes('$160.00')"), 'real tickets and cash rendered')
  const shots = join(root, 'output', 'dashboard_screenshots')
  console.log('Tickets and $160 balance rendered.')
  await mkdir(shots, { recursive: true })
  const captures = []
  for (const [index, ticketId] of [101, 102, 103].entries()) {
    await evaluate(`document.querySelectorAll('.ticket-row')[${index}].click()`)
    await waitFor(() => evaluate(`document.querySelector('.breadcrumb')?.textContent.includes('${ticketId}')`), `ticket ${ticketId} selected`)
    await sleep(400)
    const status = await evaluate("document.querySelector('.title-line .status-pill').textContent.trim()")
    assert.equal(status, 'Resolved')
    assert.equal(await evaluate("document.querySelector('.run-button').disabled"), true)
    assert.equal(await evaluate("Boolean(document.querySelector('.banner-error'))"), false)
    const shot = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
    await writeFile(join(shots, `ticket-${ticketId}.png`), Buffer.from(shot.data, 'base64'))
    captures.push({ ticket_id: ticketId, status, checking: 160, file: `dashboard_screenshots/ticket-${ticketId}.png` })
  }
  await command('Page.reload')
  await waitFor(() => evaluate("document.querySelectorAll('.ticket-row').length === 3 && !!document.querySelector('.outcome-card')"), 'historical review remains visible after reload')
  await command('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true })
  await sleep(500)
  const mobileFits = await evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
  assert.equal(mobileFits, true, 'Mobile layout overflows horizontally')
  await command('Page.navigate', { url: pathToFileURL(join(root, 'output', 'desk_tickets.html')).href })
  await waitFor(() => evaluate("document.querySelectorAll('[role=tab]').length === 5"), 'standalone evidence tabs')
  for (let i = 0; i < 5; i++) {
    assert.equal(await evaluate(`(() => { const tabs = [...document.querySelectorAll('[role=tab]')]; tabs[${i}].click(); return !document.getElementById(tabs[${i}].getAttribute('aria-controls')).hidden; })()`), true)
  }
  assert.deepEqual(exceptions, [], 'Browser runtime exceptions')
  await writeFile(join(root, 'output', 'dashboard_browser_check.json'), JSON.stringify({
    captured_at: new Date().toISOString(), backend: 'http://127.0.0.1:8001', frontend: 'http://127.0.0.1:5173',
    note: 'Separate local validation server; same real working DB and audit. No agents run or payments performed.',
    captures, mobile_width: 390, mobile_no_overflow: mobileFits, reload_summary_visible: true,
    standalone_tabs_passed: 5, runtime_exceptions: exceptions,
  }, null, 2) + '\n')
  console.log('PASS: 3 real dashboard screenshots, ticket selection/status, reload summary, mobile layout, 5 local evidence tabs; no runtime exceptions.')
  await command('Browser.close').catch(() => {})
} finally {
  socket?.close()
  for (const child of children.reverse()) {
    if (child.pid && child.exitCode === null) {
      try { execFileSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' }) } catch { /* already exited */ }
    }
  }
}

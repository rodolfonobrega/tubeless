const { createServer } = require('http')
const http = require('http')
const next = require('next')

const dev = process.env.NODE_ENV !== 'production'
const app = next({ dev })
const handle = app.getRequestHandler()

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
const _url = new URL(BACKEND_URL)
const BACKEND_HOST = _url.hostname
const BACKEND_PORT = _url.port || '8000'

app.prepare().then(() => {
  const upgradeHandler = typeof app.getUpgradeHandler === 'function'
    ? app.getUpgradeHandler()
    : null

  const server = createServer((req, res) => {
    // Proxy /api/ requests directly to bypass Next.js response buffering (breaks SSE)
    if (req.url.startsWith('/api/')) {
      const options = {
        hostname: BACKEND_HOST,
        port: BACKEND_PORT,
        path: req.url,
        method: req.method,
        headers: { ...req.headers, host: `${BACKEND_HOST}:${BACKEND_PORT}` },
      }
      const proxyReq = http.request(options, (proxyRes) => {
        res.writeHead(proxyRes.statusCode, proxyRes.headers)
        proxyRes.pipe(res)
      })
      proxyReq.on('error', () => { res.writeHead(502); res.end('Bad Gateway') })
      req.pipe(proxyReq)
      return
    }

    handle(req, res)
  })

  server.on('upgrade', (req, socket, head) => {
    // Let Next.js handle all WebSocket connections (HMR etc.)
    // Backend WebSocket is not proxied — uvicorn[standard] not installed
    if (upgradeHandler) {
      upgradeHandler(req, socket, head)
    } else {
      socket.destroy()
    }
  })

  server.listen(3000, () => {
    console.log('> Ready on http://localhost:3000')
  })
})

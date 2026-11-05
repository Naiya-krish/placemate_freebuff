/**
 * Same-origin development proxy for hosted previews (Freebuff Cloud, Codespaces).
 *
 * Browser requests hit one public port. `/api/*` is forwarded to the FastAPI server and
 * everything else (including the Next HMR WebSocket) to `next dev` on an internal port.
 * Local Docker and `make dev-local` do not use this file; they expose :3000 and :8000
 * directly. Start with:
 *
 *   NEXT_PUBLIC_API_URL=/api/v1 NEXT_PUBLIC_WS_URL=/api/v1 npm run dev:web
 *   npm run dev:proxy
 */
import http from "node:http";
import httpProxy from "http-proxy";

const PORT = Number(process.env.PROXY_PORT || 3000);
const WEB_TARGET = process.env.WEB_TARGET || "http://127.0.0.1:3001";
const API_TARGET = process.env.API_TARGET || "http://127.0.0.1:8000";
const API_PREFIX = "/api/";

const apiProxy = httpProxy.createProxyServer({ xfwd: true });
const webProxy = httpProxy.createProxyServer({ xfwd: true });

function fail(error, req, res) {
  console.error("proxy.error", req.url, error.message);
  if (res && !res.headersSent && typeof res.writeHead === "function") {
    res.writeHead(502, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ detail: "Preview proxy could not reach the service." }));
  } else if (res && typeof res.destroy === "function") {
    res.destroy();
  }
}

apiProxy.on("error", fail);
webProxy.on("error", fail);

const server = http.createServer((req, res) => {
  const isApi = (req.url || "/").startsWith(API_PREFIX);
  const proxy = isApi ? apiProxy : webProxy;
  proxy.web(req, res, { target: isApi ? API_TARGET : WEB_TARGET });
});

server.on("upgrade", (req, socket, head) => {
  const isApi = (req.url || "/").startsWith(API_PREFIX);
  const proxy = isApi ? apiProxy : webProxy;
  proxy.ws(req, socket, head, { target: isApi ? API_TARGET : WEB_TARGET });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`preview proxy listening on 0.0.0.0:${PORT}`);
  console.log(`  web -> ${WEB_TARGET}`);
  console.log(`  api -> ${API_TARGET}`);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    server.close(() => process.exit(0));
  });
}

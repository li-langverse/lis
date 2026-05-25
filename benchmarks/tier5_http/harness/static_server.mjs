#!/usr/bin/env node
/** Minimal static HTTP/1.1 server for tier-5 oracle bench (Node + Bun). */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const port = Number(process.argv[2]);
const root = path.resolve(process.argv[3]);
if (!Number.isFinite(port) || port <= 0 || !root) {
  console.error("usage: static_server.mjs <port> <doc-root>");
  process.exit(1);
}

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".htm": "text/html; charset=utf-8",
  ".css": "text/css",
  ".js": "application/javascript",
  ".json": "application/json",
  ".bin": "application/octet-stream",
};

function safePath(urlPath) {
  const p = urlPath.split("?")[0] || "/";
  const rel = p === "/" ? "/index.html" : p;
  const fp = path.normalize(path.join(root, rel));
  if (!fp.startsWith(root)) {
    return null;
  }
  return fp;
}

const server = http.createServer((req, res) => {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, { Connection: "close" });
    res.end();
    return;
  }
  const fp = safePath(req.url || "/");
  if (!fp) {
    res.writeHead(400, { Connection: "close" });
    res.end();
    return;
  }
  fs.stat(fp, (err, st) => {
    if (err || !st.isFile()) {
      res.writeHead(404, { Connection: "close" });
      res.end();
      return;
    }
    const ext = path.extname(fp).toLowerCase();
    const ctype = TYPES[ext] || "application/octet-stream";
    if (req.method === "HEAD") {
      res.writeHead(200, {
        "Content-Type": ctype,
        "Content-Length": String(st.size),
        Connection: "keep-alive",
      });
      res.end();
      return;
    }
    res.writeHead(200, {
      "Content-Type": ctype,
      "Content-Length": String(st.size),
      Connection: "keep-alive",
    });
    const stream = fs.createReadStream(fp);
    stream.on("error", () => {
      if (!res.headersSent) {
        res.writeHead(500, { Connection: "close" });
      }
      res.end();
    });
    stream.pipe(res);
  });
});

server.keepAliveTimeout = 65_000;
server.headersTimeout = 66_000;
server.listen(port, "127.0.0.1", () => {
  if (process.env.TIER5_HTTP_SERVER_READY === "1") {
    console.log(`ready ${port}`);
  }
});

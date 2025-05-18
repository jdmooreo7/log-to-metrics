const express = require('express');
const winston = require('winston');
const prom = require('prom-client');
const app = express();
const port = 3000;

// Set up Winston logger
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'app.log' })
  ]
});

// Prometheus metrics
const register = new prom.Registry();
prom.collectDefaultMetrics({ register });

const httpRequestsTotal = new prom.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'path', 'status'],
  registers: [register],
});

const httpRequestDurationMs = new prom.Histogram({
  name: 'http_request_duration_ms',
  help: 'Duration of HTTP requests in ms',
  labelNames: ['method', 'path', 'status'],
  registers: [register],
});

// Middleware to parse JSON requests and track metrics
app.use(express.json());
app.use((req, res, next) => {
  const end = httpRequestDurationMs.startTimer();
  res.on('finish', () => {
    httpRequestsTotal.inc({
      method: req.method,
      path: req.path,
      status: res.statusCode,
    });
    end({ method: req.method, path: req.path, status: res.statusCode });
  });
  next();
});

// Simulate API endpoints
app.get('/api/user', (req, res) => {
  const responseTime = Math.random() * 100;
  logger.info('GET /api/user', { status: 200, responseTime });
  res.status(200).send('User data retrieved');
});

app.post('/api/order', (req, res) => {
  const responseTime = Math.random() * (Math.random() > 0.8 ? 200 : 100);
  if (Math.random() > 0.8) { // Simulate 20% error rate
    logger.error('POST /api/order failed', { status: 500, responseTime });
    res.status(500).send('Order failed');
  } else {
    logger.info('POST /api/order', { status: 200, responseTime });
    res.status(200).send('Order placed');
  }
});

// Prometheus metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

// Start server
app.listen(port, () => {
  logger.info(`Server running at http://localhost:${port}`);
});
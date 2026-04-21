# Ubuntu Deployment Guide

This guide deploys the FDPP EMS backend on Ubuntu with Nginx and Gunicorn, serves the frontend from `frontend/serve_spa.py`, and keeps the biometric WebSocket connector talking to the backend on port `8000`.

## Target Layout

On Ubuntu, use this layout:

```text
/home/attendance/
├── Backend/
│   ├── manage.py
│   ├── fdpp_ems/
│   ├── requirements.txt
│   ├── .env
│   └── venv/
└── frontend/
    ├── serve_spa.py
    ├── build/ or dist/
    └── static assets
```

If your current project lives somewhere else, copy the backend code into `/home/attendance/Backend` and the frontend files into `/home/attendance/frontend`.

## Important Port Plan

Use these ports:

- `8000`: backend ASGI app for API + WebSocket
- `3000`: frontend SPA server from `serve_spa.py`
- `80`: Nginx public entry point

The backend and biometric WebSocket share the same ASGI service on `8000`. The frontend runs separately on `3000` and Nginx proxies traffic to it.

## 1. Install Packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx build-essential
```

If you use Redis or another channel layer backend, install that too.

## 2. Prepare Backend

```bash
cd /home/attendance/Backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn uvicorn[standard]
```

Your backend `.env` should include at least:

```env
SERVER_IP=172.172.172.160
SERVER_PORT=8000
DEVICE_IP=172.172.173.199
DEVICE_PORT=4370
DEVICE_PASSWORD=0
DEVICE_FORCE_UDP=True
DEVICE_OMMIT_PING=False
```

## 3. Run Backend on Port 8000

Use Gunicorn with an ASGI worker so WebSockets work:

```bash
cd /home/attendance/Backend
source venv/bin/activate
gunicorn fdpp_ems.asgi:application \
  --bind 127.0.0.1:8000 \
  -k uvicorn.workers.UvicornWorker \
  --workers 2 \
  --timeout 60
```

That keeps the backend and the biometric WebSocket endpoint on port `8000` internally.

## 4. Run the Biometric WebSocket Connector

Start the connector from the same machine that reaches the device:

```bash
cd /home/attendance/Backend
source venv/bin/activate
python /home/attendance/Backend/biometric_websocket.py
```

It connects to:

```text
ws://172.172.172.160:8000/ws/biometric/
```

## 5. Run the Frontend SPA Server

Copy the built frontend files into `/home/attendance/frontend` and start the SPA server:

```bash
cd /home/attendance/frontend
python3 serve_spa.py --host 127.0.0.1 --port 3000 --dir /home/attendance/frontend
```

You can also use environment variables:

```bash
export SPA_HOST=127.0.0.1
export SPA_PORT=3000
export SPA_DIR=/home/attendance/frontend
python3 serve_spa.py
```

## 6. Nginx Configuration

Create a site config such as `/etc/nginx/sites-available/fdpp-ems`:

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/fdpp-ems /etc/nginx/sites-enabled/fdpp-ems
sudo nginx -t
sudo systemctl restart nginx
```

## 7. Production Services

Create systemd services so everything starts automatically.

### Backend Service

`/etc/systemd/system/fdpp-backend.service`

```ini
[Unit]
Description=FDPP EMS Backend
After=network.target

[Service]
User=attendance
Group=www-data
WorkingDirectory=/home/attendance/Backend
Environment="PATH=/home/attendance/Backend/venv/bin"
ExecStart=/home/attendance/Backend/venv/bin/gunicorn fdpp_ems.asgi:application --bind 127.0.0.1:8000 -k uvicorn.workers.UvicornWorker --workers 2 --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
```

### Frontend Service

`/etc/systemd/system/fdpp-frontend.service`

```ini
[Unit]
Description=FDPP EMS Frontend SPA Server
After=network.target

[Service]
User=attendance
Group=www-data
WorkingDirectory=/home/attendance/frontend
Environment="SPA_HOST=127.0.0.1"
Environment="SPA_PORT=3000"
Environment="SPA_DIR=/home/attendance/frontend"
ExecStart=/usr/bin/python3 /home/attendance/frontend/serve_spa.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Biometric Connector Service

`/etc/systemd/system/fdpp-biometric.service`

```ini
[Unit]
Description=FDPP EMS Biometric WebSocket Connector
After=network.target fdpp-backend.service

[Service]
User=attendance
Group=www-data
WorkingDirectory=/home/attendance/Backend
Environment="PATH=/home/attendance/Backend/venv/bin"
ExecStart=/home/attendance/Backend/venv/bin/python /home/attendance/Backend/biometric_websocket.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable them:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fdpp-backend fdpp-frontend fdpp-biometric
sudo systemctl start fdpp-backend fdpp-frontend fdpp-biometric
```

## 8. Verify

Check these URLs and logs:

- `http://YOUR_SERVER_IP/` for the frontend
- `http://YOUR_SERVER_IP/api/` for the backend
- `ws://YOUR_SERVER_IP/ws/biometric/` for the biometric WebSocket

Useful commands:

```bash
sudo systemctl status fdpp-backend
sudo systemctl status fdpp-frontend
sudo systemctl status fdpp-biometric
sudo journalctl -u fdpp-backend -f
sudo journalctl -u fdpp-biometric -f
```

## 9. Notes

- Gunicorn must run with an ASGI worker because WebSockets are part of the backend.
- Do not bind both the frontend and backend to port `8000` at the same time.
- Keep the biometric device script pointed at the device IP and the backend WebSocket endpoint on the server IP.

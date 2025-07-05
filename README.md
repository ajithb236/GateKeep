

# GateKeep

**GateKeep** is a FastAPI-based reverse proxy with geo-blocking, static file caching, and a Django-powered analytics dashboard. Built using `asyncio` for high-performance request handling.

## 🔧 Features

-  Reverse proxy for any backend (`BACKEND_URL` via `.env`)
-  Async FastAPI + custom LRU caching
- Country-based blocking (via Django dashboard)
- Request logging and analytics
- Static file caching for performance

🚀 Quick Start

```bash
git clone https://github.com/ajithb236/gatekeep.git
cd gatekeep
pip install -r requirements.txt
````

Create a `.env` file:
Run Django:

```bash
python manage.py migrate
python manage.py runserver
```

Run FastAPI proxy:

```bash
uvicorn proxy.main:app --port 9500
```





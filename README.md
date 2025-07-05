```markdown
**GateKeep** is a FastAPI-based reverse proxy with geo blocking, static file caching, and a Django-powered analytics dashboard. Designed with asyncio for high-performance request handling.

## Features

- Reverse proxy for any backend (configurable via `.env`)
- Built with asyncio for concurrent request handling
- Country-based blocking (manage via Django dashboard)
- Custom Async LRU cache implemented in python
- Static file caching for faster static files delivery
- Request logging and analytics (view in dashboard)


## Quick Start

1. **Clone the repo**

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Configure environment variables**  
   Make a `.env` and set `BACKEND_URL` and database credentials along with a DJANGO secret key.

4. **Run Django backend**
   ```
   python manage.py migrate
   python manage.py runserver
   ```

5. **Run FastAPI proxy**
   ```
   uvicorn proxy.main:app --reload --port 9500
   ```






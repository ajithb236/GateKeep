import asyncio
import time
from datetime import datetime
import zoneinfo
from fastapi import FastAPI, Request, Response
import httpx
from fastapi.responses import PlainTextResponse
from .async_LRU import AsyncLRUCache
from .database import SessionLocal, RequestLog,BlockedCountry
from sqlalchemy import select
import os
from dotenv import load_dotenv
load_dotenv()  # Load .env
BACKEND_URL = os.getenv("BACKEND_URL")
# Timezone
IST = zoneinfo.ZoneInfo("Asia/Kolkata")

# App
app = FastAPI()
BACKEND_URL = os.getenv("BACKEND_URL")

# Shared HTTP clients
http_client = httpx.AsyncClient(
    timeout=10.0,
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
    follow_redirects=False 
)
countryLookupClient = httpx.AsyncClient(
    timeout=5.0,
    limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
    follow_redirects=True
)

# Cache
country_LRU = AsyncLRUCache(maxsize=1000)
static_cache = AsyncLRUCache(maxsize=1000,ttlseconds=300)
blocked_countries_cache = set()
# Log queue
request_log_queue = asyncio.Queue(maxsize=1000)

# Excluded headers
EXCLUDED_HEADERS = {
    "connection", "keep-alive", "transfer-encoding", "te",
    "trailer", "upgrade", "proxy-connection"
}

# Static paths/extensions to skip logging
STATIC_EXTENSIONS = {
    ".js", ".css", ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".ico"
}
STATIC_PATHS = {
    "static/", "assets/", "media/", "images/", "fonts/"
}


async def get_country(ip):
    country = await country_LRU.get(ip)
    if country:
        return country

    try:
        resp = await countryLookupClient.get(f"http://ip-api.com/json/{ip}")
        data = resp.json()
        country = data.get("country", "Unknown")
        await country_LRU.set(ip, country)
        return country
    except Exception:
        return "Unknown"


async def process_log_queue():
    while True:
        try:
            logs = []
            for _ in range(min(100, request_log_queue.qsize() or 1)):#minimise performance impact
                if request_log_queue.empty():
                    break
                logs.append(await request_log_queue.get())

            if logs:
                async with SessionLocal() as session:
                    session.add_all(logs)
                    await session.commit()

            for _ in logs:
                request_log_queue.task_done()

            if not logs:
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error processing logs: {e}")
            await asyncio.sleep(1)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_log_queue()) #to process logs in background
    await refresh_blocked_countries() #load initial blocked countries from db

@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()
    await countryLookupClient.aclose()
    if not request_log_queue.empty():
        try:
            await asyncio.wait_for(request_log_queue.join(), timeout=5.0)
        except asyncio.TimeoutError:
            print("Timeout waiting for log queue to empty")
    


@app.post("/proxy/api/admin/refresh-blocked-countries")
async def manual_refresh_blocked_countries():
    try:
        await refresh_blocked_countries()
        print("blocked_countries_cache refreshed successfully")
        return {
            "status": "success",
            "blocked_countries": list(blocked_countries_cache),
            "count": len(blocked_countries_cache)
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e),
            "current_cache": list(blocked_countries_cache)
        }

@app.api_route("/{path:path}", methods=[
    "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"
])
async def proxy(request: Request, path: str):
    try:
        start = time.perf_counter()
        is_static = (
            any(path.startswith(prefix) for prefix in STATIC_PATHS) or
            any(path.endswith(ext) for ext in STATIC_EXTENSIONS)
        )
        if is_static and request.method == "GET":
            
            cached = await static_cache.get(path)
            if cached:
                #return cached static
                content, status_code, headers, media_type = cached
                return Response(
                    content=content,
                    status_code=status_code,
                    headers=headers,
                    media_type=media_type
                )

        if path:
            url = f"{BACKEND_URL}/{path}"
        else:
            url = BACKEND_URL
        method = request.method
        headers = {}

        for k,v in request.headers.items():
            # Skip excluded headers
            if k.lower() in EXCLUDED_HEADERS:
                continue
            headers[k.lower()] = v

        # Explicitly forward cookie if present
        if "cookie" in request.headers:
            headers["cookie"] = request.headers["cookie"]

        # Forward host header if needed
        headers["host"] = request.headers.get("host", "")

        body = await request.body()

        backend_response = await http_client.request(
            method=method,
            url=url,
            headers=headers,
            content=body,
            params=request.query_params
        )

        end = time.perf_counter()
        response_time = (end - start) * 1000
        response_headers = {}
        for k, v in backend_response.headers.items():
            if k.lower() in EXCLUDED_HEADERS:
                continue
            response_headers[k.lower()] = v
      
        proxy_response = Response(
            content=backend_response.content,
            status_code=backend_response.status_code,
            headers=response_headers,
            media_type=backend_response.headers.get(
                "content-type", "text/html"
            )
        )


        for sc in backend_response.headers.get_list("set-cookie"):
            proxy_response.headers.append("set-cookie", sc)

        if is_static and request.method == "GET" and backend_response.status_code == 200:
            #cache static response
            await static_cache.set(
                path,
                (
                    backend_response.content,
                    backend_response.status_code,
                    dict(response_headers),
                    backend_response.headers.get("content-type", "text/html")
                )
            )
        if not is_static:
            ip = request.headers.get("x-forwarded-for", request.client.host)
            status = backend_response.status_code

            country = await get_country(ip)
            user_agent = request.headers.get("user-agent", "")
            referrer  = request.headers.get("referer", "")
            if country in blocked_countries_cache:
                print(f"Blocked request from {ip} ({country}) to {path}")
                return PlainTextResponse(
                    f"Access denied from your country:{country}", status_code=403
                )
            log = RequestLog(
                ip_address=ip,
                country=country,
                path="/" + path,
                method=method,
                user_agent=user_agent,
                referrer=referrer,
                response_time=response_time,
                timestamp=datetime.now(IST).replace(tzinfo=None),
                http_status=status,
            )
            await request_log_queue.put(log)

        return proxy_response

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return PlainTextResponse(str(e), status_code=500)

async def refresh_blocked_countries():
    """Load blocked countries from database into memory cache"""
    global blocked_countries_cache
    try:
        async with SessionLocal() as session:
            result = await session.execute(select(BlockedCountry.country_name))
            blocked_countries_cache = set(row[0] for row in result)
            print(f"Blocked countries cache refreshed: {blocked_countries_cache}")
    except Exception as e:
        print(f"Error refreshing blocked countries: {e}")




import logging
import asyncpg

from fastapi import FastAPI, HTTPException, Request, status, BackgroundTasks, Path
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from contextlib import asynccontextmanager

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.database import connect_db, close_db, get_db
from app.config import get_settings
from app.utils import generate_short_string
from app.crud import create_short_url, get_original_url, get_stats_data, get_click_timeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


limiter = Limiter(key_func=get_remote_address)

class ShortenRequest(BaseModel):
    url: HttpUrl

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/health", tags=["System"])
async def health_check():
    pool = await get_db()
    if not pool:
        raise HTTPException(status_code=503, detail="Database connection pool not initialized")
    try:

        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

@app.post("/shorten", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute") 
async def shorten_url(request: Request, payload: ShortenRequest):
    max_retries = 3
    for attempt in range(max_retries):
        code = generate_short_string()
        try:
            db_row = await create_short_url(str(payload.url), code)
            
            return {
                "short_url": f"{settings.BASE_URL}/{code}",
                "code": code,
                "created_at": db_row["created_at"],
                "expires_at": db_row["expires_at"]
            }
        except asyncpg.exceptions.UniqueViolationError:
            logger.warning(f"Collision detected on attempt {attempt + 1} for code: {code}")
            continue
    
    logger.error("Failed to generate unique short code after max retries.")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail="Collision threshold reached"
    )

@app.get("/stats/{short_code}")
async def get_link_stats(
    short_code: str = Path(..., min_length=6, max_length=6)
):
    pool = await get_db()
    query = """
        SELECT clicks, created_at, expires_at, original_url 
        FROM urls WHERE short_code = $1
    """
    async with pool.acquire() as conn:
        link_data = await conn.fetchrow(query, short_code)
        
        if not link_data:
            raise HTTPException(status_code=404, detail="Stats not found")
            
        ref_query = """
            SELECT v.referrer, COUNT(v.id) as count 
            FROM url_visits v
            JOIN urls u ON u.id = v.url_id
            WHERE u.short_code = $1
            GROUP BY v.referrer 
            ORDER BY count DESC 
            LIMIT 5
        """
        referrers = await conn.fetch(ref_query, short_code)
        
        return {
            "total_clicks": link_data["clicks"],
            "created_at": link_data["created_at"],
            "expires_at": link_data["expires_at"],   
            "original_url": link_data["original_url"], 
            "top_referrers": [{"source": r["referrer"], "count": r["count"]} for r in referrers]
        }

@app.get("/stats/{short_code}/timeline")
async def get_timeline_stats(short_code: str = Path(..., min_length=6, max_length=6)):
    timeline = await get_click_timeline(short_code)

    if timeline is None:
        timeline = []
        
    return {"timeline": timeline}

@app.get("/{short_code}")
async def redirect_to_original(
    request: Request, 
    background_tasks: BackgroundTasks,
    short_code: str = Path(..., min_length=6, max_length=6)
):
    ip = request.client.host
    ua = request.headers.get("user-agent")
    ref = request.headers.get("referer")
    
    original_url = await get_original_url(short_code, ip, ua, ref, background_tasks)
    
    if not original_url:
        raise HTTPException(status_code=404, detail="Short URL not found or expired")
    
    return RedirectResponse(url=original_url, status_code=status.HTTP_302_FOUND)
from app.database import get_db
from fastapi import BackgroundTasks

async def create_short_url(original_url: str, short_code: str, days_valid: int = 30):
    pool = await get_db() 
    query = """
        INSERT INTO urls (original_url, short_code, expires_at) 
        VALUES ($1, $2, NOW() + make_interval(days => $3))
        RETURNING created_at, expires_at
    """
    async with pool.acquire() as connection:
        return await connection.fetchrow(query, original_url, short_code, days_valid)

async def log_analytics(url_id: int, ip: str, ua: str, ref: str):

    pool = await get_db()
    query = """
        INSERT INTO url_visits (url_id, ip, user_agent, referrer) 
        VALUES ($1, $2, $3, $4)
    """
    async with pool.acquire() as conn:
        await conn.execute(query, url_id, ip, ua, ref)

async def get_original_url(short_code: str, ip: str, ua: str, ref: str, background_tasks: BackgroundTasks):

    pool = await get_db()
    query = """
        UPDATE urls 
        SET clicks = clicks + 1 
        WHERE short_code = $1 
        AND (expires_at IS NULL OR expires_at > NOW())
        RETURNING id, original_url
    """
    async with pool.acquire() as connection:
        row = await connection.fetchrow(query, short_code)
        
        if row:
            background_tasks.add_task(log_analytics, row['id'], ip, ua, ref)
            return row['original_url']
        return None

async def get_stats_data(short_code: str):
    pool = await get_db()
    async with pool.acquire() as conn:
        link_query = "SELECT clicks, created_at, original_url FROM urls WHERE short_code = $1"
        link_data = await conn.fetchrow(link_query, short_code)
        
        if not link_data:
            return None
            
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
            "top_referrers": [{"source": r["referrer"], "count": r["count"]} for r in referrers]
        }

async def get_click_timeline(short_code: str):
    pool = await get_db()
    query = """
        SELECT DATE_TRUNC('day', v.visited_at) as date, COUNT(v.id) as clicks
        FROM url_visits v
        JOIN urls u ON u.id = v.url_id
        WHERE u.short_code = $1
        GROUP BY date
        ORDER BY date DESC
        LIMIT 30
    """
    async with pool.acquire() as conn:
        records = await conn.fetch(query, short_code)
        return [
            {"date": record["date"].date().isoformat(), "clicks": record["clicks"]} 
            for record in records
        ]
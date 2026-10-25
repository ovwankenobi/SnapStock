from slowapi import Limiter
from slowapi.util import get_remote_address

# Behind Caddy in production, uvicorn runs with --proxy-headers so request.client is the real
# visitor (from the X-Forwarded-For header Caddy sets), not Caddy's container IP. Without that,
# every user would share one rate-limit bucket.
limiter = Limiter(key_func=get_remote_address)

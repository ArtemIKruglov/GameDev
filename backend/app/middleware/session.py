import uuid

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

_serializer = URLSafeTimedSerializer(settings.session_secret)
MAX_AGE = 86400  # 24 hours


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        session_id = None
        raw_cookie = request.cookies.get("session_id")

        if raw_cookie:
            try:
                session_id = _serializer.loads(raw_cookie, max_age=MAX_AGE)
            except (BadSignature, SignatureExpired):
                session_id = None  # tampered or expired — issue new session

        if not session_id:
            session_id = str(uuid.uuid4())

        request.state.session_id = session_id
        response = await call_next(request)

        # Always set/refresh the signed cookie
        signed = _serializer.dumps(session_id)
        response.set_cookie(
            key="session_id",
            value=signed,
            httponly=True,
            samesite="strict",
            max_age=MAX_AGE,
        )

        return response

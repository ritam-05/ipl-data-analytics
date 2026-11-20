import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from dotenv import load_dotenv

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

security = HTTPBearer(auto_error=True)

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """
    Returns a singleton Supabase client using the backend Secret key.
    Used strictly on the server after verifying the user's JWT.
    """
    global _supabase_client
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SECRET_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SECRET_KEY must be set in environment variables.")
        _supabase_client = create_client(url, key)
    return _supabase_client


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Verifies the Supabase Auth JWT from the Authorization: Bearer <token> header
    and returns the authenticated user's id and email.
    """
    token = credentials.credentials
    supabase = get_supabase_client()
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
            )
        return {
            "id": str(user_response.user.id),
            "email": user_response.user.email,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
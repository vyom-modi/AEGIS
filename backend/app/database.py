"""
AEGIS Database Module.

Initializes the Supabase client for all database operations.
Uses the service_role key for full access to tables.
"""

from supabase import create_client, Client
from app.config import get_settings


def get_supabase_client() -> Client:
    """Create and return a Supabase client instance."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)


# Module-level client for convenience
_client: Client | None = None


def get_db() -> Client:
    """Get or create the shared Supabase client."""
    global _client
    if _client is None:
        _client = get_supabase_client()
    return _client

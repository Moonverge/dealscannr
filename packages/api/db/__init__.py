"""MongoDB access (Motor async)."""

from db.mongo import close_mongo, get_database, init_indexes

__all__ = ["close_mongo", "get_database", "init_indexes"]

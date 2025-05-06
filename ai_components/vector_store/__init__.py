# ai_components/vector_store/__init__.py
from .client import (
    get_vector_db_connection, 
    close_vector_db_connection,
    search_similar_vectors,
    store_document_vector
)

__all__ = [
    'get_vector_db_connection',
    'close_vector_db_connection',
    'search_similar_vectors',
    'store_document_vector'
] 
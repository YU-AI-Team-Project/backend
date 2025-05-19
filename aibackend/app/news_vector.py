from sqlalchemy import Column,Text,DateTime
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import uuid

from news_vector_db import NewsBase

class NewsVector(NewsBase):
    __tablename__="news_vectors"
    
    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    title = Column(Text,nullable=False)
    content = Column(Text,nullable=False)
    embedding = Column(Vector(1536))
    published_at = Column(DateTime)
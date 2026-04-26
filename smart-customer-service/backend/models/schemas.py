"""数据库模型定义

所有时间字段使用 timezone-aware UTC 时间。
"""

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from utils import utcnow

Base = declarative_base()


class Document(Base):
    """知识库文档表"""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default=dict)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    versions = relationship(
        "DocumentVersion", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_documents_title", "title", postgresql_using="gin"),)

    def __repr__(self):
        return f"<Document {self.title}>"


class DocumentVersion(Base):
    """文档版本历史表"""

    __tablename__ = "document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    document = relationship("Document", back_populates="versions")

    __table_args__ = (Index("ix_versions_doc_id", "document_id", "version", unique=True),)

    def __repr__(self):
        return f"<DocumentVersion {self.document_id} v{self.version}>"


class AuditLog(Base):
    """操作审计日志表"""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    details = Column(JSON)
    created_at = Column(DateTime, default=utcnow, index=True)

    __table_args__ = (Index("ix_auditlogs_user_time", "user_id", "created_at"),)

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_id}>"


class ConversationArchive(Base):
    """会话归档表 (长期存储)"""

    __tablename__ = "conversation_archives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(100), nullable=False)
    messages = Column(JSON, nullable=False)
    final_status = Column(String(50))
    metrics = Column(JSON)
    archived_at = Column(DateTime, default=utcnow)

    __table_args__ = (Index("ix_archives_user_time", "user_id", "archived_at"),)

    def __repr__(self):
        return f"<ConversationArchive {self.session_id}>"

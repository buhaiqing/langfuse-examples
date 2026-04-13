"""initial migration - create database tables

Revision ID: 001_initial
Revises:
Create Date: 2026-04-13

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True, default=1),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_title", "documents", ["title"])

    op.create_table(
        "document_versions",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_versions_doc_id", "document_versions", ["document_id", "version"], unique=True
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("details", JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auditlogs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_auditlogs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "conversation_archives",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.String(100), nullable=False),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("messages", JSON(), nullable=False),
        sa.Column("final_status", sa.String(50), nullable=True),
        sa.Column("metrics", JSON(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_archives_session_id", "conversation_archives", ["session_id"])
    op.create_index("ix_archives_user_id", "conversation_archives", ["user_id"])


def downgrade():
    op.drop_index("ix_archives_user_id", table_name="conversation_archives")
    op.drop_index("ix_archives_session_id", table_name="conversation_archives")
    op.drop_table("conversation_archives")

    op.drop_index("ix_auditlogs_created_at", table_name="audit_logs")
    op.drop_index("ix_auditlogs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_versions_doc_id", table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index("ix_documents_title", table_name="documents")
    op.drop_table("documents")

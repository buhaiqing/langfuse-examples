"""PostgreSQL 数据库客户端封装

使用 SQLAlchemy 2.0 异步 ORM 提供数据库访问层
支持连接池、事务管理和 CRUD 操作
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional, List, TypeVar, Generic, Type, Any, Dict
from datetime import datetime

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, update, delete, insert, func, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from core.config import settings
from models.schemas import Base

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Base)


class DatabaseError(Exception):
    """数据库操作异常"""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class PostgresClient:
    """PostgreSQL 异步客户端封装"""

    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_maker: Optional[async_sessionmaker[AsyncSession]] = None
        self._connected = False

    async def connect(self) -> None:
        """初始化数据库连接池"""
        try:
            # 创建异步引擎
            self.engine = create_async_engine(
                settings.postgres_url,
                echo=settings.debug,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True,  # 自动检测连接是否有效
            )

            # 创建会话工厂
            self.session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )

            self._connected = True
            logger.info("PostgreSQL 连接池初始化成功")

        except Exception as e:
            logger.error(f"PostgreSQL 连接失败: {e}")
            raise DatabaseError("数据库连接失败", e)

    async def close(self) -> None:
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()
            self._connected = False
            logger.info("PostgreSQL 连接池已关闭")

    async def ping(self) -> bool:
        """检查数据库连接健康"""
        if not self._connected or not self.engine:
            return False

        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.warning(f"数据库健康检查失败: {e}")
            return False

    @asynccontextmanager
    async def session(self):
        """获取数据库会话上下文管理器"""
        if not self.session_maker:
            raise DatabaseError("数据库未连接")

        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise DatabaseError("数据库操作失败", e)
            finally:
                await session.close()

    @asynccontextmanager
    async def transaction(self):
        """获取事务上下文管理器，支持嵌套事务"""
        if not self.session_maker:
            raise DatabaseError("数据库未连接")

        async with self.session_maker() as session:
            async with session.begin():
                try:
                    yield session
                except Exception as e:
                    await session.rollback()
                    raise DatabaseError("事务执行失败", e)
                finally:
                    await session.close()

    # ==================== CRUD 操作 ====================

    async def create(self, model: T) -> T:
        """创建记录

        Args:
            model: 模型实例

        Returns:
            创建的模型实例（包含生成的 ID）
        """
        async with self.session() as session:
            session.add(model)
            await session.flush()  # 生成 ID
            await session.refresh(model)
            logger.debug(f"创建记录: {model}")
            return model

    async def create_many(self, models: List[T]) -> List[T]:
        """批量创建记录

        Args:
            models: 模型实例列表

        Returns:
            创建的模型实例列表
        """
        async with self.session() as session:
            session.add_all(models)
            await session.flush()
            for model in models:
                await session.refresh(model)
            logger.debug(f"批量创建 {len(models)} 条记录")
            return models

    async def get_by_id(self, model_class: Type[T], id: Any) -> Optional[T]:
        """根据 ID 查询记录

        Args:
            model_class: 模型类
            id: 记录 ID

        Returns:
            模型实例或 None
        """
        async with self.session() as session:
            result = await session.get(model_class, id)
            return result

    async def get_one(self, model_class: Type[T], **filters) -> Optional[T]:
        """根据条件查询单条记录

        Args:
            model_class: 模型类
            **filters: 过滤条件

        Returns:
            模型实例或 None
        """
        async with self.session() as session:
            stmt = select(model_class)
            for key, value in filters.items():
                if hasattr(model_class, key):
                    stmt = stmt.where(getattr(model_class, key) == value)

            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_many(
        self,
        model_class: Type[T],
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        **filters,
    ) -> tuple[List[T], int]:
        """根据条件查询多条记录（支持分页）

        Args:
            model_class: 模型类
            limit: 返回数量限制
            offset: 偏移量
            order_by: 排序字段
            **filters: 过滤条件

        Returns:
            (记录列表, 总数量)
        """
        async with self.session() as session:
            # 构建查询
            stmt = select(model_class)
            count_stmt = select(func.count()).select_from(model_class)

            # 应用过滤条件
            for key, value in filters.items():
                if hasattr(model_class, key):
                    column = getattr(model_class, key)
                    stmt = stmt.where(column == value)
                    count_stmt = count_stmt.where(column == value)

            # 排序
            if order_by and hasattr(model_class, order_by.lstrip("-")):
                column = getattr(model_class, order_by.lstrip("-"))
                if order_by.startswith("-"):
                    stmt = stmt.order_by(column.desc())
                else:
                    stmt = stmt.order_by(column.asc())

            # 分页
            stmt = stmt.limit(limit).offset(offset)

            # 执行查询
            result = await session.execute(stmt)
            count_result = await session.execute(count_stmt)

            records = result.scalars().all()
            total = count_result.scalar()

            return list(records), total

    async def update(self, model_class: Type[T], id: Any, **updates) -> Optional[T]:
        """更新记录

        Args:
            model_class: 模型类
            id: 记录 ID
            **updates: 更新字段

        Returns:
            更新后的模型实例或 None
        """
        async with self.session() as session:
            # 添加更新时间
            if hasattr(model_class, "updated_at"):
                updates["updated_at"] = datetime.utcnow()

            stmt = (
                update(model_class)
                .where(model_class.id == id)
                .values(**updates)
                .execution_options(synchronize_session="fetch")
            )

            result = await session.execute(stmt)

            if result.rowcount == 0:
                return None

            # 返回更新后的记录
            return await session.get(model_class, id)

    async def update_many(self, model_class: Type[T], ids: List[Any], **updates) -> int:
        """批量更新记录

        Args:
            model_class: 模型类
            ids: 记录 ID 列表
            **updates: 更新字段

        Returns:
            更新的记录数
        """
        async with self.session() as session:
            if hasattr(model_class, "updated_at"):
                updates["updated_at"] = datetime.utcnow()

            stmt = (
                update(model_class)
                .where(model_class.id.in_(ids))
                .values(**updates)
            )

            result = await session.execute(stmt)
            return result.rowcount

    async def delete(self, model_class: Type[T], id: Any) -> bool:
        """删除记录

        Args:
            model_class: 模型类
            id: 记录 ID

        Returns:
            是否删除成功
        """
        async with self.session() as session:
            stmt = delete(model_class).where(model_class.id == id)
            result = await session.execute(stmt)
            return result.rowcount > 0

    async def delete_many(self, model_class: Type[T], ids: List[Any]) -> int:
        """批量删除记录

        Args:
            model_class: 模型类
            ids: 记录 ID 列表

        Returns:
            删除的记录数
        """
        async with self.session() as session:
            stmt = delete(model_class).where(model_class.id.in_(ids))
            result = await session.execute(stmt)
            return result.rowcount

    async def exists(self, model_class: Type[T], **filters) -> bool:
        """检查记录是否存在

        Args:
            model_class: 模型类
            **filters: 过滤条件

        Returns:
            是否存在
        """
        async with self.session() as session:
            stmt = select(func.count()).select_from(model_class)

            for key, value in filters.items():
                if hasattr(model_class, key):
                    stmt = stmt.where(getattr(model_class, key) == value)

            result = await session.execute(stmt)
            return result.scalar() > 0

    async def count(self, model_class: Type[T], **filters) -> int:
        """统计记录数量

        Args:
            model_class: 模型类
            **filters: 过滤条件

        Returns:
            记录数量
        """
        async with self.session() as session:
            stmt = select(func.count()).select_from(model_class)

            for key, value in filters.items():
                if hasattr(model_class, key):
                    stmt = stmt.where(getattr(model_class, key) == value)

            result = await session.execute(stmt)
            return result.scalar()

    # ==================== 业务特定查询 ====================

    async def get_documents_by_title(self, title: str, limit: int = 10) -> List[Any]:
        """根据标题搜索文档

        Args:
            title: 标题关键词
            limit: 返回数量

        Returns:
            文档列表
        """
        from models.schemas import Document

        async with self.session() as session:
            stmt = (
                select(Document)
                .where(Document.title.ilike(f"%{title}%"))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_audit_logs_by_user(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> tuple[List[Any], int]:
        """获取用户的审计日志

        Args:
            user_id: 用户 ID
            limit: 返回数量
            offset: 偏移量

        Returns:
            (日志列表, 总数量)
        """
        from models.schemas import AuditLog

        async with self.session() as session:
            stmt = (
                select(AuditLog)
                .where(AuditLog.user_id == user_id)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            count_stmt = (
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.user_id == user_id)
            )

            result = await session.execute(stmt)
            count_result = await session.execute(count_stmt)

            return list(result.scalars().all()), count_result.scalar()

    async def get_conversation_archives(
        self, user_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> tuple[List[Any], int]:
        """获取会话归档列表

        Args:
            user_id: 可选的用户 ID 过滤
            limit: 返回数量
            offset: 偏移量

        Returns:
            (归档列表, 总数量)
        """
        from models.schemas import ConversationArchive

        async with self.session() as session:
            stmt = select(ConversationArchive)
            count_stmt = select(func.count()).select_from(ConversationArchive)

            if user_id:
                stmt = stmt.where(ConversationArchive.user_id == user_id)
                count_stmt = count_stmt.where(ConversationArchive.user_id == user_id)

            stmt = stmt.order_by(ConversationArchive.archived_at.desc()).limit(limit).offset(offset)

            result = await session.execute(stmt)
            count_result = await session.execute(count_stmt)

            return list(result.scalars().all()), count_result.scalar()


# 全局 PostgreSQL 客户端实例
postgres_client = PostgresClient()


async def get_postgres_client() -> PostgresClient:
    """获取 PostgreSQL 客户端实例"""
    return postgres_client


async def init_db():
    """初始化数据库表结构"""
    from models.schemas import Base

    engine = create_async_engine(settings.postgres_url, echo=settings.debug)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    logger.info("数据库表结构初始化完成")


async def drop_db():
    """删除所有表（仅用于测试）"""
    from models.schemas import Base

    engine = create_async_engine(settings.postgres_url, echo=settings.debug)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    logger.warning("数据库表已删除")

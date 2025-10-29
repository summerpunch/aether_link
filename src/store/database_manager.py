import os

from injector import inject

from src.store.model import Base
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from src.core.singleton import singleton
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

@inject
@singleton
class DatabaseManager:
    """数据库管理器，负责连接池和会话管理"""

    @staticmethod
    def _connection():
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        database = os.getenv("DB_NAME", "llm")
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "")
        return host, port, database, user, password

    @staticmethod
    def get_psycopg_connection():
        host, port, database, user, password = DatabaseManager._connection()
        connection_string = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"
        return connection_string

    @staticmethod
    def get_psycopg2_connection():
        host, port, database, user, password = DatabaseManager._connection()
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        return connection_string

    def __init__(self, connection_string: Optional[str] = None):
        if connection_string is None:
            connection_string = DatabaseManager.get_psycopg_connection()
        self.connection_string = connection_string

        # 创建引擎，配置连接池
        self.engine = create_engine(
            self.connection_string,
            poolclass=QueuePool,
            pool_size=5,  # 连接池大小
            max_overflow=10,  # 最大溢出连接数
            pool_timeout=30,  # 连接超时时间
            pool_recycle=1800,  # 连接回收时间（30分钟）
            pool_pre_ping=True,  # 连接前ping，确保连接有效
        )

        self.session_factory = sessionmaker(bind=self.engine)
        self.session = scoped_session(self.session_factory)

    def create_tables(self):
        """异步创建所有表"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
            return True
        except SQLAlchemyError as e:
            return False

    @contextmanager
    def get_session(self):
        session = self.session()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def auto_commit(self):
        session = self.session()
        try:
            yield
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def close(self, session):
        """关闭数据库引擎"""
        if session:
            session.close()


_database_manager: Optional[DatabaseManager] = None


def init_database_manager() -> DatabaseManager:
    """初始化全局数据库管理器"""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager

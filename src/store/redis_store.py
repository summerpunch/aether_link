import os
import logging
from redis import Redis
from redis.connection import ConnectionPool
from redis.exceptions import RedisError
from redis.lock import Lock as RedisLock
from src.core.singleton import singleton
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

REDIS_KEY_EXPIRE_TIME = int(os.getenv("REDIS_KEY_EXPIRE_TIME", (1 * 60 * 60 * 24 * 30)))


@singleton
class RedisManager:

    def __init__(self, connection_string: Optional[str] = None):
        """初始化Redis管理器

        Args:
            connection_string: Redis连接字符串，如果为None，则使用环境变量
        """
        # 构建连接参数
        if connection_string is None:
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            db = int(os.getenv("REDIS_DB", "0"))
            password = os.getenv("REDIS_PASSWORD", None)
        else:
            # 解析连接字符串
            from urllib.parse import urlparse
            parsed = urlparse(connection_string)
            host = parsed.hostname or "localhost"
            port = parsed.port or 6379
            db = int(parsed.path.strip("/") or 0)
            password = parsed.password

        # 创建连接池
        self.pool = ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
            max_connections=100,
            socket_timeout=30,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            socket_keepalive=True,
            health_check_interval=60
        )

        # 创建Redis客户端
        self.redis = Redis(connection_pool=self.pool)

        # 标记为已初始化
        logger.info(f"Redis manager initialized with connection to {host}:{port}/db{db}")

    @classmethod
    def get_instance(cls, connection_string: Optional[str] = None) -> 'RedisManager':
        """获取RedisManager的单例实例"""
        return cls(connection_string)

    def acquire_lock(self, lock_name: str, timeout: int = 10, blocking: bool = True) -> Optional[RedisLock]:
        """获取分布式锁

        Args:
            lock_name: 锁名称
            timeout: 锁超时时间（秒）
            blocking: 是否阻塞等待

        Returns:
            Lock对象或None（如果获取失败）
        """
        try:
            lock = self.redis.lock(
                name=lock_name,
                timeout=timeout,
                blocking=blocking,
                blocking_timeout=1 if blocking else None
            )
            if lock.acquire():
                return lock
        except RedisError as e:
            logger.error(f"Failed to acquire Redis lock '{lock_name}': {e}")
        return None

    def set_with_ttl(self, key: str, value: str, ttl: int = REDIS_KEY_EXPIRE_TIME) -> bool:
        """设置键值对，带过期时间

        Args:
            key: 键
            value: 值
            ttl: 过期时间（秒）

        Returns:
            是否设置成功
        """
        try:
            return self.redis.setex(key, ttl, value)
        except RedisError as e:
            logger.error(f"Failed to set Redis key '{key}': {e}")
            return False

    def set_value(self, key: str, value: str) -> bool:
        """设置键值对

        Args:
            key: 键
            value: 值

        Returns:
            是否设置成功
        """
        try:
            return bool(self.redis.set(key, value))
        except RedisError as e:
            logger.error(f"Failed to set Redis key '{key}': {e}")
            return False

    def get_value(self, key: str) -> Optional[str]:
        """获取键值

        Args:
            key: 键

        Returns:
            值或None（如果不存在）
        """
        try:
            return self.redis.get(key)
        except RedisError as e:
            logger.error(f"Failed to get Redis key '{key}': {e}")
            return None

    def delete(self, key: str) -> bool:
        """删除键
        Args:
            key: redisKey

        Returns:
            bool: 是否成功删除
        """
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            logger.error(f"Failed to delete human session data: {e}")
            return False

    # Hash (Map) 操作
    def hset(self, name: str, key: str, value: str, expire_seconds: int = REDIS_KEY_EXPIRE_TIME) -> bool:
        """设置Hash的字段值

        Args:
            name: Hash名称
            key: 字段名
            value: 字段值
            expire_seconds: 过期时间（秒），默认30天

        Returns:
            是否设置成功
        """
        try:
            pipe = self.redis.pipeline()
            pipe.hset(name, key, value)
            if expire_seconds is not None:
                pipe.expire(name, expire_seconds)
            results = pipe.execute()
            return bool(results[0])
        except RedisError as e:
            logger.error(f"Failed to set hash field '{name}.{key}': {e}")
            return False

    def hmset(self, name: str, mapping: Dict[str, Any]) -> bool:
        """批量设置Hash的字段值

        Args:
            name: Hash名称
            mapping: 字段名和值的映射字典

        Returns:
            是否设置成功
        """
        try:
            return bool(self.redis.hset(name, mapping=mapping))
        except RedisError as e:
            logger.error(f"Failed to set multiple hash fields for '{name}': {e}")
            return False

    def hget(self, name: str, key: str) -> Optional[str]:
        """获取Hash的字段值

        Args:
            name: Hash名称
            key: 字段名

        Returns:
            字段值或None（如果不存在）
        """
        try:
            return self.redis.hget(name, key)
        except RedisError as e:
            logger.error(f"Failed to get hash field '{name}.{key}': {e}")
            return None

    def hmget(self, name: str, keys: List[str]) -> List[Optional[str]]:
        """批量获取Hash的字段值

        Args:
            name: Hash名称
            keys: 字段名列表

        Returns:
            字段值列表，不存在的字段返回None
        """
        try:
            return self.redis.hmget(name, keys)
        except RedisError as e:
            logger.error(f"Failed to get multiple hash fields from '{name}': {e}")
            return [None] * len(keys)

    def hgetall(self, name: str) -> Dict[str, str]:
        """获取Hash的所有字段和值

        Args:
            name: Hash名称

        Returns:
            字段名和值的映射字典
        """
        try:
            return self.redis.hgetall(name)
        except RedisError as e:
            logger.error(f"Failed to get all hash fields from '{name}': {e}")
            return {}

    def hdel(self, name: str, *keys: str) -> int:
        """删除Hash的一个或多个字段

        Args:
            name: Hash名称
            keys: 要删除的字段名

        Returns:
            成功删除的字段数量
        """
        try:
            return self.redis.hdel(name, *keys)
        except RedisError as e:
            logger.error(f"Failed to delete hash fields from '{name}': {e}")
            return 0

    def hexists(self, name: str, key: str) -> bool:
        """检查Hash字段是否存在

        Args:
            name: Hash名称
            key: 字段名

        Returns:
            字段是否存在
        """
        try:
            return self.redis.hexists(name, key)
        except RedisError as e:
            logger.error(f"Failed to check hash field existence '{name}.{key}': {e}")
            return False

    # List 操作
    def lpush(self, name: str, *values: str, expire_seconds: int = REDIS_KEY_EXPIRE_TIME) -> int:
        """从列表左端推入一个或多个值

        Args:
            name: 列表名称
            values: 要推入的值
            expire_seconds: 过期时间（秒），可选

        Returns:
            操作后列表的长度
        """
        try:
            pipe = self.redis.pipeline()
            pipe.lpush(name, *values)
            if expire_seconds is not None:
                pipe.expire(name, expire_seconds)
            results = pipe.execute()
            return results[0]
        except RedisError as e:
            logger.error(f"Failed to push values to list '{name}': {e}")
            return 0

    def rpush(self, name: str, *values: str, expire_seconds: int = REDIS_KEY_EXPIRE_TIME) -> int:
        """从列表右端推入一个或多个值

        Args:
            name: 列表名称
            values: 要推入的值
            expire_seconds: 过期时间（秒），可选
        Returns:
            操作后列表的长度
        """
        try:
            pipe = self.redis.pipeline()
            pipe.rpush(name, *values)
            if expire_seconds is not None:
                pipe.expire(name, expire_seconds)
            results = pipe.execute()
            return results[0]
        except RedisError as e:
            logger.error(f"Failed to push values to list '{name}': {e}")
            return 0

    def lpop(self, name: str) -> Optional[str]:
        """从列表左端弹出一个值

        Args:
            name: 列表名称

        Returns:
            弹出的值或None（如果列表为空）
        """
        try:
            return self.redis.lpop(name)
        except RedisError as e:
            logger.error(f"Failed to pop value from list '{name}': {e}")
            return None

    def rpop(self, name: str) -> Optional[str]:
        """从列表右端弹出一个值

        Args:
            name: 列表名称

        Returns:
            弹出的值或None（如果列表为空）
        """
        try:
            return self.redis.rpop(name)
        except RedisError as e:
            logger.error(f"Failed to pop value from list '{name}': {e}")
            return None

    def lrange(self, name: str, start: int, end: int) -> List[str]:
        """获取列表指定范围内的元素

        Args:
            name: 列表名称
            start: 起始索引（0表示第一个元素）
            end: 结束索引（-1表示最后一个元素）

        Returns:
            指定范围内的元素列表
        """
        try:
            return self.redis.lrange(name, start, end)
        except RedisError as e:
            logger.error(f"Failed to get range from list '{name}': {e}")
            return []

    def llen(self, name: str) -> int:
        """获取列表长度

        Args:
            name: 列表名称

        Returns:
            列表长度
        """
        try:
            return self.redis.llen(name)
        except RedisError as e:
            logger.error(f"Failed to get list length '{name}': {e}")
            return 0

    def lrem(self, name: str, count: int, value: str) -> int:
        """从列表中删除指定的元素

        Args:
            name: 列表名称
            count: 删除的数量（0表示所有匹配的元素）
            value: 要删除的值

        Returns:
            实际删除的元素数量
        """
        try:
            return self.redis.lrem(name, count, value)
        except RedisError as e:
            logger.error(f"Failed to remove value from list '{name}': {e}")
            return 0

    def ltrim(self, name: str, start: int, end: int) -> bool:
        """修剪列表，只保留指定范围内的元素

        Args:
            name: 列表名称
            start: 起始索引
            end: 结束索引

        Returns:
            是否成功
        """
        try:
            self.redis.ltrim(name, start, end)
            return True
        except RedisError as e:
            logger.error(f"Failed to trim list '{name}': {e}")
            return False

    def exists(self, name: str) -> bool:
        """验证键是否存在

        Args:
            name: 键名称

        Returns:
            bool: 如果键存在返回True，否则返回False
        """
        try:
            return bool(self.redis.exists(name))
        except RedisError as e:
            logger.error(f"Failed to check if key '{name}' exists: {e}")
            return False

    def incr(self, name: str, amount: Optional[int] = 1) -> int:
        """键值自增

        Args:
            name: 键名称
            amount: 自增步数

        Returns:
            int: 当前自增值
        """
        return self.redis.incrby(name, amount)


redis_client = RedisManager()
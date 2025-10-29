from src.store.database_manager import DatabaseManager
from src.core.exception.exception import FailException
from typing import Any, List, Dict, Union, Optional, Literal
from sqlalchemy.orm import Query
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from sqlalchemy import asc, desc

class BaseService:
    """基础服务，完善数据库的基础增删改查功能，简化代码"""
    database_manager: DatabaseManager

    def create(self, model: Any, **kwargs) -> Any:
        """根据传递的模型类+键值对信息创建数据库记录"""
        with self.database_manager.auto_commit():
            model_instance = model(**kwargs)
            self.database_manager.session.add(model_instance)
            self.database_manager.session.flush()
            self.database_manager.session.expunge(model_instance)
        return model_instance

    def delete(self, model_instance: Any) -> Any:
        """根据传递的模型实例删除数据库记录"""
        with self.database_manager.auto_commit():
            self.database_manager.session.delete(model_instance)
        return model_instance

    def update(self, model_instance: Any, **kwargs) -> Any:
        """根据传递的模型实例+键值对信息更新数据库记录"""
        with self.database_manager.auto_commit():
            for field, value in kwargs.items():
                if hasattr(model_instance, field):
                    setattr(model_instance, field, value)
                else:
                    raise FailException("更新数据失败")
        return model_instance

    def update_by_filter(
            self,
            model: Any,
            filters: dict,
            update_fields: dict
    ) -> int:
        """
        根据指定条件更新字段（支持批量更新）

        Args:
            model: SQLAlchemy 模型类
            filters: 查询条件（字典形式，如 {"status": "active"}）
            update_fields: 要更新的字段（如 {"status": "inactive"}）
        Returns:
            更新的记录数
        """
        try:
            with self.database_manager.auto_commit():
                query: Query = self.database_manager.session.query(model)
                for field, value in filters.items():
                    if hasattr(model, field):
                        query = query.filter(getattr(model, field) == value)
                    else:
                        raise HTTPException(status_code=400, detail=f"无效字段: {field}")
                updated_count = query.update(update_fields, synchronize_session='fetch')
                return updated_count
        except SQLAlchemyError as e:
            raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

    def get(self, model: Any, primary_key: Any) -> Optional[Any]:
        """根据传递的模型类+主键的信息获取唯一数据"""
        with self.database_manager.get_session() as session:
            return session.query(model).get(primary_key)

    def filter_by_fields(self, model: Any, filters: Dict[str, Any]) -> Optional[Any]:
        """
        根据字段字典查询唯一数据，例如：{"email": "test@example.com", "status": "active"}
        """
        with self.database_manager.get_session() as session:
            query = session.query(model)
            for field_name, value in filters.items():
                if not hasattr(model, field_name):
                    raise ValueError(f"字段 {field_name} 不存在于模型 {model.__name__}")
                query = query.filter(getattr(model, field_name) == value)
            return query.one_or_none()

    def filter_by_fields_with_values(
            self,
            model: Any,
            filters: Dict[str, Union[Any, List[Any]]],
            order_by: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Any]:
        """
        根据字段（支持单值/多值/None）查询数据，并支持明确的 asc/desc 排序结构

        Args:
            model: SQLAlchemy 模型类
            filters: 查询条件，如 {"status": ["active", "pending"], "role": "admin"}
            order_by: 排序控制，如 [{"direction": "asc"}]

        Returns:
            匹配的记录列表
        """
        try:
            with self.database_manager.get_session() as session:
                query: Query = session.query(model)

                # 构造过滤条件
                for field, value in filters.items():
                    column = getattr(model, field, None)
                    if column is None:
                        raise ValueError(f"Model {model.__name__} has no field '{field}'")

                    if isinstance(value, list):
                        query = query.filter(column.in_(value))
                    elif value is None:
                        query = query.filter(column.is_(None))
                    elif isinstance(value, bool):
                        # 用于布尔字段（如 is_active）
                        query = query.filter(column.is_(value))
                    else:
                        query = query.filter(column == value)

                if order_by:
                    for order_dict in order_by:
                        field_name, direction = next(iter(order_dict.items()))
                        column = getattr(model, field_name)
                        direction = (direction or "asc").lower()
                        if direction == "desc":
                            query = query.order_by(desc(column))
                        else:
                            query = query.order_by(asc(column))
                return query.all()
        except SQLAlchemyError as e:
            raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
from contextvars import ContextVar
from typing import Optional, Dict, Any, Callable, TypeVar, Awaitable, List, Union

T = TypeVar('T')

current_user_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar("current_user", default=None)

def get_current_user_id() -> Optional[str]:
    return 'system'

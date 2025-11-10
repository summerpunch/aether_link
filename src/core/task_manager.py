import logging
import asyncio
from src.core.singleton import singleton

logger = logging.getLogger(__name__)


@singleton
class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.task_metadata = {}
        self.lock = asyncio.Lock()

    async def create_task(self, run_id, coro):
        """创建一个新任务并添加到管理器中"""
        async with self.lock:
            logger.info(f"开始创建任务: run_id={run_id}")
            if run_id in self.tasks and not self.tasks[run_id].done():
                logger.info(f"会话 {run_id} 已有运行中的任务，将被新任务替代")
                self.tasks[run_id].cancel()
                try:
                    await asyncio.wait_for(self.tasks[run_id], timeout=5.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    logger.warning(f"会话 {run_id} 的旧任务取消超时或已被取消")
            # 创建新任务并保存引用
            task = asyncio.create_task(coro)
            task.add_done_callback(lambda t: self._on_task_done(run_id, t))
            self.tasks[run_id] = task
            return task

    def _on_task_done(self, run_id, task):
        """任务完成时的回调"""
        try:
            if task.cancelled():
                logger.info(f"会话 {run_id} 的任务被取消")
            elif task.exception():
                logger.error(f"会话 {run_id} 的任务出现异常: {task.exception()}")
            else:
                logger.info(f"会话 {run_id} 的任务正常完成")
        except Exception as e:
            logger.error(f"处理会话 {run_id} 任务完成回调时出错: {e}")
        finally:
            # 只在任务确实完成时才清理，防止竞态条件
            if run_id in self.tasks and self.tasks[run_id] == task:
                del self.tasks[run_id]
                logger.info(f"已清理会话 {run_id} 的后台任务")


task_manager = TaskManager()

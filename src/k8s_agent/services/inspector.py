import logging
import threading
from datetime import datetime

from k8s_agent.models.inspection import store

logger = logging.getLogger(__name__)

_run_lock = threading.Lock()
INSPECTOR_USER_ID = "inspector"

INSPECTION_PROMPT = """请执行一次完整的集群运维巡检，按以下步骤进行：

1. 调用 analyze_pod_health 分析所有 Pod 的健康状况
2. 调用 diagnose_node_issues 检查节点是否存在问题
3. 调用 kubectl_top_nodes 查看节点资源使用情况
4. 如果发现有异常的 Pod（如 CrashLoopBackOff、OOMKilled、Pending 等），使用 kubectl_logs 查看这些 Pod 的日志，分析错误原因
5. 汇总巡检结果，包括：
   - 集群整体健康状态（健康 / 有告警 / 有严重问题）
   - 发现的具体问题列表（按严重程度排序）
   - 每个问题的简要分析和建议处理措施

请用简洁清晰的格式输出巡检报告。"""


def _execute(record_id: str) -> None:
    from k8s_agent.agent import agent

    if not _run_lock.acquire(blocking=False):
        store.update(record_id, status="failed", error="已有巡检任务正在执行，请稍后再试")
        return
    try:
        response = agent.run(input=INSPECTION_PROMPT, user_id=INSPECTOR_USER_ID)
        content = response.content if response.content else "(无回复)"
        store.update(record_id, status="completed", response=content)
        logger.info("巡检完成 record_id=%s", record_id)
    except Exception as e:
        store.update(record_id, status="failed", error=str(e))
        logger.error("巡检失败 record_id=%s: %s", record_id, e)
    finally:
        _run_lock.release()


def _new_record(trigger: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return store.insert(timestamp, trigger)


def run_inspection(trigger: str = "scheduled") -> str:
    record_id = _new_record(trigger)
    _execute(record_id)
    return record_id


def start_inspection(trigger: str = "manual") -> str:
    record_id = _new_record(trigger)
    threading.Thread(target=_execute, args=(record_id,), daemon=True).start()
    return record_id

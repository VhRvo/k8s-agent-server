from textwrap import dedent

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.litellm import LiteLLM

from k8s_agent.core.config import settings
from k8s_agent.tools.kubernetes import KubernetesTools

INSTRUCTIONS = dedent("""\
    你是 Kubernetes 智能故障诊断专家。

    ## 诊断方法论

    ### 1. 初始评估
    - 检查集群连接状态 (kubectl_cluster_info)
    - 分析整体 Pod 健康状况 (analyze_pod_health)
    - 检查节点状态 (diagnose_node_issues)

    ### 2. 定向调查
    - 获取资源详情 (kubectl_get, kubectl_describe)
    - 查看相关事件 (kubectl_get_events)
    - 分析资源使用情况 (kubectl_top_pods, kubectl_top_nodes)

    ### 3. 深入分析
    - 获取 Pod 日志 (kubectl_logs)
    - 必要时执行诊断命令 (kubectl_exec)

    ### 4. 根因分析与解决方案
    - 识别问题根本原因
    - 提供具体的修复步骤
    - 建议预防措施

    ## 沟通风格
    - 使用清晰的标题和要点
    - 包含具体的 kubectl 验证命令
    - 提供可执行的下一步操作
    - 支持中英文对话
    """)


def build_agent() -> Agent:
    db = SqliteDb(db_file=settings.agent_db_path)
    return Agent(
        name="K8sDiagnosisAgent",
        model=LiteLLM(
            id=settings.litellm_model_id,
            api_base=settings.litellm_api_base,
            api_key=settings.litellm_api_key,
        ),
        tools=KubernetesTools().get_tools(),
        instructions=INSTRUCTIONS,
        markdown=True,
        db=db,
        add_history_to_context=True,
        store_history_messages=True,
        num_history_messages=settings.agent_history_messages,
    )


agent = build_agent()

from textwrap import dedent

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.litellm import LiteLLM
from agno.team import Team, TeamMode

from k8s_agent.core.config import settings
from k8s_agent.tools.kubernetes import (
    ANALYST_TOOLS,
    INVESTIGATOR_TOOLS,
    OPERATOR_TOOLS,
)

LEADER_INSTRUCTIONS = dedent("""\
    你是 Kubernetes 智能运维团队的总协调员。

    ## 职责
    - 拆解用户运维请求，委派给合适的专家成员执行
    - 收集成员反馈，综合成清晰的最终报告
    - 不直接操作集群，一律通过成员完成

    ## 工作流程
    ### 诊断类请求
    1. 派侦察员采集相关事实（Pod/节点/事件/日志等）
    2. 派分析师综合分析、定位根因
    3. 你合成最终报告：整体健康状态 + 问题清单（按严重度）+ 修复建议

    ### 修复类请求
    1. 先派侦察员与分析师确认问题
    2. 派操作员执行修复
    3. 确认修复结果并汇报

    ## 成员
    - 侦察员（Investigator）：只读采集集群事实
    - 分析师（Analyst）：健康分析与根因定位
    - 操作员（Operator）：执行变更（仅在你明确要求时）

    ## 沟通风格
    - 清晰的标题和要点
    - 包含可执行的下一步
    - 支持中英文
    """)

INVESTIGATOR_INSTRUCTIONS = dedent("""\
    你是 Kubernetes 侦察员，负责只读采集集群事实。

    ## 规则
    - 只使用只读工具获取信息，绝不执行变更
    - 简洁汇报原始发现，不做诊断判断
    - 控制输出长度，聚焦关键数据
    """)

ANALYST_INSTRUCTIONS = dedent("""\
    你是 Kubernetes 分析师，负责健康分析与根因定位。

    ## 规则
    - 基于侦察员提供的事实综合分析
    - 识别问题根本原因，按严重程度排序
    - 给出具体的修复建议
    """)

OPERATOR_INSTRUCTIONS = dedent("""\
    你是 Kubernetes 操作员，负责执行集群变更。

    ## 规则
    - 仅在总协调员明确要求执行修复时操作
    - 保守优先，执行前确认目标资源
    - 执行后回报具体结果与影响
    """)

OPERATOR_ADVISOR_INSTRUCTIONS = dedent("""\
    你是 Kubernetes 操作方案顾问。

    ## 规则
    - 只生成变更方案，绝不执行任何集群操作
    - 明确列出目标资源、预期影响、风险、验证步骤和回滚方案
    - 信息不足时先指出需要补充的证据
    - 不声称已经完成任何变更
    """)

AGENT_PROFILES = [
    {
        "id": "team",
        "name": "总协调员",
        "english_name": "K8sOps Team",
        "description": "拆解任务、协调专家并汇总最终结论",
        "permission": "团队协调",
        "icon": "Users",
        "available": True,
    },
    {
        "id": "investigator",
        "name": "侦察员",
        "english_name": "Investigator",
        "description": "只读采集 Pod、节点、事件、日志和资源数据",
        "permission": "只读",
        "icon": "Search",
        "available": True,
    },
    {
        "id": "analyst",
        "name": "分析师",
        "english_name": "Analyst",
        "description": "根据集群证据定位根因并评估影响",
        "permission": "分析",
        "icon": "Activity",
        "available": True,
    },
    {
        "id": "operator",
        "name": "操作员",
        "english_name": "Operator",
        "description": "生成变更、验证和回滚方案，不直接执行",
        "permission": "方案模式",
        "icon": "Wrench",
        "available": False,
        "availability_note": (
            "后续版本将提供变更方案编排、人工审批、执行验证和回滚能力。"
        ),
    },
]


def _litellm() -> LiteLLM:
    return LiteLLM(
        id=settings.litellm_model_id,
        api_base=settings.litellm_api_base,
        api_key=settings.litellm_api_key,
    )


def build_team() -> Team:
    investigator = Agent(
        name="Investigator",
        model=_litellm(),
        tools=INVESTIGATOR_TOOLS,
        instructions=INVESTIGATOR_INSTRUCTIONS,
        description="只读采集集群事实：get/describe/logs/top/events/exec",
    )
    analyst = Agent(
        name="Analyst",
        model=_litellm(),
        tools=ANALYST_TOOLS,
        instructions=ANALYST_INSTRUCTIONS,
        description="健康分析与根因定位：analyze_pod_health/diagnose_node_issues",
    )
    operator = Agent(
        name="Operator",
        model=_litellm(),
        tools=OPERATOR_TOOLS,
        instructions=OPERATOR_INSTRUCTIONS,
        description="执行集群变更：apply/delete/scale/rollout",
    )
    db = SqliteDb(db_file=settings.agent_db_path)
    return Team(
        name="K8sOpsTeam",
        model=_litellm(),
        mode=TeamMode.coordinate,
        members=[investigator, analyst, operator],
        instructions=LEADER_INSTRUCTIONS,
        db=db,
        add_history_to_context=True,
        store_history_messages=True,
        num_history_messages=settings.agent_history_messages,
        stream_member_events=False,
    )


team = build_team()


def build_direct_agents() -> dict[str, Agent]:
    shared = {
        "db": team.db,
        "add_history_to_context": True,
        "store_history_messages": True,
        "num_history_messages": settings.agent_history_messages,
    }
    safe_investigator_tools = [
        tool for tool in INVESTIGATOR_TOOLS if tool.name != "kubectl_exec"
    ]
    return {
        "investigator": Agent(
            id="investigator",
            name="Investigator",
            model=_litellm(),
            tools=safe_investigator_tools,
            instructions=INVESTIGATOR_INSTRUCTIONS,
            description="只读采集集群事实",
            **shared,
        ),
        "analyst": Agent(
            id="analyst",
            name="Analyst",
            model=_litellm(),
            tools=ANALYST_TOOLS,
            instructions=ANALYST_INSTRUCTIONS,
            description="健康分析与根因定位",
            **shared,
        ),
        "operator": Agent(
            id="operator",
            name="Operator",
            model=_litellm(),
            tools=[],
            instructions=OPERATOR_ADVISOR_INSTRUCTIONS,
            description="只生成操作方案，不执行变更",
            **shared,
        ),
    }


direct_agents = build_direct_agents()


def get_agent_profiles() -> list[dict]:
    return [profile.copy() for profile in AGENT_PROFILES]

from k8s_agent.tools.kubernetes import KubernetesTools


def test_tools_count():
    tools = KubernetesTools().get_tools()
    assert len(tools) == 15


def test_tools_import():
    from k8s_agent.tools.kubernetes import kubectl_get, analyze_pod_health
    assert kubectl_get is not None
    assert analyze_pod_health is not None


from k8s_agent.tools.kubernetes import (
    ANALYST_TOOLS,
    INVESTIGATOR_TOOLS,
    OPERATOR_TOOLS,
)


def test_tool_group_counts():
    assert len(INVESTIGATOR_TOOLS) == 8
    assert len(ANALYST_TOOLS) == 2
    assert len(OPERATOR_TOOLS) == 5


def test_tool_groups_no_overlap_and_complete():
    all_tools = KubernetesTools().get_tools()
    grouped = INVESTIGATOR_TOOLS + ANALYST_TOOLS + OPERATOR_TOOLS
    assert len(grouped) == 15
    assert len({id(t) for t in grouped}) == 15
    assert {id(t) for t in grouped} == {id(t) for t in all_tools}

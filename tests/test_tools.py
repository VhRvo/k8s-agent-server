from k8s_agent.tools.kubernetes import KubernetesTools


def test_tools_count():
    tools = KubernetesTools().get_tools()
    assert len(tools) == 15


def test_tools_import():
    from k8s_agent.tools.kubernetes import kubectl_get, analyze_pod_health
    assert kubectl_get is not None
    assert analyze_pod_health is not None

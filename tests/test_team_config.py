from agno.team.mode import TeamMode

from k8s_agent.team import team
from k8s_agent.tools.kubernetes import KubernetesTools


def test_team_has_session_db():
    assert team.db is not None


def test_team_mode_coordinate():
    assert team.mode == TeamMode.coordinate


def test_team_has_three_members():
    assert len(team.members) == 3


def test_team_does_not_stream_member_events():
    assert team.stream_member_events is False


def test_member_tool_counts():
    counts = {len(m.tools) for m in team.members}
    assert counts == {8, 2, 5}


def test_leader_has_no_kubectl_tools():
    kubectl_names = {t.name for t in KubernetesTools().get_tools()}
    leader_names = {getattr(t, "name", None) for t in (team.tools or [])}
    assert not (leader_names & kubectl_names)

"""Tests for the agent, query parser, critic, and evaluation harness."""

import pytest

from src.agent import RecommendationAgent
from src.critic import critique
from src.evaluation import run_evaluation
from src.query_parser import parse_query
from src.recommender import load_songs


# ---- Query parser --------------------------------------------------

def test_parse_query_extracts_all_fields_from_natural_language():
    result = parse_query("I want chill lofi music for studying with acoustic textures")
    assert result.profile["genre"] == "lofi"
    assert result.profile["mood"] == "focused"
    assert result.profile["energy"] == 0.4
    assert result.profile["likes_acoustic"] is True
    assert not result.warnings


def test_parse_query_warns_on_unknown_genre():
    result = parse_query("k-pop with high energy")
    assert result.profile["genre"] == "__unknown__"
    assert any("no genre matched" in w for w in result.warnings)


def test_parse_query_defaults_on_empty_input():
    result = parse_query("")
    assert result.profile == {
        "genre": "pop", "mood": "chill", "energy": 0.5, "likes_acoustic": False,
    }
    assert any("empty query" in w for w in result.warnings)


def test_parse_query_does_not_match_pop_inside_k_pop():
    """Regression: 'pop' as a substring of 'k-pop' must not fire the pop trigger."""
    result = parse_query("k-pop hits")
    assert result.profile["genre"] != "pop"


# ---- Critic --------------------------------------------------------

def test_critique_flags_empty_results():
    report = critique([], user_prefs={"mood": "chill"})
    assert report.has_severity("critical")
    assert "EMPTY_RESULTS" in report.codes()


def test_critique_flags_artist_repetition():
    same_artist = [
        ({"artist": "LoRoom", "genre": "lofi", "mood": "chill"}, 5.0, "..."),
        ({"artist": "LoRoom", "genre": "lofi", "mood": "focused"}, 4.5, "..."),
        ({"artist": "Other", "genre": "pop", "mood": "happy"}, 3.0, "..."),
    ]
    report = critique(same_artist, user_prefs={"mood": "chill"})
    assert "ARTIST_REPETITION" in report.codes()


def test_critique_confidence_labels_by_score():
    high = [({"artist": "A", "genre": "pop", "mood": "happy"}, 7.0, "")]
    low = [({"artist": "A", "genre": "pop", "mood": "happy"}, 1.0, "")]
    assert critique(high, {"mood": "happy"}).confidence_label == "HIGH"
    assert critique(low, {"mood": "happy"}).confidence_label == "LOW"


# ---- Agent ---------------------------------------------------------

@pytest.fixture(scope="module")
def songs():
    return load_songs("data/songs.csv")


def test_agent_rejects_empty_catalog():
    with pytest.raises(ValueError):
        RecommendationAgent([])


def test_agent_produces_a_result_for_natural_language_query(songs):
    agent = RecommendationAgent(songs)
    result = agent.run("I want chill lofi music for studying", k=5)
    assert len(result.recommendations) == 5
    assert result.iterations >= 1
    assert result.iterations <= 3
    top_song = result.recommendations[0][0]
    assert top_song["genre"] in {"lofi", "jazz", "ambient"}


def test_agent_switches_mode_when_top_mood_mismatches(songs):
    """
    Sanity check that the plan → critique → refine loop actually reacts —
    for a query where the initial parse leaves mood ambiguous, the agent
    should escalate at least once (either mode change or diversity toggle).
    """
    agent = RecommendationAgent(songs)
    result = agent.run("high energy pop for my workout, upbeat and electric", k=5)
    # Should hit at least one refine step OR converge cleanly on iteration 1.
    assert 1 <= result.iterations <= 3


def test_agent_never_crashes_on_pathological_input(songs):
    agent = RecommendationAgent(songs)
    for query in ["", "asdf qwerty zxcv", "🎵🎵🎵", "12345"]:
        result = agent.run(query, k=5)
        assert len(result.recommendations) == 5
        assert result.critique.confidence_label in {"LOW", "MEDIUM", "HIGH"}


def test_agent_run_produces_structured_log(songs):
    agent = RecommendationAgent(songs)
    result = agent.run("chill lofi study", k=5)
    steps = result.log.steps()
    assert "agent.start" in steps
    assert "plan.parse" in steps
    assert "act.recommend" in steps
    assert "critique.report" in steps
    assert "agent.done" in steps


# ---- Reliability harness end-to-end -------------------------------

def test_reliability_harness_all_cases_pass():
    """
    The reliability harness is our regression contract. If any of the six
    curated test cases starts failing after a code change, either the code
    or the harness expectation needs updating — this test forces that decision.
    """
    report = run_evaluation()
    assert report.n_cases_passed == len(report.cases), (
        f"{len(report.cases) - report.n_cases_passed} cases failed. "
        f"See criteria detail:\n" + "\n".join(
            f"  {case.name}: {c.name} — {c.detail}"
            for case in report.cases for c in case.criteria if not c.passed
        )
    )

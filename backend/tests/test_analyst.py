from app.agents.analyst import heuristic_analyze


def test_classifies_cybersecurity():
    r = heuristic_analyze("Privilege escalation on Linux – Hack The Box walkthrough", "We exploit a SUID binary")
    assert r.category == "ciberseguridad"
    assert r.subtopic == "pentesting"


def test_classifies_spanish_football_speed():
    r = heuristic_analyze("Cómo mejorar tu aceleración en fútbol sala", "Ejercicios de sprint y pliometría")
    assert r.category == "deporte"
    assert r.subtopic == "velocidad"
    assert r.quality > 0.5  # "cómo" = señal educativa


def test_clickbait_penalized():
    good = heuristic_analyze("How transformers work, explained", "A detailed look at attention " * 20)
    bad = heuristic_analyze("YOU WON'T BELIEVE THIS AI!!! 😱", "")
    assert bad.clickbait and not good.clickbait
    assert good.quality > bad.quality + 0.2


def test_prior_category_breaks_ties():
    r = heuristic_analyze("Mi rutina de la mañana", "", prior_category="mente")
    assert r.category == "mente"


def test_politics_flagged():
    r = heuristic_analyze("Elecciones: el presidente y el senado", "campaña electoral, votos y partido")
    assert r.political

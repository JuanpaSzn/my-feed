from app.agents.commands import heuristic_parse


def test_agents_command():
    p = heuristic_parse("Muéstrame los últimos avances en agentes autónomos")
    assert "ia" in p["categories"]
    assert "agentes" in p["subtopics"]
    assert p["max_age_days"]
    assert any("agente" in k for k in p["keywords"])


def test_futsal_acceleration():
    p = heuristic_parse("Quiero vídeos sobre cómo mejorar mi aceleración en fútbol sala")
    assert p["categories"][0] == "deporte"
    assert "velocidad" in p["subtopics"]


def test_cyber_projects():
    p = heuristic_parse("Enséñame proyectos interesantes de ciberseguridad")
    assert "ciberseguridad" in p["categories"]


def test_science_this_week_and_format():
    p = heuristic_parse("Quiero conocer los descubrimientos científicos más importantes de esta semana, solo cortos")
    assert "ciencia" in p["categories"]
    assert p["max_age_days"] == 7
    assert p["format"] == "short"

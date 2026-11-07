import numpy as np

from paperflip.dashboard import (
    energy_breakdown,
    exact_at_pressure,
    model_fingerprint,
    model_with_pressure,
    tiny_business_model,
)


def test_tiny_example_energy_terms_and_pressure_are_deterministic():
    model = tiny_business_model((7500, 5500, 6000), 1500, 1050)
    paper = np.array([-1, -1, -1], dtype=np.int8)
    digital = np.array([1, 1, 1], dtype=np.int8)
    p = 4900
    breakdown = energy_breakdown(model, p, paper)
    assert breakdown["total_energy_int"] == model_with_pressure(model, p).energy(paper, 2026)
    assert model_with_pressure(model, p).energy(paper, 2026) != model_with_pressure(model, p).energy(digital, 2026)
    assert exact_at_pressure(model, p).energy <= breakdown["total_energy_int"]
    assert model_fingerprint(model) == model_fingerprint(model)


def test_zero_field_without_ties_has_a_legitimate_degenerate_pair():
    model = tiny_business_model((3500, 3500, 3500), 0, 0)
    # At A=r all fields are zero, so paper/digital extrema are both ground states.
    result = exact_at_pressure(model, 3500)
    assert np.all(result.paper_state == -1)
    assert np.all(result.digital_state == 1)

from src.game.action_modifiers import compute_action_modifier, evaluate_check
from src.game.models import PlayerCharacter

def _pc():
    return PlayerCharacter(
        pc_id="pc1",
        player_name="Alice",
        name="Aria",
        gender="",
        ancestry="human",
        archetype="rogue",
        level=1,
        concept="sneaky",
        stats={"STR": 8, "DEX": 14, "INT": 12},
        max_hp=10,
        current_hp=10,
    )

def test_compute_action_modifier_uses_stats():
    pc = _pc()
    mod = compute_action_modifier(pc, "stealth_check", "stealth_check: sneak")
    assert isinstance(mod, int)

def test_evaluate_check_returns_dc_and_outcome():
    dc, outcome = evaluate_check(total=15, action_type="stealth_check", reason="stealth_check: sneak")
    assert dc is not None
    assert outcome in {"success", "fail", "mixed", None}

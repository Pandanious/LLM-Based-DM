import random
import pytest 


from src.game.dice import roll_dice
from src.agent.dm_dice import parse_roll_request,parse_action_type,ensure_action_label_in_reason

def _rand_int(sequence):
    if isinstance(sequence, int):
        sequence = [sequence]
    seq = iter(sequence)


    def _randint(_a,_b):
        return next(seq)
    
    return _randint

def test_roll_parses_modifiers(monkeypatch):
    monkeypatch.setattr(random,"randint",_rand_int([4,5]))
    result = roll_dice("2d6+3")
    assert result.rolls == [4,5]
    assert result.modifier == 3
    assert result.total == 12
    assert result.expression == "2d6+3"

def test_one_dice_roll(monkeypatch):
    monkeypatch.setattr(random,"randint",_rand_int(6))
    result = roll_dice("d6")
    assert result.rolls == [6]
    assert result.total == 6
    assert result.modifier == 0


def test_request_extracts_expr_and_reason():
    rr = parse_roll_request("[ROLL_REQUEST: 1d20+3 | stealth_check: sneak past guard]")
    assert rr == ("1d20+3", "stealth_check: sneak past guard")

def test_request_ignores_missing():
    assert parse_roll_request("no roll here") is None

def test_action_type_known_and_unknown():
    assert parse_action_type("attack: hit the goblin") == "attack"
    assert parse_action_type("unknown: something") is None

def test_adds_missing_label():
    reason = ensure_action_label_in_reason("sneak past guard", "stealth_check")
    assert reason.startswith("stealth_check:")
    
    reason2 = ensure_action_label_in_reason("attack: goblin", "stealth_check")
    assert reason2 == "attack: goblin"




@pytest.mark.parametrize("expr",["", "2d", "abc", "2d6++1", "d"])
def test_wrong_express_dice_roll(expr):
    with pytest.raises(ValueError):
        roll_dice(expr)

        

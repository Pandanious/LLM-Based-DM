import random
import pytest 


from src.game.dice import roll_dice

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


@pytest.mark.parametrize("expr",["", "2d", "abc", "2d6++1", "d"])
def test_wrong_express_dice_roll(expr):
    with pytest.raises(ValueError):
        roll_dice(expr)

        

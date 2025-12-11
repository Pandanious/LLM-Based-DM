import pytest

from src.agent.context_parser import parse_command,CommandKind,register_action_synonym,ACTION_SYNONYMS


def test_meta_cmd_help():
    cmd = parse_command("/help show tips")
    assert cmd is not None
    assert cmd.kind == CommandKind.META
    assert cmd.needs_dice is False
    assert cmd.base == "/help"
    assert cmd.description == "show tips"
    assert cmd.action_type is None

def test_attack_light_damage():
    cmd = parse_command("/attack goblin")
    assert cmd.kind == CommandKind.MECHANICAL
    assert cmd.needs_dice is True
    assert cmd.action_type == "damage_light"
    assert cmd.description == "goblin"
    assert cmd.base == "/attack"

def test_synonym_use_list():
    cmd = parse_command("/action sneak past guard")
    assert cmd is not None
    assert cmd.kind == CommandKind.MECHANICAL
    assert cmd.needs_dice is True
    assert cmd.action_type == "stealth_check"
    assert cmd.description == "sneak past guard"
    assert cmd.base == "/action"

def test_non_command_returns_none():
    assert parse_command("say hi") is None
    assert parse_command("") is None    

def test_register_action_synonym_allows_new_trigger():
    register_action_synonym("zap", "damage_light")
    assert ACTION_SYNONYMS["zap"] == "damage_light"
    cmd = parse_command("/zap the golem")
    assert cmd is not None
    assert cmd.action_type == "damage_light"
    assert cmd.needs_dice is True
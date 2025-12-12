# Project Idea: Local RPG Dungeon Master

## Purpose:
This is a project done to showcase a simple agentic AI running locally which can help users set up their own local or over the internet TTRPG sessions.
This is aimed at reviewers who want to see on-device inference and basic testing/CI.

## Overview:

## Tech Choices:
A local LLM model was used, python was used for most of the coding, Llama-cpp-python (local GGUf, Offline), JSON saves over a Database.  

## Persistance:
UI actions change 'GameState'; Saves/Load bundles to 'saves/'; turn logs and summaries are written for context; share state allows multiple users based on Game ID. Authentication via ngrok.

## Retrival and Context (RAG):
Keyword seach over saved JSON to build context blocks for prompts. This was decided overr vector search for slimplicity. Context is added before LLM calls.

### Python Backend:

#### Dice and Mechanics handling:
Dice is rolled locally. 'ROLL_REQUEST' is parsed from LLM. Modifiers are calculated from the Player Character statistics. The LLM narrates, but 

## Performance Considerations:
Present setup based on 3060ti GPU. Context trimming added for memory consideration. Model footprint ~ 6-7 GB. Can always be toggled to CPU only.

## Testing and CI:
Unit test suite covers: Dice, Parser, Save/Load, RAG, Summarization (stubbed)
Optional real LLM test gated by 'RUN_LLM_TESTS' + model presence. CI (GitHub Actions) runs model free tests only.

## Limitation and Future Work:
Basic keyword RAG (no embeddings), minimal logging/metrics.
Trust-based access over the internet through ngrok. Basic password authentication, each person can set their own.

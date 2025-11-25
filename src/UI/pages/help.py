#PLACEHOLDER - AI GEN BASED ON REPO - NOT FINAL

import sys
from pathlib import Path

import streamlit as st

# --- Make src importable ---
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.game.game_state import get_global_games  # optional, for world/game info


def get_game_and_world():
    query_params = st.query_params
    game_id = query_params.get("game_id", "default")

    games = get_global_games()
    game = games.get(game_id)

    if not game or game.world is None:
        return None, None, game_id

    return game, game.world, game_id


st.set_page_config(page_title="How to Play – Local DM", layout="wide")
st.title("How to Play / Help")

game, world, game_id = get_game_and_world()

st.markdown(f"**Game ID:** `{game_id}`")

if world is not None:
    st.markdown(f"**Current World:** **{world.title}**")
    st.markdown(world.world_summary)
else:
    st.info(
        "No active world detected for this Game ID yet. "
        "You can still read the instructions below."
    )

st.markdown("---")

# =========================
# Section: Overall Flow
# =========================

st.header("1. Overall Game Flow")

st.markdown(
    """
1. **Start / Reset Game**
   - In the main app, enter a **Game ID** in the sidebar.
   - Click **Start/Reset Game** to clear world, chat, and characters for that Game ID.

2. **Create a World**
   - In the main app chat, the DM first asks you to **describe the world or setting**.
   - Write a short description (genre, tone, themes), then the system generates:
     - a world title,
     - world summary and lore,
     - major & minor locations,
     - and a set of NPCs.

3. **Create Player Characters**
   - Open the **Character Manager** (button on the right of the main app).
   - For each player name:
     - choose character name, gender, ancestry,
     - write a short concept,
     - click **Generate / Re-roll**.
   - The system uses the LLM to produce a **character sheet** and saves it.

4. **Start Playing**
   - Return to the main app.
   - If needed, use **Refresh Party Summary** so the DM sees the latest characters.
   - Type **“start”** to begin the adventure using the existing party.
   - From then on, you play by typing normal text (in-character) and special `/action` commands.
"""
)

st.markdown("---")

# =========================
# Section: Commands
# =========================

st.header("2. Commands and Actions")

st.subheader("2.1 Normal in-character messages")

st.markdown(
    """
- Just type what your character does or says:

  - `I lean on the bar and ask the bartender about work.`
  - `I tell the gang leader we want safe passage.`

- The DM responds with narration and may suggest options **only when you have not clearly chosen an action**.
"""
)

st.subheader("2.2 Mechanical actions: `/action ...`")

st.markdown(
    """
To trigger **dice mechanics**, use the `/action` command:

- `/action I try to sneak past the guard`
- `/action I pick the lock on the door`
- `/action I shoot at the drone`
- `/action I search the room carefully`

The system interprets your `/action` and maps it to one of several **standard action types** (used for stats and skills):

- `attack` – basic attacks and strikes  
- `stealth_check` – sneaking, hiding, avoiding detection  
- `perception_check` – noticing details, sounds, danger  
- `lockpick` – opening locks, bypassing mechanisms  
- `persuasion` – convincing, calming, negotiating  
- `athletics` – climbing, jumping, pushing, breaking  
- `acrobatics` – balancing, agile movement, dodging  
- `damage_light` – light weapon damage (dagger, quick shots)  
- `damage_heavy` – heavy weapon damage (big swings, powerful hits)

You can also type shortcuts like:

- `/sneak past the guard`
- `/perception check the door`
- `/shoot the drone`

These are automatically normalized to a canonical `/action ...` form by the system, so the DM will treat them as mechanical actions.
"""
)

st.subheader("2.3 Out-of-character or meta commands")

st.markdown(
    """
Some slash commands are reserved for **meta / system use** (not dice):

- `/ooc ...` – out-of-character comments.
- `/help` – you can ask for in-game help or clarification.
- These do not trigger dice directly.
"""
)

st.markdown("---")

# =========================
# Section: Dice and Checks
# =========================

st.header("3. Dice, Stats, and Success / Failure")

st.markdown(
    """
### 3.1 How dice rolls work

1. You declare an action with `/action ...` (or shortcut).
2. The DM may respond with a special line:

   `\[ROLL_REQUEST: 1d20+2 | stealth_check: sneak past the guard]`

   This means: the DM wants a **stealth check** to resolve your action.

3. The **game system** (not the DM) then:
   - looks up your character from the current **party**,
   - uses your **stats** (STR, DEX, CON, INT, WIS, CHA),
   - checks your **skills** (e.g. stealth, perception),
   - considers simple difficulty cues in the reason text (“easy”, “hard”, etc.),
   - builds a final dice expression like `1d20+3` or `1d20-1`,
   - rolls it and computes **total**, **DC**, and **outcome** (success/failure).

4. The game adds a system line:

   `\[ROLL_RESULT: 1d20+3 = 17 (rolls=[14], modifier=3, action_type=stealth_check, dc=13, outcome=success, actor=Your PC Name) | stealth_check: sneak past the guard]`

5. The DM then sees this and narrates the outcome based on the result.
"""
)

st.markdown(
    """
### 3.2 Modifiers and difficulty

- Modifiers come from:
  - your relevant **ability score** (e.g. DEX for stealth),
  - any matching **skills** (for a small proficiency bonus),
  - simple difficulty hints in the DM’s reason text:
    - “easy / simple” → easier DC / bonus
    - “hard / difficult / risky” → harder DC / penalty
    - “very hard / extremely” → very high DC / strong penalty

- Checks use a d20:
  - `1d20 + modifiers` vs. a target DC.
  - Outcome is recorded as **success** or **failure** in the roll result.

- Damage actions:
  - `damage_light` → typically a small die (e.g. `1d6 + mod`)
  - `damage_heavy` → larger die (e.g. `1d10 + mod`)
"""
)

st.markdown("---")

# =========================
# Section: Pages & Buttons
# =========================

st.header("4. Pages and Buttons in the UI")

st.markdown(
    """
### 4.1 Main page (Game Log)

- **Game ID** (sidebar): all players who use the same ID share the same world.
- **Start/Reset Game**:
  - Clears world, messages, and characters for that Game ID.
- **Reset the LLM Model**:
  - Reloads the underlying language model with fresh settings.
- **Game Log**:
  - Shows all player and DM messages.
  - This is where you type to actually play.

### 4.2 Right column buttons

- **Open World Information**:
  - Opens a page showing world summary, lore, locations, and NPCs.
- **Open Character Manager**:
  - Opens the page to create / edit characters.

- **Refresh Party Summary** (if you added this button):
  - Re-loads characters from disk for the current world.
  - Rebuilds the PARTY SUMMARY system message so the DM sees the latest party.
  - Also saves the summary to a text file for debugging (if implemented).

### 4.3 This page (How to Play / Help)

- Accessible via the **“How to Play / Help”** button in the main sidebar.
- Explains:
  - the game flow,
  - commands and actions,
  - how dice and stats work,
  - what each button and page is for.
"""
)

st.markdown("---")

st.header("5. Tips")

st.markdown(
    """
- If the DM ever seems to **ignore your character sheet** or invent a new one:
  - Make sure your characters were generated in the Character Manager.
  - Use **Refresh Party Summary** so the DM sees the correct party.
  - Then type **“start”** to begin, and the DM should introduce your existing PCs.

- If dice rolls don’t trigger:
  - Make sure your command starts with `/action` or a supported shortcut like
    `/sneak`, `/perception`, `/shoot`. The system normalizes these.

- If something feels off, you can always describe your intent in plain text.
  The system is designed to keep the rules light and story-focused.
"""
)

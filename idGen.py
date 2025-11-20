import os
import json

STATE_FILE = "id_state.json"


def load_state():
    """Load the last used user/session IDs from file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If file is corrupted or unreadable, start fresh
            return {"user": 0, "session": 0}
    return {"user": 0, "session": 0}


def save_state(state):
    """Save the current user/session ID state to file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def generate_ids():
    """Generate new incremental user and session IDs."""
    state = load_state()

    state["user"] += 1
    state["session"] += 1

    user_id = f"u{state['user']:04d}"
    session_id = f"s{state['session']:04d}"

    save_state(state)

    return user_id, session_id

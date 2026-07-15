"""Assignment-scoped launch state stored in the signed session cookie."""

from collections.abc import Mapping, MutableMapping

LAUNCH_CONTEXTS_KEY = "launch_contexts"


def get_launch_context(
    session: Mapping[str, object], assignment_id: str
) -> dict[str, str] | None:
    """Return an assignment's launch context, including legacy cookie support."""
    contexts = session.get(LAUNCH_CONTEXTS_KEY)
    if isinstance(contexts, dict):
        context = contexts.get(assignment_id)
        if isinstance(context, dict):
            lineitem = context.get("ags_lineitem", "")
            return {
                "ags_lineitem": lineitem if isinstance(lineitem, str) else "",
            }

    if session.get("assignment_id") == assignment_id:
        lineitem = session.get("ags_lineitem", "")
        return {
            "ags_lineitem": lineitem if isinstance(lineitem, str) else "",
        }

    return None


def record_launch_context(
    session: MutableMapping[str, object],
    *,
    user_id: int,
    assignment_id: str,
    ags_lineitem: str,
) -> None:
    """Record one launch while preserving this user's other assignments."""
    same_user = session.get("user_id") == user_id
    contexts: dict[str, dict[str, str]] = {}

    if same_user:
        existing = session.get(LAUNCH_CONTEXTS_KEY)
        if isinstance(existing, dict):
            for key, value in existing.items():
                if not isinstance(key, str) or not isinstance(value, dict):
                    continue
                lineitem = value.get("ags_lineitem", "")
                contexts[key] = {
                    "ags_lineitem": lineitem if isinstance(lineitem, str) else "",
                }

        legacy_assignment = session.get("assignment_id")
        if isinstance(legacy_assignment, str):
            legacy_context = get_launch_context(session, legacy_assignment)
            if legacy_context is not None:
                contexts.setdefault(legacy_assignment, legacy_context)

    contexts[assignment_id] = {"ags_lineitem": ags_lineitem}
    session["user_id"] = user_id
    session[LAUNCH_CONTEXTS_KEY] = contexts
    session.pop("assignment_id", None)
    session.pop("ags_lineitem", None)

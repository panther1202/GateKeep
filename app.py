import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from post_queue import PostQueue, QueueError
from gemini_client import generate_draft, find_buzzwords, GeminiError
from linkedin_client import LinkedInError
from publish import publish_one

load_dotenv()
POSTS_PATH = Path(__file__).parent / "posts.json"
queue = PostQueue(POSTS_PATH)


def recent_pillars(n=3):
    """Pillars of the last n posts, newest first, to steer a no-topic draft.

    Only nudges the model away from repeating itself; not a hard exclusion.
    """
    return [p["pillar"] for p in reversed(queue.all_posts())][:n]


def delete_control(post):
    """Two-click confirm delete for a queued (draft/approved) post."""
    pid = post["id"]
    confirm_key = f"confirm_del_{pid}"
    if st.session_state.get(confirm_key):
        st.warning("Delete this post permanently? This cannot be undone.")
        yes, no = st.columns(2)
        if yes.button("Yes, delete", key=f"yesdel_{pid}"):
            queue.delete_post(pid)
            st.session_state.pop(confirm_key, None)
            st.rerun()
        if no.button("Cancel", key=f"canceldel_{pid}"):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    elif st.button("Delete", key=f"del_{pid}"):
        st.session_state[confirm_key] = True
        st.rerun()


def publish_control(post, edited_text):
    """Two-click confirm to publish a post to live LinkedIn right now.

    Saves any pending text edit first, then publishes (approving a draft on the
    way). Publishing is irreversible, hence the explicit confirm.
    """
    pid = post["id"]
    confirm_key = f"confirm_pub_{pid}"
    if st.session_state.get(confirm_key):
        st.warning("Publish this to your live LinkedIn now? This cannot be undone.")
        yes, no = st.columns(2)
        if yes.button("Yes, publish", key=f"yespub_{pid}"):
            token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
            urn = os.environ.get("LINKEDIN_AUTHOR_URN")
            if not token or not urn:
                st.error("LinkedIn credentials missing from .env (run reauth.py).")
            else:
                try:
                    if edited_text.strip() and edited_text.strip() != post["text"]:
                        queue.update_text(pid, edited_text.strip())
                    post_urn = publish_one(queue, pid, token, urn)
                    st.success(f"Published to LinkedIn ({post_urn}).")
                except (LinkedInError, QueueError) as e:
                    st.error(f"Publish failed: {e}")
            st.session_state.pop(confirm_key, None)
            st.rerun()
        if no.button("Cancel", key=f"nopub_{pid}"):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    elif st.button("Publish now", key=f"pub_{pid}"):
        st.session_state[confirm_key] = True
        st.rerun()


def refine_control(post):
    """Ask Gemini to revise this draft in place from a plain-language note.

    Overwrites the text (no undo, by choice). The pillar tag is kept: a
    refinement sharpens a post, it does not re-file it.
    """
    pid = post["id"]
    note = st.text_input(
        "Refine", key=f"refine_{pid}", placeholder="e.g. shorter, lead with the number"
    )
    if st.button("Regenerate", key=f"regen_{pid}"):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            st.error("GEMINI_API_KEY missing from .env")
            return
        try:
            with st.spinner("Revising..."):
                _, revised = generate_draft(api_key, note, previous=post["text"])
            queue.update_text(pid, revised)
            st.rerun()
        except (GeminiError, QueueError) as e:
            st.error(str(e))


def buzzword_warning(text):
    """Flag any banned buzzwords in the current text so the reviewer cuts them.

    Deterministic check (find_buzzwords); does not block, just warns.
    """
    flagged = find_buzzwords(text)
    if flagged:
        st.warning("Banned buzzwords present: " + ", ".join(flagged) + ". Edit before publishing.")


st.set_page_config(page_title="GateKeep", page_icon="✅")
st.title("GateKeep — LinkedIn post control panel")

# Nothing can publish without an OAuth token, and the failure was previously
# invisible until you clicked into the publish confirm. Say it up front.
if not (os.environ.get("LINKEDIN_ACCESS_TOKEN") and os.environ.get("LINKEDIN_AUTHOR_URN")):
    st.error(
        "LinkedIn is not connected: no access token in .env. Approving a post will "
        "queue it but nothing will publish. Run `python reauth.py`, then restart this app."
    )

# --- New post ------------------------------------------------------------
# One box for both paths. Say what you want and let Gemini write it, or paste
# text you already wrote. No pillar picker: the model tags what it produced
# (see gemini_client._split_pillar) and hand-written posts are tagged "manual".
st.header("New post")
with st.form("new_post", clear_on_submit=True):
    request = st.text_area(
        "What do you want to post about, and how should it land?",
        height=140,
        placeholder=(
            "e.g. the race condition I fixed in the workflow engine, "
            "engineer-to-engineer and a bit opinionated. "
            "Leave empty and hit Draft with AI to let it pick a topic."
        ),
    )
    draft_col, manual_col = st.columns(2)
    do_draft = draft_col.form_submit_button("Draft with AI")
    do_manual = manual_col.form_submit_button("Add as-is")

if do_manual:
    if not request.strip():
        st.error("Nothing to add. Type the post text first.")
    else:
        queue.add_post(text=request.strip(), pillar="manual", source="manual")
        st.success("Draft added.")
        st.rerun()

if do_draft:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY missing from .env")
    else:
        try:
            with st.spinner("Drafting..."):
                pillar, draft = generate_draft(api_key, request, recent_pillars())
            queue.add_post(text=draft, pillar=pillar, source="generated")
            st.success(f"Draft added below for review (tagged {pillar}).")
            st.rerun()
        except GeminiError as e:
            st.error(str(e))

# --- Review pending drafts ----------------------------------------------
st.header("Pending review")
pending = queue.pending_drafts()
if not pending:
    st.caption("No drafts awaiting review.")
for post in pending:
    with st.container(border=True):
        st.caption(f"{post['pillar']} · {post['source']} · {post['created_at']}")
        edited = st.text_area("Text", value=post["text"], key=f"edit_{post['id']}", height=160)
        buzzword_warning(edited)
        c1, c2, c3 = st.columns(3)
        if c1.button("Save edits", key=f"save_{post['id']}"):
            queue.update_text(post["id"], edited.strip())
            st.rerun()
        if c2.button("Approve", key=f"approve_{post['id']}"):
            if edited.strip() != post["text"]:
                queue.update_text(post["id"], edited.strip())
            queue.approve(post["id"])
            st.rerun()
        if c3.button("Reject", key=f"reject_{post['id']}"):
            queue.reject(post["id"])
            st.rerun()
        if post["source"] == "generated":
            refine_control(post)
        publish_control(post, edited)
        delete_control(post)

# --- Approved (waiting to publish) --------------------------------------
st.header("Approved — waiting to publish")
approved = [p for p in queue.all_posts() if p["status"] == "approved"]
if not approved:
    st.caption("Nothing approved yet.")
for post in sorted(approved, key=lambda p: p["approved_at"]):
    with st.container(border=True):
        st.caption(f"{post['pillar']} · approved {post['approved_at']}")
        edited = st.text_area(
            "Text", value=post["text"], key=f"edit_appr_{post['id']}", height=160
        )
        buzzword_warning(edited)
        save_col, _ = st.columns(2)
        if save_col.button("Save edits", key=f"save_appr_{post['id']}"):
            queue.update_text(post["id"], edited.strip())
            st.rerun()
        publish_control(post, edited)
        delete_control(post)

# --- History -------------------------------------------------------------
st.header("History")
history = [p for p in queue.all_posts() if p["status"] in ("posted", "rejected")]
for post in reversed(history):
    label = "posted" if post["status"] == "posted" else "rejected"
    when = post["posted_at"] or post["created_at"]
    st.markdown(f"- **{label}** · {post['pillar']} · {when}: {post['text'][:80]}…")

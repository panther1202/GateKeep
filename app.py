import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from post_queue import PostQueue, VALID_PILLARS, QueueError
from gemini_client import generate_draft, find_buzzwords, GeminiError, PILLAR_PROMPTS
from linkedin_client import LinkedInError
from publish import publish_one

load_dotenv()
POSTS_PATH = Path(__file__).parent / "posts.json"
queue = PostQueue(POSTS_PATH)

GENERATABLE_PILLARS = list(PILLAR_PROMPTS.keys())  # excludes "manual"


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


def buzzword_warning(text):
    """Flag any banned buzzwords in the current text so the reviewer cuts them.

    Deterministic check (find_buzzwords); does not block, just warns.
    """
    flagged = find_buzzwords(text)
    if flagged:
        st.warning("Banned buzzwords present: " + ", ".join(flagged) + ". Edit before publishing.")


st.set_page_config(page_title="GateKeep", page_icon="✅")
st.title("GateKeep — LinkedIn post control panel")

# --- Add a manual post ---------------------------------------------------
st.header("Add a manual post")
with st.form("manual", clear_on_submit=True):
    manual_text = st.text_area("Post text", height=160)
    manual_pillar = st.selectbox("Pillar / tag", sorted(VALID_PILLARS))
    if st.form_submit_button("Add draft") and manual_text.strip():
        queue.add_post(text=manual_text.strip(), pillar=manual_pillar, source="manual")
        st.success("Draft added.")
        st.rerun()

# --- Generate a draft with Gemini ---------------------------------------
st.header("Generate a draft (Gemini)")
gen_pillar = st.selectbox("Pillar", GENERATABLE_PILLARS, key="gen_pillar")
gen_context = st.text_input("Optional extra context")
if st.button("Generate"):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY missing from .env")
    else:
        try:
            draft = generate_draft(api_key, gen_pillar, gen_context)
            queue.add_post(text=draft, pillar=gen_pillar, source="generated")
            st.success("Generated draft added below for review.")
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

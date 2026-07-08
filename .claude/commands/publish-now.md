# /publish-now - Manually Trigger a Publish Run

Runs the same logic as the scheduled weekly job, on demand - for testing or when the user doesn't want to wait for the schedule.

## Steps

1. Run `python publish.py` and show the output.
2. If it published something: report which post (id, first line of text, pillar) and the returned `linkedin_post_id`.
3. If the queue had no `approved` posts: tell the user plainly and suggest running `/generate-post` or approving something in the Streamlit app (`streamlit run app.py`).
4. If it failed (LinkedIn API error): show the error from `logs/publish.log`, and confirm the post's status is still `approved` (not silently lost) so it will retry next scheduled run.

## Notes

This is a real publish - it posts to the live LinkedIn profile. Only run it when the user actually wants that post to go out now, not as a dry-run check. If the user wants to inspect what *would* publish without actually posting, read `posts.json` and report the oldest `approved` entry instead of running the script.

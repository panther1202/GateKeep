# /reauth - Refresh the LinkedIn OAuth Token

LinkedIn's access token expires roughly every 60 days. This walks the user through getting a new one - it cannot be done headlessly, LinkedIn requires an interactive browser login from the account owner.

## Steps

1. Check `.env` for the current token's issued/expiry date if tracked; tell the user if it's actually expired or if they're refreshing early.
2. Run `python reauth.py`, which prints a LinkedIn authorization URL.
3. Tell the user to open that URL in their browser, log in as themselves, and approve the app.
4. LinkedIn redirects to a localhost URL with a `code` parameter - tell the user to paste the full redirected URL (or just the code) back into the terminal prompt `reauth.py` shows.
5. `reauth.py` exchanges the code for a new access token and writes it into `.env`, replacing the old one.
6. Confirm success by showing the new token's expiry date (do not print the token value itself).

## Notes

Never attempt to automate the browser login step - it requires the user's own LinkedIn credentials and consent. Do not ask the user to paste their LinkedIn password anywhere; only the OAuth redirect URL/code is needed.

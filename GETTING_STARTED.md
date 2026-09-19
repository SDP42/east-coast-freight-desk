# Getting Started — How to Run and View This Project

Step-by-step, assuming no prior experience with terminals or dev servers.

## What you need open

Two things need to run at the same time: the **backend** (the API/data engine)
and the **frontend** (the website you actually look at). Think of the backend
as the kitchen and the frontend as the dining room — the frontend calls the
backend to get real data.

## 0. First-time only: loading the real data

Before starting the backend for the first time (or after deleting the database
file), load the real research data — port constraints, freight rate history,
commodity prices, disruption events:

```bash
cd /Users/swayampanchal/Desktop/SAIL/backend
source .venv/bin/activate
alembic upgrade head          # creates the database tables
cd ../scripts
python run_all.py             # loads all the real/seed data — takes a few seconds
                              # (optional datasets in data/raw are skipped if the files are missing)
```

You only need to do this once (or again if you ever delete `backend/freight_forecast.db`).

## 1. Starting the backend

Open a Terminal window, then run these commands one at a time (press Enter
after each):

```bash
cd /Users/swayampanchal/Desktop/SAIL/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

You'll see lines ending in something like `Application startup complete.` —
that means it's running. **Leave this terminal window open**; closing it stops
the backend.

To check it's actually working, open a web browser and go to:

- **http://localhost:8000** — you should see a small block of text (JSON) naming the service.
- **http://localhost:8000/docs** — this is the interactive API documentation.
  Every backend feature we build shows up here automatically, and you can click
  "Try it out" on any endpoint to test it directly, no coding needed.
- **http://localhost:8000/api/v1/health** — shows whether the database and
  cache are connected. `"database":"up"` is what you want to see.

## 2. Starting the frontend

Open a **second** Terminal window (don't close the first one), then run:

```bash
cd /Users/swayampanchal/Desktop/SAIL/frontend
npm run dev
```

You'll see a line like `Local: http://localhost:5173/`. Open that address in
your browser — that's the actual dashboard. It automatically talks to the
backend you started in step 1, so make sure that's still running.

If you see a red/orange badge saying "Backend unreachable" in the top-right of
the Overview page, it means the backend (step 1) isn't running or was closed —
go back and check that terminal window.

## 2b. Signing in and what to click

Open **http://localhost:5173**. You'll land on the public home page.

1. Click **Get started**, choose the role closest to yours (Procurement Manager, Chartering Analyst, Port & Logistics Officer or Finance & Treasury), fill in name, email and a password of at least 8 characters, and create the account. Any email works. The password needs at least 8 characters with a letter and a number (the form shows a strength meter). Five wrong attempts lock that email out for ten minutes. Accounts live only in your local database.
2. You're signed in automatically and land on the dashboard. The **Overview** greets you by name and shows three quick actions for your role; the small dots in the sidebar mark the tools suggested for that role. Every role can still open every tool.
3. The sidebar groups the tools into Decide, Analyse and Operate. Try, in this order: **Ask the Desk** (click a suggestion, or type a question about freight, ports, origins or risk), **Markets** (streaming price chart, click any row in the regional boards to chart it), **Freight Forecast** (click *Run ensemble* and wait about 12 seconds), **Chartering Recommendation**, **Port Map** (click a port in the list), **Scenario Sandbox**, then the newer tools: **Voyage Economics**, **Port Signals**, **Fixture Ledger** (load the sample entries), **Alerts** (create a rule, press Check now), **Model Monitor** and **Data Explorer**.
4. **Account** (name, role, change password) and **Sign out** are at the bottom of the sidebar. Next time use **Sign in** with the same email and password.

Things to know:
- The Port Map loads its map tiles from OpenStreetMap, so it needs an internet connection.
- Prices are replayed real history, not a live feed; each chart says so.

## 3. Stopping everything

In each terminal window, press `Ctrl + C` to stop the server. It's safe to
close the terminal windows after that.

## 4. Where things live

| What | Where |
|---|---|
| Backend code | `backend/app/` |
| Database models (what data looks like) | `backend/app/models/` |
| Database migration history | `backend/alembic/versions/` |
| Frontend pages | `frontend/src/pages/` |
| Local database file (SQLite, dev only) | `backend/freight_forecast.db` — safe to delete, it'll be recreated by running `alembic upgrade head` again |
| Project settings/secrets | `.env` in the project root (never share this file or commit it to GitHub — it's already excluded via `.gitignore`) |
| What's been built so far | `SECTIONS.md` |
| Feature list | `FEATURES.md` |

## 5. Common issues

- **"command not found: uvicorn" or similar** — you forgot the `source .venv/bin/activate` line, or ran it from the wrong folder. Re-run the three commands from step 1 in order.
- **Port already in use** — something is already running on that port (maybe you started it twice). Either close the other terminal running it, or ask to run it on a different port.
- **Changes to the code don't show up** — the backend auto-reloads (`--reload` flag) and the frontend auto-reloads too, but if something looks stuck, stop it (`Ctrl+C`) and start it again.

## 6. Deployment (when we get there)

We're planning to deploy the frontend to **Vercel** and the backend to
**Render's free tier**. When that's set up, you won't need to run anything
locally to show it to someone — you'll just share a link. I'll walk you through
the exact clicking-through-the-website steps for both when we get to that
section, since neither needs command-line work beyond connecting your GitHub
account.

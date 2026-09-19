# Deploying: Neon (database) + Render (API) + Vercel (website)

All three have free tiers and no Docker. Do the steps in this order. You create the accounts and paste the
secrets yourself; nobody else needs your passwords or connection strings.

## Before you start

**Free-tier limits.** Render's free web service has 512 MB of memory and sleeps after about 15 minutes idle
(the first request after a sleep takes about 30-60 seconds). The heaviest model call (the ARIMA + XGBoost
ensemble) may be slow or run out of memory there. If that happens, the rest of the app still works.

**Data licences.** Only public-domain data is loaded: USDA ocean rates, US BLS and EIA series, Federal Reserve rates, NOAA
cyclone tracks and Ministry of Ports figures, all downloaded free with no account or key (see LICENCES.md). Ship availability
is uploaded by your own users. Keep `LIVE_SHIP_FEED` unset: that feed was removed. Refresh the market series any time with
`python scripts/ingest_latest.py` and `python scripts/ingest_usda_ocean.py`.

## Step 1: Neon (database)

1. Go to neon.tech and sign up. Create a project (any name, the region closest to you).
2. On the project dashboard click **Connect** and copy the connection string. It looks like
   `postgresql://user:password@ep-xxxx.aws.neon.tech/neondb?sslmode=require`. Keep it private.

## Step 2: Load the data into Neon (from your laptop, once)

The raw datasets are not in GitHub, so the database has to be filled from your machine. In a terminal:

```bash
cd /Users/swayampanchal/Desktop/SAIL/backend
source .venv/bin/activate
export DATABASE_URL='paste-the-neon-connection-string-here'
alembic upgrade head            # creates the tables in Neon
cd ../scripts
python run_all.py               # loads all the data into Neon (a few minutes over the internet)
python seed_demo_users.py       # the six demo accounts and sample fixtures (skip for a real launch)
```

Watch for red error text. The tables were built and tested on SQLite; this is their first run on Postgres, so if
something fails, copy the message to me and I will fix it.

## Step 3: Render (API)

1. Push the code to GitHub (ask me to commit and push).
2. On render.com sign up with GitHub. Click **New +**, then **Blueprint**, and pick this repository. Render reads
   `render.yaml` and proposes the `freight-desk-api` service.
3. It will ask for two values:
   - `DATABASE_URL`: paste the Neon string from Step 1.
   - `CORS_ORIGINS`: for now type `["http://localhost:5173"]`. You will change it in Step 5.
   `JWT_SECRET_KEY` is generated for you.
4. Click **Apply**. Wait for the build (a few minutes). When it says **Live**, open
   `https://YOUR-SERVICE.onrender.com/api/v1/health`. You should see `"database":"up"`.

## Step 4: Vercel (website)

1. On vercel.com sign up with GitHub. **Add New > Project**, import this repository.
2. Set **Root Directory** to `frontend`. The framework is detected as Vite.
3. Under **Environment Variables** add `VITE_API_BASE_URL` = `https://YOUR-SERVICE.onrender.com/api/v1`.
4. Click **Deploy**. Note the address it gives you, e.g. `https://freight-desk.vercel.app`.

## Step 5: Let the website talk to the API

In Render, open the service, then **Environment**, and change `CORS_ORIGINS` to
`["https://freight-desk.vercel.app"]` (your real Vercel address, in that exact JSON list format). Save; Render
redeploys. Then open the Vercel address, register an account and click around.

## Demo accounts on the live site

The sign-in page offers one-click demo accounts (one per role) when `ALLOW_DEMO_LOGIN` is `true` (the default). They hold
sample data only, but the demo Administrator can see the audit log and user list, so for a real launch set
`ALLOW_DEMO_LOGIN` to `false` in Render's Environment tab and assign roles to real users with
`python scripts/set_role.py you@example.com admin` (run against the Neon database as in Step 2). Model training
(`scripts/train_current.py`, `train_current_dl.py`) is done on a laptop; the deployed API only reads the small result files already in the repository.

## If something goes wrong

- **Website loads but every panel says the backend is unreachable:** `VITE_API_BASE_URL` is wrong, or
  `CORS_ORIGINS` does not match the website's exact address (including `https://`, no trailing slash).
- **Render build fails on a package:** send me the log. Version pins are in `backend/requirements.txt`.
- **First load is very slow:** the free service was asleep. Wait a minute and retry.
- **The API refuses to start:** with `ENVIRONMENT=production` it demands a real `JWT_SECRET_KEY` (32+ characters).
  The blueprint generates one, so this only happens if you removed it.

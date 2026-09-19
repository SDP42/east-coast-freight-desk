# Deploying: Neon (database) + Render (API) + Vercel (website)

All three have free tiers and no Docker. Do the steps in this order. You create the accounts and paste the
secrets yourself; nobody else needs your passwords or connection strings.

## Before you start: two things to decide

1. **The Baltic Dry Index data.** The daily BDI series came from an Investing.com export via a public GitHub
   mirror with no licence. It is fine for private research, but loading it into a hosted database and serving it
   from a public API redistributes it. Options: (a) keep the hosted demo but accept that, (b) deploy without
   the BDI (the forecast pages will be empty), or (c) switch to a licensed source. This is your call; the code
   works either way.
2. **Free-tier limits.** Render's free web service has 512 MB of memory and sleeps after ~15 minutes idle
   (the first request after a sleep takes about 30-60 seconds). The heaviest model call (the ARIMA + XGBoost
   ensemble) may be slow or run out of memory there. If that happens, the rest of the app still works.

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

## If something goes wrong

- **Website loads but every panel says the backend is unreachable:** `VITE_API_BASE_URL` is wrong, or
  `CORS_ORIGINS` does not match the website's exact address (including `https://`, no trailing slash).
- **Render build fails on a package:** send me the log. Version pins are in `backend/requirements.txt`.
- **First load is very slow:** the free service was asleep. Wait a minute and retry.
- **The API refuses to start:** with `ENVIRONMENT=production` it demands a real `JWT_SECRET_KEY` (32+ characters).
  The blueprint generates one, so this only happens if you removed it.

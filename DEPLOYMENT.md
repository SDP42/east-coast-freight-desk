# Deployment guide: Neon (database) + Render (backend) + Vercel (frontend)

Written for someone who has never deployed before. Everything below is free, needs no credit card, and takes about 60 to 90 minutes the first time.
Follow the steps **in order**. Text in `code style` is exactly what to type or paste. Words in **bold** are buttons or field names on the website
(the sites redesign now and then, so a label may differ slightly; look for the closest match).

**What you will end up with**

```
 Reviewers' browser  ──►  Vercel  (the website, the React frontend)
                              │  calls
                              ▼
                          Render   (the backend API, Python/FastAPI)
                              │  reads and writes
                              ▼
                           Neon    (the Postgres database)
```

**Accounts to create (all free):** GitHub (you already have one), Neon, Render, Vercel. Sign up to the last three with **Continue with GitHub**: it is the
easiest and lets them see your repository.

**Two limits of the free plans you should know now**
- Render's free backend **falls asleep after 15 minutes without visitors**. The next visit takes up to about a minute to wake it. Step 9 shows a free way to keep it awake.
- Render's free backend has 512 MB of memory. This app peaked around 315 MB in testing, so it fits, but one page (the ensemble forecast) is heavy. If it ever crashes with "out of memory", upgrade that one service to the **Starter** plan (about US$7 a month).

---

## Step 0. Get the latest code onto GitHub

Render and Vercel deploy from GitHub, so GitHub must have the latest code. Ask for the latest commit to be pushed (the project owner does `git push`). Then open
https://github.com/SDP42/east-coast-freight-desk and check the top of the page shows the newest commit message.

## Step 1. Make a clean copy of the project on your computer

The Desktop folder can be slow with iCloud, so use a fresh copy in your home folder. Open the **Terminal** app and paste these lines one at a time, pressing Return after each:

```bash
cd ~
git clone https://github.com/SDP42/east-coast-freight-desk freight-desk
cd freight-desk
python3 --version
```

The last command should print `Python 3.11` or `3.12` (or higher). If it says the command is not found, install Python from https://www.python.org/downloads/ and try again.
If `git` is not found, macOS will offer to install the developer tools: accept, wait, then repeat.

Create an isolated Python environment and install what the backend needs (this takes a few minutes):

```bash
cd ~/freight-desk/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You will see `(.venv)` at the start of the prompt. **Keep this Terminal window open**; you will use it again in Step 3.

## Step 2. Create the database on Neon

1. Go to https://neon.tech and click **Sign up**, then **Continue with GitHub**.
2. If asked to create a project, or after clicking **New Project**, fill in:
   - **Project name:** `freight-desk`
   - **Postgres version:** `16` (or the default)
   - **Cloud provider / Region:** the one closest to India, for example **AWS, Asia Pacific (Singapore)**
3. Click **Create project**.
4. On the project page click **Connect** (top right). A box shows a **connection string**.
   - Make sure the **Pooled connection** switch is **off** (we want the direct connection).
   - The database should be `neondb`, the role `neondb_owner`.
   - Click **Copy snippet** / the copy icon.
5. The string looks like this (yours has different letters):
   `postgresql://neondb_owner:AbCdEf123@ep-cool-name-123456.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`
6. **Paste it into a text file for now and keep it private.** It contains your database password: never post it in a chat, screenshot or GitHub.
   Call it **the Neon string** below.

## Step 3. Put the tables and data into Neon (from your computer)

Go back to the Terminal window from Step 1 (with `(.venv)` showing). Tell the project where the database is. Replace the part inside the quotes with **your** Neon string:

```bash
export DATABASE_URL="PASTE-YOUR-NEON-STRING-HERE"
```

Now run these three commands one at a time. The first builds the empty tables, the second downloads the free public data and fills them (about 3 to 6 minutes; it downloads a 28 MB file from NOAA), the third adds the demo accounts:

```bash
cd ~/freight-desk/backend
alembic upgrade head
cd ~/freight-desk/scripts
python run_all.py
python seed_demo_users.py
```

What you should see: `alembic` prints several `Running upgrade ...` lines; `run_all.py` prints a section for each step and ends without an error; the last command prints
`Demo accounts ready: admin@demo.example.com, ...`.

**Check that the data is really there** (still in the same Terminal):

```bash
cd ~/freight-desk/backend
python - <<'PY'
from sqlalchemy import text
from app.db.session import SessionLocal
db = SessionLocal()
print("database:", db.bind.dialect.name)
for r in db.execute(text("select index_name, count(*) from freight_rates group by 1 order by 1")): print(r)
print("ports:", db.execute(text("select count(*) from ports")).scalar(), "| users:", db.execute(text("select count(*) from users")).scalar())
PY
```

You should see `database: postgresql`, nine series names (`AUD`, `BRENT`, `COAL_PPI`, `DEEPSEA_PPI`, `DXY`, `INR`, `OCEAN_GULF_JAPAN`, `OCEAN_PNW_JAPAN`, `ZAR`), `ports: 12` and `users: 6`.

Now make a secret key for the backend and copy it somewhere safe (it is a long random string):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Call it **the secret key**.

## Step 4. Deploy the backend on Render

1. Go to https://render.com, click **Get Started**, then **GitHub**, and allow access.
2. Click **New +** (top right) and choose **Web Service**.
3. Choose **Build and deploy from a Git repository**, click **Next**, find **east-coast-freight-desk** and click **Connect**.
   (If it is not listed, click **Configure account** and give Render access to that repository.)
4. Fill in the form **exactly** like this:

| Field | Value |
|---|---|
| Name | `freight-desk-api` |
| Region | Singapore (closest to India) |
| Branch | `main` |
| Root Directory | `backend` |
| Runtime / Language | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | **Free** |

5. Scroll to **Environment Variables** and click **Add Environment Variable** for each row (Key on the left, Value on the right):

| Key | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.7` |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | **the Neon string** from Step 2 |
| `JWT_SECRET_KEY` | **the secret key** from Step 3 |
| `CORS_ORIGINS` | `["https://placeholder.vercel.app"]` (we fix this in Step 6) |
| `PREWARM` | `false` |
| `ALLOW_DEMO_LOGIN` | `true` |
| `SHOW_SIMULATED_FEEDS` | `false` |
| `LIVE_SHIP_FEED` | `false` |

6. Open **Advanced** and set **Health Check Path** to `/api/v1/healthz` (a light check that never waits on the database; the free server is slow, and a heavier check can time out and cause restarts).
7. Click **Create Web Service**. Render now builds it: watch the **Logs** tab. The first build takes about 5 to 10 minutes (it installs the scientific libraries).
8. It is finished when the top of the page shows a green **Live** and the log ends with `Application startup complete`.
9. At the top you will see your backend address, like `https://freight-desk-api.onrender.com`. **Copy it.** Open this in a browser tab to test:
   `https://freight-desk-api.onrender.com/api/v1/health`
   You should see something like `{"status":"ok","database":"up",...}`. (If the address differs from mine, Render added letters; use exactly what it shows.)

If the build fails, open the log, copy the last 20 lines and see **Troubleshooting** at the end.

## Step 5. Deploy the frontend on Vercel

1. Go to https://vercel.com, click **Sign Up**, then **Continue with GitHub**.
2. Click **Add New...** then **Project**. Next to **east-coast-freight-desk** click **Import**.
3. On the **Configure Project** screen:

| Field | Value |
|---|---|
| Project Name | `east-coast-freight-desk` (anything is fine) |
| Framework Preset | **Vite** |
| Root Directory | click **Edit**, choose `frontend`, click **Continue** |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Install Command | `npm install` |

4. Open **Environment Variables** and add **one** variable:

| Name | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://freight-desk-api.onrender.com/api/v1` |

   Use **your** Render address from Step 4, then add `/api/v1`. There is **no** slash at the very end.
5. Click **Deploy**. It takes 1 to 3 minutes. When you see the confetti, click **Continue to Dashboard**, then **Visit**.
6. Your website address is at the top, like `https://east-coast-freight-desk.vercel.app`. **Copy it.**

At this point the site opens but sign-in will fail with a network error: the backend does not yet trust the website's address. That is Step 6.

## Step 6. Tell the backend which website may call it (CORS)

1. In Render open your `freight-desk-api` service, then **Environment** (left menu).
2. Edit **CORS_ORIGINS** and set it to your Vercel address in this exact format (square brackets, double quotes, no slash at the end):

   `["https://east-coast-freight-desk.vercel.app"]`

   If you later add a custom domain, list both: `["https://east-coast-freight-desk.vercel.app","https://yourdomain.com"]`
3. Click **Save changes**. Render redeploys automatically (about 2 minutes). Wait for **Live** again.

## Step 7. Test everything

1. Open your Vercel address. The landing page should show the aurora background, the four map tabs and the statistics.
2. Click **Try the live demo**. If the first attempt takes long, that is the free backend waking up: wait up to a minute and try again.
3. Click a demo persona card (for example **Finance & Treasury**). You should land on the dashboard.
4. Open these pages and check each loads real content: **The Verdict**, **Urgent Fixture Desk**, **What-If Studio**, **Open Tonnage** (press **Load a sample list**), **Freight Forecast**, **Model Lab**, **Port Map**.
5. Sign out, sign in as **Port Officer, Haldia**, open **Ask the Desk** and ask `How risky is Australia to Paradip?`. It should be refused (that port is not his).

## Step 8. Share it

Send reviewers the Vercel address. Tell them the first visit can take up to a minute while the free backend wakes, and that the demo accounts hold sample data only.

## Step 9 (optional, recommended). Stop the backend falling asleep

1. Go to https://uptimerobot.com and sign up (free).
2. Click **Add New Monitor**. Monitor Type: **HTTP(s)**. Friendly Name: `freight-desk-api`. URL: `https://freight-desk-api.onrender.com/api/v1/health` (your address). Monitoring Interval: **5 minutes**. Click **Create Monitor**.

## Step 10. When you are ready for real users (after the demo)

Do this against the database you will keep, not one you still demo from.

1. In the Terminal from Step 3 (with `DATABASE_URL` still exported), remove all demo and sample data. First a dry run that only lists what would go:
   ```bash
   cd ~/freight-desk/scripts && python prepare_production.py
   ```
   then, if the list looks right: `python prepare_production.py --apply`
2. In Render, **Environment**, change `ALLOW_DEMO_LOGIN` to `false` and save.
3. Register your own account on the website. It starts as **Viewer**. Make yourself the administrator (put your email in the quotes):
   ```bash
   cd ~/freight-desk/scripts && python set_role.py you@example.com admin
   ```
4. Sign out and in again. **Access & Audit** now lets you give each colleague a role and assign ports to port officers.

## Refreshing the data later

The market series come from free public sources. To update them, in a Terminal with `DATABASE_URL` set:
`cd ~/freight-desk/scripts && python ingest_latest.py && python ingest_usda_ocean.py`. USDA and the labour-statistics series update monthly.

---

## Troubleshooting

| What you see | Cause and fix |
|---|---|
| Website loads but sign-in says network error / red text in the browser console mentions CORS | `CORS_ORIGINS` in Render does not exactly match the Vercel address. Fix Step 6: brackets, double quotes, `https://`, no trailing slash. |
| Sign-in spins for a minute, then works | The free backend was asleep. Normal. Use Step 9. |
| Render build fails on `pip install` | Check `PYTHON_VERSION` is `3.12.7` and Root Directory is `backend`. |
| Render log says `JWT_SECRET_KEY must be set` | The secret key is missing or under 32 characters: set it (Step 3). |
| Render log says `could not connect to server` or `password authentication failed` | `DATABASE_URL` is wrong. Re-copy the Neon string (direct connection, `sslmode=require`), no extra spaces or quotes. |
| Render log says `relation ... does not exist` | Step 3 was skipped or ran against the wrong database. Repeat Step 3 with the same Neon string. |
| Render shows `Out of memory` and restarts | The ensemble forecast is heavy. Upgrade the service to **Starter**, or avoid pressing "Run ensemble" repeatedly. |
| Render **Events** shows "HTTP health check failed (timed out after 5 seconds)" | The free server was busy with a heavy request. Set **Health Check Path** to `/api/v1/healthz` (Settings, then Health Checks). |
| Pages show "Could not load ... is the backend running?" | Open your Render address plus `/api/v1/health`. If that fails the backend is down or asleep; check the Render **Logs**. |
| Port Map is blank grey | Vercel did not deploy `frontend/public/geo/`. Check the folder exists in GitHub and redeploy. |
| Every page reloads to a 404 on Vercel | `frontend/vercel.json` must be in GitHub (it rewrites every path to the app). Redeploy. |
| Neon is slow on the first query after a quiet period | Neon pauses idle databases. The first request wakes it (a second or two). Normal. |
| You changed a Vercel environment variable and nothing changed | Vercel bakes them in at build time: **Deployments** then **Redeploy**. |

## Keep these secret, and keep these safe

- **Never commit** the Neon string, the secret key or a `.env` file to GitHub. They live only in Render's Environment page and your private notes.
- The demo accounts sign in with one click and hold **sample data only**. They are the reason to run Step 10 before real users.
- Redeploys: pushing to GitHub redeploys both Render and Vercel automatically.

## Data and licences

Only public-domain data is loaded (see LICENCES.md), downloaded free with no key. Ship availability is uploaded by your own users. No simulated data is shown unless `SHOW_SIMULATED_FEEDS` is set.

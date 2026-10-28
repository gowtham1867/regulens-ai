# ReguLens AI — Vercel Deployment Guide

This project is configured as a full-stack monorepo ready for immediate deployment on **Vercel** with a **React + Vite Frontend** and a **FastAPI Python Serverless Backend**.

---

## Architecture on Vercel

```
ReguLens AI /
├── api/
│   ├── index.py           <-- FastAPI Serverless Entrypoint for Vercel
│   └── requirements.txt   <-- Python dependencies
├── backend/               <-- FastAPI Application & Services
├── frontend/              <-- React + Vite + TailwindCSS UI
├── vercel.json            <-- Monorepo build & rewrite rules
├── package.json           <-- Root build script orchestrator
└── .vercelignore          <-- Excludes unnecessary files & caches
```

- **Frontend**: Vite statically builds the React SPA to `frontend/dist`.
- **Backend API**: Handled serverlessly via `api/index.py` using Vercel's Python runtime.
- **Routing**:
  - `/api/*` requests route directly to the FastAPI serverless function.
  - All other routes (`/login`, `/officer/login`, `/institution/register`, `/applications/*`) rewrite to `/index.html` for client-side routing.
- **Database**:
  - **Zero-config (Default)**: Automatically runs SQLite using the seeded `regulens.db` initialized into writable `/tmp`.
  - **Production Option**: Set `DATABASE_URL` in your Vercel Environment Variables to point to any remote PostgreSQL database (e.g. Neon, Supabase, Vercel Postgres).

---

## Method 1: Deploy via GitHub (Recommended)

1. **Commit and push this repository to GitHub**:
   ```bash
   git add .
   git commit -m "Configure full-stack ReguLens AI for Vercel deployment"
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git branch -M main
   git push -u origin main
   ```

2. **Import to Vercel**:
   - Go to [vercel.com/new](https://vercel.com/new).
   - Select your repository and click **Import**.
   - Leave the root directory as `./` (the root).
   - Vercel automatically detects `vercel.json`, `package.json`, and `api/index.py`.

3. **Deploy**:
   - Click **Deploy**.
   - Vercel will install frontend dependencies, build Vite, install Python packages, and deploy your live URL.

---

## Method 2: Deploy via Vercel CLI

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Authenticate with Vercel**:
   ```bash
   vercel login
   ```

3. **Deploy from project root**:
   ```bash
   # Deploy preview
   vercel

   # Deploy directly to production
   vercel --prod
   ```

---

## Environment Variables (Optional)

Configure these in the Vercel Dashboard under **Project Settings > Environment Variables** if desired:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | *(Built-in development key)* | Cryptographic key for signing JWT tokens |
| `DATABASE_URL` | `sqlite:////tmp/regulens.db` | Remote PostgreSQL connection string (optional) |
| `REGULATORY_ACADEMIC_YEAR` | `2025-2026` | Current regulatory scrutinization cycle |

---

## Default Test Accounts

- **Institution Account**:
  - Email: `apex@institution.edu.in`
  - Password: `Institute@123`
  - Portal: `/login` (Default landing page)

- **AICTE Scrutiny Officer**:
  - Email: `officer@aicte-india.org`
  - Password: `Officer@123`
  - Portal: `/officer/login`

- **Institution Registration**:
  - Portal: `/institution/register`


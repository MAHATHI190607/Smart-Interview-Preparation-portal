# Smart Interview Preparation Portal

A beginner-friendly Flask web application for interview practice, resume screening, quiz history and job application tracking.

## Features
- Register and log in securely (passwords are hashed).
- Dashboard with quiz statistics and application summary.
- Resume PDF upload and automated screening suggestions.
- Optional Gemini AI feedback when `GEMINI_API_KEY` is configured.
- Technical, HR and aptitude quizzes with saved scores.
- Application tracker with stages: Saved, Applied, Interview, Offer and Rejected.
- Profile page and responsive layout.

> Resume screening without an API key uses transparent keyword-based analysis. With a Gemini API key, the app also requests AI-generated feedback. Suggestions are guidance only, not a hiring decision.

## Run on your computer (Windows)

1. Install Python 3.10 or newer from https://www.python.org/downloads/. During installation, tick **Add Python to PATH**.
2. Extract this ZIP file.
3. Open the extracted `Smart-Interview-Preparation-Portal` folder.
4. In VS Code, choose **File → Open Folder** and select this folder.
5. Open **Terminal → New Terminal**.
6. Run these commands one at a time:

```bash
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```

7. Hold `Ctrl` and click the address shown in the terminal, or open `http://127.0.0.1:5000` in Chrome.
8. Register a new account and explore the portal.

If `py` does not work, try `python` instead.

## Optional: enable Gemini AI feedback

1. Create an API key in Google AI Studio: https://aistudio.google.com/apikey
2. Set an environment variable named `GEMINI_API_KEY` to your key before starting the app.
3. Never paste your key into `app.py`, HTML, GitHub, or a public repository.

Windows PowerShell (current terminal only):
```powershell
$env:GEMINI_API_KEY="YOUR_KEY_HERE"
py app.py
```

Without a key, resume screening still works using the built-in keyword analysis.

## Publish the code on GitHub

1. Sign in at https://github.com and click **New repository**.
2. Name it `Smart-Interview-Preparation-Portal`.
3. Choose **Public** (if you want others to see it). Do not upload passwords, API keys, `.env`, or your private database.
4. Create the repository.
5. In VS Code, open the extracted project folder.
6. Open **Source Control** (branch icon on the left), click **Initialize Repository**.
7. Enter a commit message such as `First version of Smart Interview Portal`, then click **Commit**.
8. Click **Publish Branch** / **Publish to GitHub**, sign in if asked, and select the repository you created.

Alternative terminal commands:
```bash
git init
git add .
git commit -m "Initial Smart Interview Preparation Portal"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/Smart-Interview-Preparation-Portal.git
git push -u origin main
```
Replace `YOUR-USERNAME` with your GitHub username. If you already connected this folder to a GitHub repository, do not add a second remote; use `git remote -v` to check.

## Publish the live website with Render

GitHub stores your project code. Because this project uses Python/Flask, GitHub Pages alone cannot run the backend. Use Render:

1. Push your project to GitHub first.
2. Visit https://render.com and sign up / log in.
3. Choose **New + → Web Service**.
4. Connect GitHub and select `Smart-Interview-Preparation-Portal`.
5. Render detects `render.yaml`. If asked, use:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
6. Deploy. Render provides a public `onrender.com` website address.
7. For AI feedback, add `GEMINI_API_KEY` in the Render service's Environment settings. Do not put it in GitHub.

### Important hosting note
The included SQLite database and uploaded files are suitable for learning and local demonstrations. Free hosting filesystems may be temporary and may reset during redeploys. For a long-term public deployment, use managed PostgreSQL and persistent file/object storage. Do not upload real personal resumes while using a demo deployment.

## Project pages
- `/` Landing page
- `/register` and `/login`
- `/dashboard`
- `/resume` Resume screening
- `/practice` Quiz categories
- `/tracker` Job application pipeline
- `/profile`

## Troubleshooting
- **Python not recognized:** reinstall Python and tick Add Python to PATH, then restart VS Code.
- **Module not found:** activate `.venv` and run `py -m pip install -r requirements.txt`.
- **Port already in use:** close the older terminal running the app, or change the port in `app.py`.
- **PDF not readable:** upload a text-based PDF, not a scanned image.

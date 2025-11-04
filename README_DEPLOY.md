# Quick Deploy Guide (Railway / Render)

## Railway
1) Create new project -> Deploy from GitHub -> select this repo.
2) Railway auto-detects `Procfile`.
3) After deploy, copy the public URL, verify `/health` and `/docs`.

## Render
1) New -> Web Service -> connect GitHub repository.
2) Runtime: Python. Build command (auto): `pip install -r requirements.txt`.
3) Start command: `uvicorn main:app --host 0.0.0.0 --port 10000`.
4) Set PORT=10000 if not auto.
5) Open public URL, verify `/health` and `/docs`.

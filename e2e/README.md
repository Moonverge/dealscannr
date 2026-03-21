# DealScannr E2E

## API tests (pytest)

- **Requires MongoDB** on `DATABASE_URL` (default test DB: `mongodb://127.0.0.1:5300/dealscannr_pytest`). Start with `docker compose up -d mongodb`.
- Uses **in-process FastAPI `TestClient`** (no real HTTP). External HTTP is not hit; connectors and Groq are **monkeypatched** in fixtures.
- Install deps into the API venv or a dedicated venv:

```bash
cd e2e
# Use python -m pip if `pip` is not on your PATH (common on macOS):
python3 -m pip install -r requirements.txt
# Or reuse the API venv:
# ../packages/api/.venv/bin/python -m pip install -r requirements.txt

PYTHONPATH=../packages:../packages/api python3 -m pytest api/ -v
```

Override DB: `export TEST_DATABASE_URL=mongodb://...`

## Web tests (Playwright)

```bash
cd e2e/web
npm install
npx playwright install
# Start Vite on 5100 separately, then:
npx playwright test
```

`PLAYWRIGHT_BASE_URL` defaults to `http://localhost:5100`. Many tests **mock** `/api/*` via `page.route`.

# Tech Context: Technologies & Setup

## Technologies Used
- Python 3.8+
- FastAPI (web dashboard & API)
- Rich (CLI interface)
- psutil (system metrics)
- OpenAI GPT API (AI analysis)
- Windows APIs (service/process monitoring)
- asyncio (asynchronous operations)
- aiosqlite (async SQLite for persistence)

## Development Setup
- Clone repo and install dependencies: `pip install -r requirements.txt`
- Set environment variables in `.env` (e.g., `OPENAI_API_KEY`)
- Run with `python web_interface.py` (web) or `python cli_interface.py` (CLI)
- Configurable via `config.py` (thresholds, agent intervals, GPT settings, etc.)
- Database persistence enabled by default (see config.py: persistence_enabled, db_path)

## Technical Constraints
- Full service/process monitoring only on Windows 10/11
- Requires admin rights for some remediation actions
- GPT API key required for full AI functionality (fallback to rules otherwise)
- Disk space and resource usage should be monitored for production

## Dependencies
- See `requirements.txt` for full list
- Key packages: fastapi, uvicorn, psutil, rich, openai, python-dotenv, aiosqlite
- aiosqlite (for async DB access) 
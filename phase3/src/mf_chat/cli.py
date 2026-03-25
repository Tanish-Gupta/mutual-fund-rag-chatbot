from __future__ import annotations

from mf_ingest.env_bootstrap import load_project_dotenv


def main() -> None:
    load_project_dotenv()
    import uvicorn

    uvicorn.run(
        "mf_chat.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()

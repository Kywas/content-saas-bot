from pathlib import Path
import sys


def main() -> None:
    env_path = Path("/opt/content-saas-bot/.env")
    if not env_path.is_file():
        print("Missing /opt/content-saas-bot/.env", file=sys.stderr)
        raise SystemExit(1)

    token = ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("BOT_TOKEN="):
            token = stripped.split("=", 1)[1].strip().strip('"').strip("'")
            break

    if not token:
        print("BOT_TOKEN is missing or empty in .env", file=sys.stderr)
        raise SystemExit(1)

    print("OK: .env contains BOT_TOKEN")


if __name__ == "__main__":
    main()

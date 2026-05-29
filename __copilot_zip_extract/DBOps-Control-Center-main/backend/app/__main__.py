import argparse

from .reset_demo import reset_demo_data
from .seed_demo import seed_demo_data


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app",
        description="DBOps backend utility commands",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="seed-demo",
        choices=["seed-demo", "reset-demo"],
        help="Command to run (default: seed-demo)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required for reset-demo (safety confirmation)",
    )
    args = parser.parse_args()

    if args.command == "seed-demo":
        seed_demo_data()
        return

    if args.command == "reset-demo":
        if not args.yes:
            raise SystemExit("reset-demo requires --yes (deletes incidents, schedules, report logs, onboarding markers)")
        counts = reset_demo_data()
        print("Reset complete:", counts)


if __name__ == "__main__":
    main()

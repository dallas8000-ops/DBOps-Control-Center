import argparse

from .demo_public import demo_public_mode_enabled, lock_public_demo, print_lock_summary
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
        choices=["seed-demo", "reset-demo", "lock-public-demo"],
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

    if args.command == "lock-public-demo":
        results = lock_public_demo()
        print_lock_summary(results)
        if not demo_public_mode_enabled():
            print("Tip: set DEMO_PUBLIC_MODE=1 on Railway so /health advertises the locked demo.")
        return

    if args.command == "reset-demo":
        if not args.yes:
            raise SystemExit("reset-demo requires --yes (deletes incidents, schedules, report logs, onboarding markers)")
        counts = reset_demo_data()
        print("Reset complete:", counts)


if __name__ == "__main__":
    main()

import argparse

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
        choices=["seed-demo"],
        help="Command to run (default: seed-demo)",
    )
    args = parser.parse_args()

    if args.command == "seed-demo":
        seed_demo_data()


if __name__ == "__main__":
    main()
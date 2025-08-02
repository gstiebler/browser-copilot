import os


WAIT_FOR_INPUT = os.getenv("WAIT_FOR_INPUT", "false").lower() == "true"


def wait_for_input():
    if WAIT_FOR_INPUT:
        input("Press Enter to continue...")

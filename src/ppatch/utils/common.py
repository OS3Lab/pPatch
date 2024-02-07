import subprocess


def clean_repo():
    subprocess.run(["git", "clean", "-df"])
    subprocess.run(["git", "reset", "--hard"])

# run.py – place in /home/dante/Desktop/Apps/Autonomous Agent/

import os
import subprocess
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
requirements_file = os.path.join(project_root, "requirements.txt")
venv_candidates = [
    os.path.join(project_root, "venv", "bin", "python"),
    os.path.join(project_root, ".venv", "bin", "python"),
]
venv_python = next((path for path in venv_candidates if os.path.exists(path)), venv_candidates[-1])


def ensure_project_venv() -> None:
    """Create a project venv if none exists yet."""
    if os.path.exists(venv_python):
        return

    print("Creating project virtual environment...", flush=True)
    subprocess.run([sys.executable, "-m", "venv", ".venv"], cwd=project_root, check=True)


def is_running_in_project_venv() -> bool:
    """Check if we're running inside the project virtual environment."""
    # Check if VIRTUAL_ENV is set to our project venv
    venv_env = os.getenv("VIRTUAL_ENV", "")
    if venv_env:
        return os.path.realpath(venv_env) in [os.path.realpath(c.replace("/bin/python", "")) for c in venv_candidates]
    
    # Fallback: try to import a project-specific package
    try:
        import strands  # noqa: F401
        return True
    except ModuleNotFoundError:
        return False


def ensure_dependencies() -> None:
    """Install dependencies into the project virtual environment."""
    if not os.path.exists(venv_python):
        return

    if os.path.exists(requirements_file):
        print("Installing project dependencies in the project virtual environment...", flush=True)
        subprocess.run([venv_python, "-m", "pip", "install", "-r", requirements_file], cwd=project_root, check=False)


if __name__ == "__main__":
    ensure_project_venv()

    if not is_running_in_project_venv():
        ensure_dependencies()
        os.execv(venv_python, [venv_python, __file__] + sys.argv[1:])

    sys.path.insert(0, project_root)
    from src.main import run_cycle

    run_cycle()
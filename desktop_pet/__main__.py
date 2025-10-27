try:
    from .app import run
except ImportError:  # pragma: no cover - runtime fallback for PyInstaller entry point
    from desktop_pet.app import run

if __name__ == "__main__":
    run()

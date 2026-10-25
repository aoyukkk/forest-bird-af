import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / 'src'))
"""Run the password-protected annotation gateway (HTTPS tunnel managed separately)."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from forest_bird_annotator.remote import main

if __name__ == '__main__':
    main()

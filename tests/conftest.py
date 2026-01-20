import sys
from pathlib import Path
SRC_PATH = Path(__file__).parent.parent / "src"
GOLD_PATH = SRC_PATH / "gold"
sys.path.insert(0, str(SRC_PATH))
sys.path.insert(0, str(GOLD_PATH))

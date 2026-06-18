"""구버전 호환용 파일입니다.

새 구조에서는 설정은 game/config.py, 카드 데이터는 game/card_data.py에 있습니다.
기존 코드가 `from constants import ...`를 사용하더라도 깨지지 않게 다시 내보냅니다.
"""

from game.config import *
from game.card_data import CARD_POOL

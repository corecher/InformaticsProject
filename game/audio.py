"""효과음 로딩과 재생을 담당하는 모듈입니다.

현재 규칙:
- Sound 폴더 안의 mp3 파일 하나를 카드 이동 공통 효과음으로 사용합니다.
- 카드를 뽑을 때, 버릴 때, 손에서 카드 내기 칸으로 이동할 때만 재생합니다.
- 카드가 확대되며 '발동!'되는 순간에는 소리를 재생하지 않습니다.
- 효과음 파일이 없거나 오디오 장치 문제가 있어도 게임이 꺼지지 않도록 방어합니다.
"""

from __future__ import annotations

import os
import pygame


class SoundManager:
    """Pygame mixer를 감싸는 안전한 효과음 관리자."""

    def __init__(self, project_root: str, volume: float = 0.55):
        self.project_root = project_root
        self.volume = volume
        self.card_move_sound = None
        self.load()

    def _candidate_folders(self):
        """사용자가 실제로 쓰는 Sound 폴더와 구버전 sounds 폴더를 모두 확인합니다."""
        return [
            os.path.join(self.project_root, "Sound"),
            os.path.join(self.project_root, "sounds"),
        ]

    def _find_mp3_file(self):
        """Sound 폴더에서 사용할 mp3 파일을 찾습니다.

        card.mp3를 가장 우선으로 사용하고, 없으면 폴더 안의 첫 번째 mp3를 사용합니다.
        """
        preferred_names = ["card.mp3", "sound.mp3", "effect.mp3", "draw.mp3", "discard.mp3"]
        for folder in self._candidate_folders():
            if not os.path.isdir(folder):
                continue

            for filename in preferred_names:
                path = os.path.join(folder, filename)
                if os.path.exists(path):
                    return path

            try:
                for filename in sorted(os.listdir(folder)):
                    if filename.lower().endswith(".mp3"):
                        return os.path.join(folder, filename)
            except Exception:
                pass
        return None

    def load(self):
        """효과음 파일을 로드합니다. 실패해도 예외를 밖으로 던지지 않습니다."""
        try:
            if not pygame.mixer.get_init():
                return
            path = self._find_mp3_file()
            if not path:
                return
            sound = pygame.mixer.Sound(path)
            sound.set_volume(self.volume)
            self.card_move_sound = sound
        except Exception as exc:
            print(f"[SFX] 효과음 로드 실패: {exc}")
            self.card_move_sound = None

    def play_card_move(self):
        """카드가 이동하는 순간 재생되는 공통 효과음입니다."""
        try:
            if self.card_move_sound:
                self.card_move_sound.play()
        except Exception:
            pass

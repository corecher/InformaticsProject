"""카드 객체와 카드 보관용 스택 클래스를 정의하는 모듈입니다.

Card는 카드 데이터, 이미지 로딩, 카드 렌더링을 담당합니다.
CardDummy/CardOnHand/TrashCard는 카드 묶음을 관리하는 아주 단순한 컨테이너입니다.
"""

import os
import pygame
from .config import DARK

DEFAULT_CARD_W = 150
DEFAULT_CARD_H = 240

# 카드 이름과 이미지 파일명이 아주 살짝 다른 카드들을 위한 매핑입니다.
# 게임 규칙/로그에 쓰이는 카드 이름은 그대로 두고, 이미지를 찾을 때만 아래 이름을 사용합니다.
IMAGE_FILE_ALIASES = {
    "9와 4분의3 승강장": "９와 ４분의３ 승강장",
    "윤규는 숫돌이": "윤규는 슛돌이",
}


def _encode_image_filename(name):
    """압축/OS 환경에 따라 한글 파일명이 #Uxxxx 형태로 보일 때를 위한 후보 이름을 만든다.

    예: "게임" -> "#Uac8c#Uc784"
    일반 한글 파일명과 #Uxxxx 파일명을 둘 다 후보로 넣기 때문에,
    Windows에서 정상 한글 파일명을 쓰는 경우와 압축 해제 후 인코딩된 경우를 모두 지원한다.
    """
    encoded = ""
    for ch in name:
        encoded += f"#U{ord(ch):04x}" if ord(ch) > 127 else ch
    return encoded


def _wrap_text_to_width(font, text, max_width, max_lines, ellipsis=True):
    """글자가 카드 밖으로 삐져나가지 않도록 픽셀 기준으로 줄바꿈한다."""
    if max_lines <= 0 or max_width <= 0:
        return []

    text = str(text)
    lines = []
    current = ""

    for ch in text:
        if ch == "\n":
            lines.append(current.rstrip())
            current = ""
            if len(lines) >= max_lines:
                break
            continue

        candidate = current + ch
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current.rstrip())
            current = ch.lstrip()
            if len(lines) >= max_lines:
                break

    if len(lines) < max_lines and current:
        lines.append(current.rstrip())

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    if ellipsis and len(lines) == max_lines:
        consumed = "".join(lines)
        original = text.replace("\n", "")
        if len(consumed) < len(original):
            last = lines[-1]
            suffix = "..."
            while last and font.size(last + suffix)[0] > max_width:
                last = last[:-1]
            lines[-1] = (last + suffix) if last else suffix

    return lines


class Card:
    def __init__(self, data):
        self.name = data["name"]
        self.card_type = data["type"]
        self.desc = data["desc"]

        if self.card_type == "행동":
            self.color = (135, 206, 250)
        elif self.card_type == "함정":
            self.color = (240, 128, 128)
        else:
            self.color = (255, 215, 0)

        self.rect = pygame.Rect(0, 0, DEFAULT_CARD_W, DEFAULT_CARD_H)
        self.dragging = False
        self.offset_x = 0
        self.offset_y = 0
        self.image = None
        self.instant_triggered = False

        project_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(project_dir)
        # 기본적으로는 images/카드이름.png 를 찾습니다.
        # 단, 일부 카드 이미지는 실제 파일명이 카드 표시 이름과 달라서
        # IMAGE_FILE_ALIASES에 등록된 이미지 이름도 후보에 넣습니다.
        image_names = []

        # 1순위: 카드 표시 이름과 같은 파일명
        image_names.append(self.name)

        # 2순위: 표시 이름과 실제 이미지 파일명이 다른 예외 케이스
        alias_name = IMAGE_FILE_ALIASES.get(self.name)
        if alias_name:
            image_names.append(alias_name)

        # 3순위: 압축/OS 환경에서 한글 파일명이 #Uxxxx 형태로 풀린 경우
        # 중복 후보는 제거해서 불필요한 exists 검사를 줄인다.
        expanded_image_names = []
        for image_name in image_names:
            expanded_image_names.append(image_name)
            expanded_image_names.append(_encode_image_filename(image_name))
        image_names = list(dict.fromkeys(expanded_image_names))

        img_candidates = []
        for image_name in image_names:
            img_candidates.extend([
                os.path.join(project_root, "images", f"{image_name}.png"),
                os.path.join(project_dir, "images", f"{image_name}.png"),
                os.path.join("images", f"{image_name}.png"),
            ])

        for img_path in img_candidates:
            if os.path.exists(img_path):
                try:
                    self.image = pygame.image.load(img_path).convert_alpha()
                    break
                except Exception as e:
                    print(f"[{self.name}] 이미지 로드 실패: {e}")

    def draw(self, screen, x, y):
        self.draw_at(screen, x, y, DEFAULT_CARD_W, DEFAULT_CARD_H, update_rect=True)

    def draw_image_only(self, screen, x, y, width=DEFAULT_CARD_W, height=DEFAULT_CARD_H, update_rect=True):
        self.draw_at(screen, x, y, width, height, update_rect=update_rect, image_only=True)

    def draw_at(self, screen, x, y, width=DEFAULT_CARD_W, height=DEFAULT_CARD_H, update_rect=True, image_only=False):
        """카드 렌더링 공용 함수.

        image_only=True이면 손패용으로 텍스트 없이 카드 이미지가 카드 모양을 거의 채우게 그린다.
        왼쪽 미리보기/더미/발동 애니메이션은 image_only=False로 전체 정보를 보여준다.
        """
        width = int(width)
        height = int(height)

        if width < 18 or height < 24:
            return

        if update_rect:
            if not self.dragging:
                self.rect = pygame.Rect(int(x), int(y), width, height)
            else:
                self.rect.size = (width, height)
            draw_x, draw_y = self.rect.x, self.rect.y
        else:
            draw_x, draw_y = int(x), int(y)

        rect = pygame.Rect(draw_x, draw_y, width, height)
        radius = max(5, min(width, height) // 12)
        border = max(1, width // 45)

        pygame.draw.rect(screen, self.color, rect, border_radius=radius)
        pygame.draw.rect(screen, DARK, rect, border, border_radius=radius)

        if image_only:
            pad = max(4, int(min(width, height) * 0.07))
            img_rect = pygame.Rect(draw_x + pad, draw_y + pad, width - pad * 2, height - pad * 2)
            if self.image:
                try:
                    scaled_img = pygame.transform.smoothscale(self.image, (img_rect.width, img_rect.height))
                    screen.blit(scaled_img, img_rect.topleft)
                except Exception:
                    pygame.draw.rect(screen, (215, 215, 215), img_rect, border_radius=max(3, width // 25))
            else:
                pygame.draw.rect(screen, (215, 215, 215), img_rect, border_radius=max(3, width // 25))
                pygame.draw.rect(screen, (160, 160, 160), img_rect, 1, border_radius=max(3, width // 25))
            return

        scale = width / DEFAULT_CARD_W
        small_card = width <= 95 or height <= 125

        name_size = max(8, int(16 * scale))
        type_size = max(7, int(12 * scale))
        desc_size = max(7, int(11 * scale))

        if small_card:
            name_size = max(8, min(name_size + 1, 10))
            type_size = max(7, min(type_size, 8))
            desc_size = max(7, min(desc_size, 8))

        c_font = pygame.font.SysFont("malgungothic", name_size, bold=True)
        t_font = pygame.font.SysFont("malgungothic", type_size)
        d_font = pygame.font.SysFont("malgungothic", desc_size)

        pad = max(4, int(10 * scale))
        max_text_width = max(10, width - pad * 2)

        name_max_lines = 2 if small_card else 3
        name_lines = _wrap_text_to_width(c_font, self.name, max_text_width, name_max_lines, ellipsis=True)
        y_cursor = draw_y + pad
        name_gap = max(c_font.get_linesize() - 2, name_size + 1)
        for line in name_lines:
            screen.blit(c_font.render(line, True, DARK), (draw_x + pad, y_cursor))
            y_cursor += name_gap

        type_text = f"[{self.card_type}]"
        type_lines = _wrap_text_to_width(t_font, type_text, max_text_width, 1, ellipsis=True)
        if type_lines:
            screen.blit(t_font.render(type_lines[0], True, (60, 60, 60)), (draw_x + pad, y_cursor))
            y_cursor += max(t_font.get_linesize() - 2, type_size + 1)

        y_cursor += max(2, int(4 * scale))

        bottom_limit = draw_y + height - pad
        desc_reserved = max(14, int(height * (0.18 if small_card else 0.20)))
        available_for_image = max(8, bottom_limit - y_cursor - desc_reserved)
        desired_img = int(height * (0.32 if small_card else 0.42))
        img_size = max(8, min(width - pad * 2, desired_img, available_for_image))
        img_x = draw_x + (width - img_size) // 2
        img_y = y_cursor

        if self.image and img_size > 0:
            try:
                scaled_img = pygame.transform.smoothscale(self.image, (img_size, img_size))
                screen.blit(scaled_img, (img_x, img_y))
            except Exception:
                pygame.draw.rect(screen, (215, 215, 215), (img_x, img_y, img_size, img_size), border_radius=max(3, width // 25))
        else:
            pygame.draw.rect(screen, (215, 215, 215), (img_x, img_y, img_size, img_size), border_radius=max(3, width // 25))
            pygame.draw.rect(screen, (160, 160, 160), (img_x, img_y, img_size, img_size), 1, border_radius=max(3, width // 25))

        desc_y = img_y + img_size + max(2, int(6 * scale))
        line_gap = max(d_font.get_linesize() - 2, desc_size + 1)
        max_lines = max(0, (bottom_limit - desc_y) // line_gap)
        if small_card:
            max_lines = min(max_lines, 2)

        desc_lines = _wrap_text_to_width(d_font, self.desc, max_text_width, max_lines, ellipsis=True)
        for idx, line in enumerate(desc_lines):
            screen.blit(d_font.render(line, True, DARK), (draw_x + pad, desc_y + idx * line_gap))


class CardDummy:
    def __init__(self):
        self.cardList = []

    def push(self, card):
        self.cardList.append(card)

    def pop(self):
        return self.cardList.pop() if not self.isEmpty() else None

    def isEmpty(self):
        return len(self.cardList) == 0

    def peek(self):
        return self.cardList[-1] if not self.isEmpty() else None


class CardOnHand:
    def __init__(self):
        self.cardList = []


class TrashCard:
    def __init__(self):
        self.cardList = []

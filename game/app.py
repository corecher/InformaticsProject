"""Pygame 화면, 입력, 애니메이션을 담당하는 실행 모듈입니다.

GameManager는 실제 카드 효과와 게임 상태를 처리하고,
이 모듈은 그 결과로 쌓인 시각 이벤트를 순서대로 재생합니다.

파일이 길어지는 것을 줄이기 위해 설정/카드 데이터/효과음/유틸 함수는 별도 모듈로 분리했습니다.
"""

import os
import pygame
import sys

from .audio import SoundManager
from .config import WIDTH, HEIGHT, WHITE, GRAY, DARK, RED, GREEN, FPS, CLEAR_HAND_SIZE, MAX_HAND_CARDS
from .manager import GameManager
from .utils import clamp, ease_out_cubic, ease_in_out, lerp, lerp_pos, format_time

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("그리다 만 게임")

font = pygame.font.SysFont("malgungothic", 25)
big_font = pygame.font.SysFont("malgungothic", 60)
mid_font = pygame.font.SysFont("malgungothic", 34)
log_font = pygame.font.SysFont("malgungothic", 13)
small_font = pygame.font.SysFont("malgungothic", 16)

start_button = pygame.Rect(450, 300, 300, 80)
exit_button = pygame.Rect(450, 410, 300, 80)
restart_button = pygame.Rect(450, 500, 300, 70)

selected_panel_rect = pygame.Rect(38, 45, 260, 385)
selected_card_rect = pygame.Rect(58, 68, 220, 352)
quit_game_button = pygame.Rect(58, 445, 222, 45)
skip_effect_button = pygame.Rect(58, 500, 222, 45)

status_bar_rect = pygame.Rect(330, 20, 820, 38)
draw_pile_rect = pygame.Rect(360, 82, 145, 230)
play_zone_rect = pygame.Rect(650, 112, 165, 215)
log_rect = pygame.Rect(840, 105, 320, 220)
hand_area_rect = pygame.Rect(315, 438, 682, 255)

HAND_X = 330
HAND_Y = 488
HAND_CARD_W = 78
HAND_CARD_H = 102
HAND_COL_GAP = 82
HAND_ROW_GAP = 106
CARDS_PER_ROW = 8
VISIBLE_HAND_ROWS = 2
VISIBLE_HAND_COUNT = CARDS_PER_ROW * VISIBLE_HAND_ROWS
HOVER_RISE = 16

MAX_TOTAL_QUEUED_EFFECTS = 220

clock = pygame.time.Clock()
manager = GameManager()

# =========================
# 효과음 설정
# =========================
# Sound 폴더의 mp3 파일을 카드 이동 공통 효과음으로 사용한다.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sound_manager = SoundManager(PROJECT_ROOT)

active_effect = None
effect_queue = []
hidden_cards = set()
visual_hand_cards = []  # 연출 기준 손패. 논리 손패와 분리해서, 애니메이션이 끝난 뒤 화면 상태를 갱신한다.
waiting_for_clear = False
effect_sequence_started_at = None




def get_effect_speed_multiplier():
    """연출이 길어질수록 자동으로 배속을 올린다.

    연출 묶음이 시작된 뒤 0~6초: 1배속, 7~13초: 2배속,
    14~20초: 3배속처럼 7초 단위로 빨라진다.
    """
    if effect_sequence_started_at is None:
        return 1
    elapsed_ms = max(0, pygame.time.get_ticks() - effect_sequence_started_at)
    return max(1, min(8, 1 + elapsed_ms // 7000))


def update_effect_sequence_timer():
    global effect_sequence_started_at
    if has_pending_effects():
        if effect_sequence_started_at is None:
            effect_sequence_started_at = pygame.time.get_ticks()
    else:
        effect_sequence_started_at = None


def get_queued_draw_card_after_current():
    """현재 화면에 보일 뽑을 더미의 맨 위 카드.

    논리 덱은 효과 처리 시점에 이미 최종 상태로 변하기 때문에,
    연출 중에는 effect_queue 안의 아직 화면에 뽑히지 않은 draw 이벤트를
    우선해서 보여준다.
    """
    for event in effect_queue:
        if event.get("kind") == "draw" and event.get("card"):
            return event.get("card")
    return None


def get_visual_draw_pile_card():
    queued_card = get_queued_draw_card_after_current()
    if queued_card:
        return queued_card
    if active_effect and active_effect.kind == "draw":
        # 현재 카드는 이미 날아가는 중이므로, 다음 예약 draw가 없으면 실제 더미 top을 보여준다.
        pass
    if not manager.card_dummy.isEmpty():
        return manager.card_dummy.peek()
    return None


def wrap_text_pixels(font_obj, text, max_width, max_lines=None):
    """로그/도움말용 픽셀 기준 줄바꿈."""
    text = str(text)
    lines = []
    current = ""

    for ch in text:
        if ch == "\n":
            lines.append(current.rstrip())
            current = ""
            if max_lines and len(lines) >= max_lines:
                break
            continue

        candidate = current + ch
        if font_obj.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current.rstrip())
            current = ch.lstrip()
            if max_lines and len(lines) >= max_lines:
                break

    if (not max_lines or len(lines) < max_lines) and current:
        lines.append(current.rstrip())

    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]

    if max_lines and len(lines) == max_lines:
        joined = "".join(lines)
        if len(joined) < len(text.replace("\n", "")):
            suffix = "..."
            last = lines[-1]
            while last and font_obj.size(last + suffix)[0] > max_width:
                last = last[:-1]
            lines[-1] = (last + suffix) if last else suffix

    return lines


def reset_visual_state():
    global active_effect, effect_sequence_started_at
    effect_queue.clear()
    active_effect = None
    effect_sequence_started_at = None
    hidden_cards.clear()
    visual_hand_cards.clear()


def sync_visual_hand_to_logical():
    """연출이 없을 때만 화면용 손패를 실제 게임 상태와 동기화한다.

    v12까지는 manager.card_on_hand가 이미 최종 상태로 바뀐 뒤 애니메이션만 재생되어,
    '8장 버리는 연출 중인데 이미 손패가 비어 보이는' 문제가 있었다.
    화면용 손패를 따로 두고 draw/discard 연출 완료 시점에 갱신해서 그 문제를 막는다.
    """
    visual_hand_cards[:] = manager.card_on_hand.cardList[:]


def get_render_hand_cards():
    # 연출이 진행 중이면 visual_hand_cards가 현재 화면에 보여줄 손패다.
    # 연출이 없을 때는 logical hand와 같도록 루프에서 동기화된다.
    return visual_hand_cards


def get_total_hand_rows():
    hand_cards = get_render_hand_cards()
    if not hand_cards:
        return 1
    return max(1, (len(hand_cards) + CARDS_PER_ROW - 1) // CARDS_PER_ROW)


def get_max_scroll_index():
    # 화면에는 항상 2행씩 보여주므로, 스크롤 가능한 시작 행은 전체 행 - 2까지만 허용한다.
    return max(0, get_total_hand_rows() - VISIBLE_HAND_ROWS)


def clamp_hand_scroll():
    manager.scroll_index = max(0, min(manager.scroll_index, get_max_scroll_index()))


def get_visible_hand_cards():
    clamp_hand_scroll()
    start_card_idx = manager.scroll_index * CARDS_PER_ROW
    return get_render_hand_cards()[start_card_idx:start_card_idx + VISIBLE_HAND_COUNT]


def get_hand_page_text():
    total_pages = get_max_scroll_index() + 1
    current_page = min(manager.scroll_index + 1, total_pages)
    return f"페이지: {current_page}/{total_pages} ({len(get_render_hand_cards())}장 보유)"


def get_hand_card_rect(card):
    hand_cards = get_render_hand_cards()
    if card not in hand_cards:
        return pygame.Rect(HAND_X + 6 * HAND_COL_GAP, HAND_Y + HAND_ROW_GAP, HAND_CARD_W, HAND_CARD_H)

    card_index = hand_cards.index(card)
    row_index = card_index // CARDS_PER_ROW
    max_scroll = get_max_scroll_index()

    if row_index < manager.scroll_index or row_index > manager.scroll_index + VISIBLE_HAND_ROWS - 1:
        manager.scroll_index = max(0, min(row_index, max_scroll))

    visible_index = card_index - manager.scroll_index * CARDS_PER_ROW
    row = visible_index // CARDS_PER_ROW
    col = visible_index % CARDS_PER_ROW
    return pygame.Rect(HAND_X + col * HAND_COL_GAP, HAND_Y + row * HAND_ROW_GAP, HAND_CARD_W, HAND_CARD_H)


def get_hand_card_effect_target_rect(card, frozen_scroll_index=None):
    """
    드로우 애니메이션 전용 목적지 계산.
    일반 get_hand_card_rect()는 카드가 현재 페이지 밖에 있으면 스크롤 위치를 바꾸기 때문에,
    여러 장을 동시에 뽑을 때 애니메이션 목적지가 흔들리는 문제가 생긴다.
    이 함수는 애니메이션 시작 시점의 페이지를 고정해서 목적지를 계산한다.
    """
    if frozen_scroll_index is None:
        frozen_scroll_index = manager.scroll_index

    hand_cards = get_render_hand_cards()
    if card in hand_cards:
        card_index = hand_cards.index(card)
    else:
        card_index = frozen_scroll_index * CARDS_PER_ROW

    start_index = frozen_scroll_index * CARDS_PER_ROW
    visible_index = card_index - start_index

    # 현재 보이는 2행 안에 들어오는 카드면 실제 칸으로 이동한다.
    if 0 <= visible_index < VISIBLE_HAND_COUNT:
        slot_index = visible_index
    # 현재 페이지 밖의 카드는 스크롤을 강제로 바꾸지 않고,
    # 보이는 손패 영역의 마지막 칸으로 모이게 해서 화면 밖/엉뚱한 곳으로 튀는 것을 막는다.
    elif visible_index < 0:
        slot_index = 0
    else:
        slot_index = VISIBLE_HAND_COUNT - 1

    row = slot_index // CARDS_PER_ROW
    col = slot_index % CARDS_PER_ROW
    return pygame.Rect(HAND_X + col * HAND_COL_GAP, HAND_Y + row * HAND_ROW_GAP, HAND_CARD_W, HAND_CARD_H)


def get_hand_card_effect_rect_by_index(hand_index, frozen_scroll_index=None):
    """버려진 카드처럼 이미 손패에서 빠진 카드의 이전 위치를 인덱스로 계산한다."""
    if frozen_scroll_index is None:
        frozen_scroll_index = manager.scroll_index

    if hand_index is None:
        hand_index = frozen_scroll_index * CARDS_PER_ROW

    start_index = frozen_scroll_index * CARDS_PER_ROW
    visible_index = hand_index - start_index
    if 0 <= visible_index < VISIBLE_HAND_COUNT:
        slot_index = visible_index
    elif visible_index < 0:
        slot_index = 0
    else:
        slot_index = VISIBLE_HAND_COUNT - 1

    row = slot_index // CARDS_PER_ROW
    col = slot_index % CARDS_PER_ROW
    return pygame.Rect(HAND_X + col * HAND_COL_GAP, HAND_Y + row * HAND_ROW_GAP, HAND_CARD_W, HAND_CARD_H)


class CardEffect:
    def __init__(self, card, kind, start_rect=None, target_rect=None, hand_index=None, logs=None, play_sound=True):
        self.card = card
        self.kind = kind
        self.start_rect = start_rect or pygame.Rect(draw_pile_rect)
        self.target_rect = target_rect
        self.hand_index = hand_index
        self.logs = list(logs or [])
        self.logs_shown = False
        self.start_time = pygame.time.get_ticks()
        if kind == "draw":
            self.duration = 430
        elif kind == "discard":
            self.duration = 390
        else:
            self.duration = 680

        # 뽑기/버리기/카드 내기 이동에만 효과음을 재생한다.
        # 카드 확대 발동 연출에는 소리를 내지 않는다.
        if play_sound and kind in ("draw", "discard"):
            sound_manager.play_card_move()

    def show_attached_logs(self):
        if self.logs_shown:
            return
        for msg in self.logs:
            manager.add_log_now(msg)
        self.logs_shown = True

    def get_scaled_elapsed(self):
        return (pygame.time.get_ticks() - self.start_time) * get_effect_speed_multiplier()

    def is_done(self):
        return self.get_scaled_elapsed() >= self.duration

    def draw(self, surface):
        elapsed = self.get_scaled_elapsed()
        if elapsed < 0:
            return
        t = clamp(elapsed / self.duration)

        if self.kind == "draw":
            hand_rect = self.target_rect or get_hand_card_effect_target_rect(self.card)
            e = ease_out_cubic(t)
            cx, cy = lerp_pos(self.start_rect.center, hand_rect.center, e)
            w = lerp(self.start_rect.width, HAND_CARD_W, e)
            h = lerp(self.start_rect.height, HAND_CARD_H, e)
            self.card.draw_at(surface, cx - w / 2, cy - h / 2, w, h, update_rect=False)
            return

        if self.kind == "discard":
            # 버려지는 카드: 손패 위치에서 카드 내기 영역으로 이동하며 살짝 작아진다.
            target = self.target_rect or play_zone_rect
            e = ease_in_out(t)
            cx, cy = lerp_pos(self.start_rect.center, target.center, e)
            pop = 1.0 + 0.15 * (1.0 - abs(0.5 - t) * 2.0)
            w = lerp(self.start_rect.width, HAND_CARD_W * 0.88, e) * pop
            h = lerp(self.start_rect.height, HAND_CARD_H * 0.88, e) * pop
            shadow = pygame.Surface((int(w + 12), int(h + 12)), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 45), shadow.get_rect(), border_radius=10)
            surface.blit(shadow, (cx - shadow.get_width() / 2 + 5, cy - shadow.get_height() / 2 + 6))
            self.card.draw_at(surface, cx - w / 2, cy - h / 2, w, h, update_rect=False)
            return

        # 카드 발동 연출: 카드 내기 영역에서 확대 → 짧게 유지 → 작아지며 사라짐.
        cx, cy = play_zone_rect.center
        if t < 0.18:
            scale = lerp(1.0, 3.9, ease_out_cubic(t / 0.18))
        elif t < 0.68:
            scale = 3.9
        else:
            scale = lerp(3.9, 0.0, ease_in_out((t - 0.68) / 0.32))

        w = HAND_CARD_W * scale
        h = HAND_CARD_H * scale
        if w < 18 or h < 24:
            return

        glow_w = int(w + 48)
        glow_h = int(h + 48)
        glow = pygame.Surface((glow_w, glow_h), pygame.SRCALPHA)
        pygame.draw.rect(glow, (255, 255, 255, 150), glow.get_rect(), border_radius=20)
        pygame.draw.rect(glow, (40, 40, 40, 140), glow.get_rect(), 4, border_radius=20)
        surface.blit(glow, (cx - glow_w // 2, cy - glow_h // 2))

        label = mid_font.render("발동!", True, DARK)
        label_x = cx - label.get_width() // 2
        label_y = max(10, cy - h / 2 - 50)
        # 카드가 크게 확대되어 화면 위쪽을 침범할 때도 발동 문구가 잘리지 않게 고정한다.
        shadow_label = mid_font.render("발동!", True, (255, 255, 255))
        surface.blit(shadow_label, (label_x + 2, label_y + 2))
        surface.blit(label, (label_x, label_y))
        self.card.draw_at(surface, cx - w / 2, cy - h / 2, w, h, update_rect=False)


def enqueue_effect_event(event):
    """manager.py에서 온 시각 이벤트를 실제 연출 큐로 옮긴다."""
    kind = event.get("kind")

    if kind == "log":
        msg = event.get("message", "")
        if not msg:
            return
        # 직전에 대기 중인 발동 연출이 있으면, 그 카드가 '발동!' 되는 순간 로그를 같이 띄운다.
        if effect_queue and effect_queue[-1].get("kind") == "activate":
            effect_queue[-1].setdefault("logs", []).append(msg)
        elif active_effect and active_effect.kind == "activate" and not active_effect.logs_shown:
            active_effect.logs.append(msg)
        else:
            effect_queue.append({"kind": "log", "message": msg})
        return

    card = event.get("card")
    if not card:
        return

    frozen_scroll_index = manager.scroll_index

    if kind == "draw":
        # 논리 손패에는 이미 들어갔지만, 화면용 손패에는 draw 연출 완료 시점에 추가한다.
        # 그래서 카드를 미리 숨기는 방식(hidden_cards)은 draw에는 쓰지 않는다.
        hand_index = event.get("hand_index")
        target_rect = (
            get_hand_card_effect_rect_by_index(hand_index, frozen_scroll_index)
            if hand_index is not None
            else get_hand_card_effect_target_rect(card, frozen_scroll_index)
        )
        effect_queue.append({
            "kind": "draw",
            "card": card,
            "start_rect": pygame.Rect(draw_pile_rect),
            "target_rect": target_rect,
            "hand_index": hand_index,
        })

    elif kind == "discard":
        hand_index = event.get("hand_index")
        effect_queue.append({
            "kind": "discard",
            "card": card,
            "start_rect": get_hand_card_effect_rect_by_index(hand_index, frozen_scroll_index),
            "target_rect": pygame.Rect(play_zone_rect),
            "hand_index": hand_index,
        })

    elif kind == "activate":
        effect_queue.append({
            "kind": "activate",
            "card": card,
            "start_rect": pygame.Rect(play_zone_rect),
            "target_rect": pygame.Rect(play_zone_rect),
            "hand_index": event.get("hand_index"),
        })


def collect_all_pending_effects():
    events = manager.consume_pending_effect_events()
    if not events:
        return

    available_slots = max(0, MAX_TOTAL_QUEUED_EFFECTS - len(effect_queue) - (1 if active_effect else 0))
    if len(events) > available_slots:
        # 내부 연출 큐 제한은 플레이 로그에 표시하지 않는다.
        events = events[:available_slots]

    for event in events:
        enqueue_effect_event(event)

    # 구버전 pending 리스트는 v12에서 직접 쓰지 않으므로 비워서 중복 연출을 막는다.
    manager.pending_draw_cards.clear()
    manager.pending_activation_cards.clear()


def start_next_effect_if_needed():
    global active_effect
    if active_effect:
        return
    while effect_queue:
        data = effect_queue.pop(0)
        if data.get("kind") == "log":
            manager.add_log_now(data.get("message", ""))
            continue
        break
    else:
        return
    active_effect = CardEffect(
        data["card"],
        data["kind"],
        start_rect=data.get("start_rect"),
        target_rect=data.get("target_rect"),
        hand_index=data.get("hand_index"),
        logs=data.get("logs"),
    )
    # 발동 로그는 발동 카드가 화면에 나타나는 순간 같이 표시한다.
    if active_effect.kind == "activate":
        active_effect.show_attached_logs()
    # discard 연출 중에는 손패 칸에 남은 원본을 잠깐 숨겨서, 날아가는 카드와 중복 표시되지 않게 한다.
    if active_effect.kind == "discard":
        hidden_cards.add(active_effect.card)


def finish_effect(effect):
    """효과 하나를 완료 처리한다. 실제 애니메이션이 끝났거나 스킵될 때 공통으로 사용한다."""
    if not effect:
        return

    if effect.kind == "activate":
        effect.show_attached_logs()

    card = effect.card
    if effect.kind == "draw":
        # draw 연출이 끝난 뒤에야 화면용 손패에 카드를 추가한다.
        if card not in visual_hand_cards:
            insert_index = effect.hand_index
            if insert_index is None:
                insert_index = len(visual_hand_cards)
            insert_index = max(0, min(int(insert_index), len(visual_hand_cards)))
            visual_hand_cards.insert(insert_index, card)

    elif effect.kind == "discard":
        # discard 연출이 끝난 뒤에야 화면용 손패에서 카드를 제거한다.
        if card in visual_hand_cards:
            visual_hand_cards.remove(card)
        hidden_cards.discard(card)


def skip_all_effects():
    """현재 남은 연출을 전부 스킵하고 최종 화면 상태로 맞춘다."""
    global active_effect
    collect_all_pending_effects()

    if active_effect:
        finish_effect(active_effect)
        active_effect = None

    while effect_queue:
        data = effect_queue.pop(0)
        if data.get("kind") == "log":
            manager.add_log_now(data.get("message", ""))
            continue
        temp = CardEffect(
            data["card"],
            data["kind"],
            start_rect=data.get("start_rect"),
            target_rect=data.get("target_rect"),
            hand_index=data.get("hand_index"),
            logs=data.get("logs"),
            play_sound=False,
        )
        finish_effect(temp)

    hidden_cards.clear()
    sync_visual_hand_to_logical()
    clamp_hand_scroll()


def update_visual_effects():
    global active_effect
    if active_effect and active_effect.is_done():
        finish_effect(active_effect)
        active_effect = None

    start_next_effect_if_needed()


def has_pending_effects():
    return bool(active_effect or effect_queue or getattr(manager, "pending_effect_events", []))


def interaction_locked():
    """연쇄 연출 중에는 카드 뽑기/사용을 막아서 상태 꼬임을 방지한다."""
    return manager.game_state == "game" and has_pending_effects()

def request_clear(current_time_sec):
    global waiting_for_clear
    if waiting_for_clear:
        return
    manager.final_time = current_time_sec
    waiting_for_clear = True
    # 결과창 전환 대기는 내부 상태이므로 로그에 표시하지 않는다.


def check_clear_condition(current_time_sec):
    # 뽑기/버리기/발동 연출이 남아있을 때는 중간 손패 수로 클리어 판정을 하지 않는다.
    # 예: 8장 뽑는 중 잠깐 7장이 되더라도, 전체 효과가 끝난 최종 손패가 7장일 때만 클리어.
    if manager.game_state != "game" or waiting_for_clear or has_pending_effects():
        return
    if manager.mingi_project_turns > 0:
        # 민기의 프로젝트가 활성화된 동안 발생한 클리어 조건은
        # 나중에 저장해두지 않고 이번 판정에서 완전히 무시한다.
        manager.force_clear = False
        return

    hand_count = len(get_render_hand_cards())
    has_cinderella = any(c.name == "신데렐라는 아쉬워 벌써 12시" for c in manager.card_on_hand.cardList)
    if manager.force_clear or hand_count == CLEAR_HAND_SIZE or (has_cinderella and hand_count == 12):
        request_clear(current_time_sec)


def draw_menu():
    title = big_font.render("그리다 만 게임", True, DARK)
    screen.blit(title, (410, 160))
    pygame.draw.rect(screen, (120, 220, 120), start_button, border_radius=5)
    screen.blit(font.render("게임 시작", True, DARK), (540, 325))
    pygame.draw.rect(screen, (240, 128, 128), exit_button, border_radius=5)
    screen.blit(font.render("게임 종료", True, DARK), (540, 435))


def draw_status_bar(current_time_sec):
    pygame.draw.rect(screen, (238, 238, 238), status_bar_rect, border_radius=8)
    pygame.draw.rect(screen, (190, 190, 190), status_bar_rect, 1, border_radius=8)

    hand_count = len(get_render_hand_cards())
    goal_color = GREEN if hand_count == CLEAR_HAND_SIZE else DARK
    texts = [
        (f"현재 카드 {hand_count}/{MAX_HAND_CARDS}", DARK),
        (f"목표 {CLEAR_HAND_SIZE}장", goal_color),
        (f"행동 {manager.total_actions}회", DARK),
        (f"시간 {format_time(current_time_sec)}", DARK),
    ]
    x = status_bar_rect.x + 18
    for text, color in texts:
        rendered = small_font.render(text, True, color)
        screen.blit(rendered, (x, status_bar_rect.y + 10))
        x += rendered.get_width() + 42

    status_text = ""
    status_color = RED
    if manager.turtle_neck_active:
        status_text = f"거북목 {manager.turtle_neck_counter}턴"
    elif manager.dog_bite_turns > 0:
        status_text = f"상처 {manager.dog_bite_turns}턴"
    if status_text:
        rendered = small_font.render(status_text, True, status_color)
        screen.blit(rendered, (status_bar_rect.right - rendered.get_width() - 18, status_bar_rect.y + 10))


def draw_selected_card_panel(selected_card):
    pygame.draw.rect(screen, (232, 232, 232), selected_panel_rect, border_radius=10)
    pygame.draw.rect(screen, (170, 170, 170), selected_panel_rect, 2, border_radius=10)

    if selected_card:
        selected_card.draw_at(
            screen,
            selected_card_rect.x,
            selected_card_rect.y,
            selected_card_rect.width,
            selected_card_rect.height,
            update_rect=False,
        )
    else:
        title = font.render("카드 미리보기", True, DARK)
        help_lines = [
            "손패 카드나 뽑을 카드에",
            "마우스를 올리거나",
            "카드를 드래그하면",
            "크게 표시됩니다.",
        ]
        screen.blit(title, (selected_panel_rect.centerx - title.get_width() // 2, 145))
        for idx, text in enumerate(help_lines):
            rendered = small_font.render(text, True, DARK)
            screen.blit(rendered, (selected_panel_rect.centerx - rendered.get_width() // 2, 205 + idx * 24))


def get_hovered_card(visible_cards, mouse_pos):
    if manager.drag_card or waiting_for_clear:
        return None, -1
    for idx in range(len(visible_cards) - 1, -1, -1):
        card = visible_cards[idx]
        if card in hidden_cards:
            continue
        row, col = idx // CARDS_PER_ROW, idx % CARDS_PER_ROW
        base_rect = pygame.Rect(HAND_X + col * HAND_COL_GAP, HAND_Y + row * HAND_ROW_GAP, HAND_CARD_W, HAND_CARD_H)
        hover_rect = base_rect.move(0, -HOVER_RISE)
        if base_rect.collidepoint(mouse_pos) or hover_rect.collidepoint(mouse_pos):
            return card, idx
    return None, -1


def get_hovered_draw_card(mouse_pos):
    if waiting_for_clear:
        return None
    if draw_pile_rect.collidepoint(mouse_pos):
        return get_visual_draw_pile_card()
    return None


def draw_log_panel():
    pygame.draw.rect(screen, (245, 245, 245), log_rect, border_radius=5)
    screen.blit(font.render("실시간 로그", True, DARK), (850, 110))

    old_clip = screen.get_clip()
    screen.set_clip(log_rect.inflate(-10, -10))

    max_width = log_rect.width - 24
    line_height = 17
    text_top = 147
    text_bottom = log_rect.bottom - 10
    max_lines = max(1, (text_bottom - text_top) // line_height)

    all_lines = []
    for log in manager.log_queue:
        wrapped = wrap_text_pixels(log_font, log, max_width, max_lines=3)
        if not wrapped:
            continue
        all_lines.extend(wrapped)

    visible_lines = all_lines[-max_lines:]
    for idx, line in enumerate(visible_lines):
        screen.blit(log_font.render(line, True, (30, 30, 30)), (850, text_top + idx * line_height))

    screen.set_clip(old_clip)


def draw_game(current_time_sec):
    visible_cards = get_visible_hand_cards()
    mouse_pos = pygame.mouse.get_pos()
    hovered_card, hovered_idx = get_hovered_card(visible_cards, mouse_pos)
    hovered_draw_card = get_hovered_draw_card(mouse_pos)
    selected_card = manager.drag_card if manager.drag_card else (hovered_card or hovered_draw_card)

    draw_selected_card_panel(selected_card)
    pygame.draw.rect(screen, RED, quit_game_button, border_radius=5)
    screen.blit(font.render("중도 포기", True, WHITE), (quit_game_button.x + 55, quit_game_button.y + 8))

    # 연출 중일 때만 왼쪽 아래에 스킵 버튼을 보여준다.
    if has_pending_effects() and not waiting_for_clear:
        pygame.draw.rect(screen, (70, 70, 70), skip_effect_button, border_radius=5)
        screen.blit(font.render("연출 스킵", True, WHITE), (skip_effect_button.x + 55, skip_effect_button.y + 8))

    draw_status_bar(current_time_sec)

    visual_top_card = get_visual_draw_pile_card()
    if visual_top_card:
        visual_top_card.draw_at(screen, draw_pile_rect.x, draw_pile_rect.y, draw_pile_rect.width, draw_pile_rect.height, update_rect=False)
    else:
        pygame.draw.rect(screen, GRAY, draw_pile_rect, border_radius=8)
        pygame.draw.rect(screen, DARK, draw_pile_rect, 2, border_radius=8)
        screen.blit(font.render("더미 없음", True, DARK), (382, 180))

    pygame.draw.rect(screen, (230, 230, 230), play_zone_rect, border_radius=5)
    screen.blit(font.render("카드 내기", True, DARK), (680, 197))

    draw_log_panel()

    pygame.draw.rect(screen, (220, 220, 220), hand_area_rect, border_radius=5)

    if get_render_hand_cards():
        label = get_hand_page_text()
        label_surface = small_font.render(label, True, DARK)
        screen.blit(label_surface, (hand_area_rect.centerx - label_surface.get_width() // 2, hand_area_rect.y + 8))

    for idx, card in enumerate(visible_cards):
        if card in hidden_cards or card == hovered_card:
            continue
        row, col = idx // CARDS_PER_ROW, idx % CARDS_PER_ROW
        card.draw_at(
            screen,
            HAND_X + col * HAND_COL_GAP,
            HAND_Y + row * HAND_ROW_GAP,
            HAND_CARD_W,
            HAND_CARD_H,
            update_rect=True,
        )

    if hovered_card:
        row, col = hovered_idx // CARDS_PER_ROW, hovered_idx % CARDS_PER_ROW
        hovered_card.draw_at(
            screen,
            HAND_X + col * HAND_COL_GAP,
            HAND_Y + row * HAND_ROW_GAP - HOVER_RISE,
            HAND_CARD_W,
            HAND_CARD_H,
            update_rect=True,
        )

    if waiting_for_clear:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 80))
        screen.blit(overlay, (0, 0))
        msg = mid_font.render("클리어 연출 정리 중...", True, DARK)
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, 365))


def draw_clear():
    screen.blit(big_font.render("GAME CLEAR", True, GREEN), (430, 115))
    pygame.draw.rect(screen, (245, 245, 245), (360, 235, 480, 210), border_radius=10)
    pygame.draw.rect(screen, DARK, (360, 235, 480, 210), 2, border_radius=10)
    screen.blit(font.render(f"최종 행동 횟수 : {manager.total_actions}회", True, DARK), (470, 280))
    screen.blit(font.render(f"걸린 시간 : {format_time(manager.final_time)}", True, DARK), (490, 330))
    screen.blit(font.render(f"최종 카드 수 : {len(manager.card_on_hand.cardList)}장", True, DARK), (495, 380))
    pygame.draw.rect(screen, (120, 220, 120), restart_button, border_radius=5)
    screen.blit(font.render("다시 하기", True, DARK), (550, 520))




def run_game():
    """게임을 실행하는 메인 루프입니다.

    이 루프는 매 프레임마다 다음 순서로 동작합니다.
    1. 현재 게임 상태와 연출 큐를 갱신한다.
    2. 메뉴/게임/클리어 화면을 그린다.
    3. 마우스 입력을 처리한다.
    4. 클리어 조건을 최종 상태 기준으로 검사한다.
    """
    global waiting_for_clear
    running = True
    while running:
        screen.fill(WHITE)
        current_time_sec = 0

        if manager.game_state == "game":
            current_time_sec = (pygame.time.get_ticks() - manager.start_ticks) // 1000
            if not waiting_for_clear and not has_pending_effects():
                manager.check_passive_traps()
            collect_all_pending_effects()

        update_effect_sequence_timer()
        update_visual_effects()
        update_effect_sequence_timer()

        if manager.game_state == "game" and not has_pending_effects() and not waiting_for_clear:
            sync_visual_hand_to_logical()
            clamp_hand_scroll()

        if waiting_for_clear and not has_pending_effects():
            waiting_for_clear = False
            reset_visual_state()
            manager.game_state = "clear"

        if manager.game_state == "menu":
            draw_menu()
        elif manager.game_state == "game":
            draw_game(manager.final_time if waiting_for_clear else current_time_sec)
        elif manager.game_state == "clear":
            draw_clear()

        if active_effect:
            active_effect.draw(screen)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if manager.game_state == "menu" and event.type == pygame.MOUSEBUTTONDOWN:
                if start_button.collidepoint(event.pos):
                    reset_visual_state()
                    waiting_for_clear = False
                    manager.start_game()
                    collect_all_pending_effects()
                elif exit_button.collidepoint(event.pos):
                    running = False

            elif manager.game_state == "game" and not waiting_for_clear:
                locked = interaction_locked()
                if event.type == pygame.MOUSEBUTTONDOWN and locked:
                    # 연출 중에는 일반 화면 클릭은 무시한다.
                    # 중도 포기는 허용하고, 남은 연출 스킵은 전용 버튼으로만 처리한다.
                    if quit_game_button.collidepoint(event.pos):
                        reset_visual_state()
                        waiting_for_clear = False
                        manager.game_state = "menu"
                    elif skip_effect_button.collidepoint(event.pos):
                        skip_all_effects()
                        current_time_sec = (pygame.time.get_ticks() - manager.start_ticks) // 1000
                        check_clear_condition(current_time_sec)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if draw_pile_rect.collidepoint(event.pos):
                        manager.total_actions += 1
                        manager.draw_card_from_dummy()
                        manager.tick_turn_counters()
                        collect_all_pending_effects()
                        current_time_sec = (pygame.time.get_ticks() - manager.start_ticks) // 1000
                        check_clear_condition(current_time_sec)
                    elif quit_game_button.collidepoint(event.pos):
                        reset_visual_state()
                        waiting_for_clear = False
                        manager.game_state = "menu"
                    else:
                        visible_cards = get_visible_hand_cards()
                        for card in reversed(visible_cards):
                            if card in hidden_cards:
                                continue
                            if card.rect.collidepoint(event.pos):
                                manager.drag_card = card
                                card.dragging = True
                                card.offset_x = card.rect.x - event.pos[0]
                                card.offset_y = card.rect.y - event.pos[1]
                                break

                elif event.type == pygame.MOUSEMOTION and manager.drag_card and manager.drag_card.dragging:
                    manager.drag_card.rect.x = event.pos[0] + manager.drag_card.offset_x
                    manager.drag_card.rect.y = event.pos[1] + manager.drag_card.offset_y

                elif event.type == pygame.MOUSEBUTTONUP and manager.drag_card:
                    manager.drag_card.dragging = False
                    if play_zone_rect.colliderect(manager.drag_card.rect) and manager.drag_card in manager.card_on_hand.cardList:
                        if manager.drag_card.card_type != "행동":
                            manager.add_log_now(f"{manager.drag_card.card_type} 카드는 직접 낼 수 없습니다!")
                        else:
                            used_card = manager.drag_card
                            manager.score += 1
                            manager.total_actions += 1
                            manager.play_action_card(used_card)
                            collect_all_pending_effects()
                            clamp_hand_scroll()
                            current_time_sec = (pygame.time.get_ticks() - manager.start_ticks) // 1000
                            check_clear_condition(current_time_sec)
                    manager.drag_card = None

                elif event.type == pygame.MOUSEWHEEL and not locked:
                    manager.scroll_index += -1 if event.y > 0 else 1
                    clamp_hand_scroll()

            elif manager.game_state == "clear" and event.type == pygame.MOUSEBUTTONDOWN:
                if restart_button.collidepoint(event.pos):
                    reset_visual_state()
                    waiting_for_clear = False
                    manager.start_game()
                    collect_all_pending_effects()

        if manager.game_state == "game" and not waiting_for_clear and not has_pending_effects():
            current_time_sec = (pygame.time.get_ticks() - manager.start_ticks) // 1000
            check_clear_condition(current_time_sec)

        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run_game()

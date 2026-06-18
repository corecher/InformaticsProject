"""게임 규칙과 카드 효과를 처리하는 핵심 로직 모듈입니다.

이 파일은 화면을 직접 그리지 않습니다.
대신 손패/더미/버린더미 상태를 바꾸고, 화면에서 재생할 연출 이벤트를 큐에 쌓습니다.

중요한 설계 규칙:
- 손패는 스택입니다. 뽑기는 append, 버리기는 최신 카드부터 처리합니다.
- 즉발 카드는 뽑히면 효과가 발동하지만 손패에는 남습니다.
- n장 달성형 함정은 모든 연출/효과가 끝난 뒤 최종 손패 수로 판정합니다.
"""

import datetime
import random
import pygame
from .card_data import CARD_POOL
from .config import MAX_HAND_CARDS, START_DECK_SIZE, START_HAND_SIZE
from .models import Card, CardDummy, CardOnHand, TrashCard

# 한 번의 효과에서 무한 드로우가 나지 않게 막는 제한입니다.
# 게임 규칙 수치(시작 덱/시작 손패/최대 손패)는 config.py의 값을 사용합니다.
MAX_SINGLE_DRAW_RESOLVE = 300


class GameManager:
    def __init__(self):
        self.game_state = "menu"
        self.score = 0
        self.total_actions = 0
        self.start_ticks = 0
        self.final_time = 0
        self.force_clear = False

        self.card_dummy = CardDummy()
        self.card_on_hand = CardOnHand()
        self.trash_card = TrashCard()

        self.drag_card = None
        self.scroll_index = 0
        self.show_preview = False

        self.last_played_card_name = ""
        self.turtle_neck_active = False
        self.turtle_neck_counter = 0
        self.mingi_project_turns = 0
        self.dog_bite_turns = 0
        self.log_queue = []

        self.pending_draw_cards = []  # 구버전 호환용. v12에서는 pending_effect_events를 사용한다.
        self.pending_activation_cards = []  # 구버전 호환용. v12에서는 pending_effect_events를 사용한다.
        self.pending_effect_events = []

        self.draw_queue_count = 0
        self.is_resolving_draws = False
        self.action_queue = []
        self.is_processing_actions = False
        self.passive_lock = False

    # -------------------------
    # 공통 유틸
    # -------------------------
    def add_log_now(self, msg):
        """실제 로그창에 즉시 출력한다.

        카드 효과 로그는 연출 순서에 맞춰 보여야 하므로 보통 add_log()를 사용한다.
        UI 경고처럼 연출과 무관한 메시지만 이 함수를 직접 쓴다.
        """
        self.log_queue.append(str(msg))
        if len(self.log_queue) > 24:
            self.log_queue.pop(0)

    def add_log(self, msg):
        """카드 효과 로그를 연출 큐에 넣는다.

        v16부터는 효과 처리 순간에 로그창에 바로 띄우지 않고,
        main.py가 draw/discard/activate 연출 순서에 맞춰 표시한다.
        """
        self.pending_effect_events.append({
            "kind": "log",
            "message": str(msg),
        })

    def effect_log(self, card, detail):
        card_name = card.name if card else "효과"
        self.add_log(f"{card_name} 발동: {detail}")

    def queue_visual_event(self, kind, card, hand_index=None):
        """main.py가 순서대로 연출할 시각 이벤트를 기록한다.

        kind:
        - draw: 더미 -> 손패
        - discard: 손패 -> 카드 내기/버린 더미 쪽
        - activate: 카드 내기 영역에서 확대 발동
        """
        if card:
            self.pending_effect_events.append({
                "kind": kind,
                "card": card,
                "hand_index": hand_index,
            })

    def queue_activation_effect(self, card):
        if card:
            self.pending_activation_cards.append(card)
            self.queue_visual_event("activate", card)

    def consume_pending_effect_events(self):
        events = self.pending_effect_events[:]
        self.pending_effect_events.clear()
        return events

    def consume_pending_draw_cards(self):
        cards = self.pending_draw_cards[:]
        self.pending_draw_cards.clear()
        return cards

    def consume_pending_activation_cards(self):
        cards = self.pending_activation_cards[:]
        self.pending_activation_cards.clear()
        return cards

    def is_card_in_any_zone(self, card):
        return (
            card in self.card_on_hand.cardList
            or card in self.card_dummy.cardList
            or card in self.trash_card.cardList
        )

    def make_card(self, name):
        data = next((d for d in CARD_POOL if d["name"] == name), None)
        return Card(data) if data else None

    def start_game(self):
        self.score = 0
        self.total_actions = 0
        self.scroll_index = 0
        self.drag_card = None
        self.show_preview = False
        self.last_played_card_name = ""
        self.turtle_neck_active = False
        self.turtle_neck_counter = 0
        self.mingi_project_turns = 0
        self.dog_bite_turns = 0
        self.force_clear = False
        self.log_queue = []
        self.pending_draw_cards = []
        self.pending_activation_cards = []
        self.pending_effect_events = []
        self.draw_queue_count = 0
        self.is_resolving_draws = False
        self.action_queue = []
        self.is_processing_actions = False
        self.passive_lock = False

        self.start_ticks = pygame.time.get_ticks()
        self.final_time = 0
        self.card_dummy = CardDummy()
        self.card_on_hand = CardOnHand()
        self.trash_card = TrashCard()

        for _ in range(START_DECK_SIZE):
            self.card_dummy.push(Card(random.choice(CARD_POOL)))

        self.add_log("게임을 시작합니다! 목표는 정확히 7장 맞추기.")
        for _ in range(START_HAND_SIZE):
            self.raw_draw_logic()

        self.game_state = "game"

    def refill_dummy_from_trash(self):
        if self.trash_card.cardList:
            for c in self.trash_card.cardList:
                c.instant_triggered = False
            self.card_dummy.cardList.extend(self.trash_card.cardList)
            self.trash_card.cardList.clear()
            random.shuffle(self.card_dummy.cardList)

    def generate_emergency_cards(self):
        self.add_log("카드가 모두 고갈되어 새 카드 세트를 불러옵니다!")
        for _ in range(START_DECK_SIZE):
            self.card_dummy.push(Card(random.choice(CARD_POOL)))

    def ensure_dummy_has_card(self):
        if self.card_dummy.isEmpty():
            if self.trash_card.cardList:
                self.refill_dummy_from_trash()
            else:
                self.generate_emergency_cards()
        return not self.card_dummy.isEmpty()

    def safe_pop_random(self, target_list):
        """구버전 호환용 이름. 손패는 스택이므로 가장 최근 카드를 pop한다."""
        if target_list:
            return target_list.pop()
        return None

    def discard_card(self, card, check_traps=True):
        """손패에 있는 특정 카드를 버린더미로 보내고, 손패 -> 카드 내기 영역 연출을 예약한다.

        check_traps=True이면 카드가 버려진 직후 즉시 반응형 함정을 검사합니다.
        단, 행동카드를 직접/자동으로 사용할 때는 먼저 행동 효과와 묵비권 판정을 처리해야 하므로
        play_action_card()에서 check_traps=False로 제거한 뒤 마지막에 함정을 검사합니다.
        """
        if card in self.card_on_hand.cardList:
            hand_index = self.card_on_hand.cardList.index(card)
            self.card_on_hand.cardList.remove(card)
            self.trash_card.cardList.append(card)
            self.queue_visual_event("discard", card, hand_index=hand_index)
            if check_traps:
                # 카드가 버려지는 도중에도 카드 수와 무관한 조건형 함정은 즉시 확인한다.
                self.check_reactive_traps()
            return True
        return False

    def play_action_card(self, card, show_animation=True):
        """행동카드 1장을 '사용 비용 지불 -> 효과 처리 -> 반응형 함정 확인' 순서로 처리한다.

        예전 구조에서는 손패에서 행동카드를 버리는 순간 check_reactive_traps()가 먼저 돌아서,
        '묵비권'보다 '토큰을 다 쓴 이승찬' 같은 반응형 함정이 먼저 터질 수 있었습니다.
        이 함수는 행동카드 처리 순서를 한 곳으로 모아 그 우선순위 꼬임을 막습니다.

        행동 횟수 증가는 플레이어가 직접 사용했을 때 app.py에서만 처리합니다.
        카드 효과로 자동 사용되는 행동카드는 의도대로 total_actions에 포함하지 않습니다.
        """
        if not card or card.card_type != "행동":
            return False

        if card in self.card_on_hand.cardList:
            self.discard_card(card, check_traps=False)

        self.execute_action_card(card, show_animation=show_animation)
        self.check_reactive_traps()
        return True

    def discard_random_cards(self, count, exclude_cards=None):
        """손패에서 카드를 버린다.

        이름은 기존 코드 호환 때문에 random으로 남겨두지만,
        실제 규칙은 스택(LIFO)이다. 즉, 가장 최근에 얻은 카드부터 버린다.
        exclude_cards에 들어간 카드는 건너뛰고 그 다음 최신 카드를 버린다.
        """
        exclude_cards = set(exclude_cards or [])
        discarded = 0
        for _ in range(max(0, int(count))):
            popped_card = None
            for c in reversed(self.card_on_hand.cardList):
                if c not in exclude_cards:
                    popped_card = c
                    break
            if not popped_card:
                break
            if self.discard_card(popped_card):
                discarded += 1
        return discarded

    def discard_all_hand(self, exclude_cards=None):
        """손패 전체를 버릴 때도 가장 최근에 얻은 카드부터 버린다."""
        exclude_cards = set(exclude_cards or [])
        discarded = 0
        for c in list(reversed(self.card_on_hand.cardList[:])):
            if c in exclude_cards:
                continue
            if self.discard_card(c):
                discarded += 1
        return discarded

    def remove_card_from_all_zones(self, name):
        before = (
            len(self.card_on_hand.cardList)
            + len(self.card_dummy.cardList)
            + len(self.trash_card.cardList)
        )
        self.card_on_hand.cardList = [c for c in self.card_on_hand.cardList if c.name != name]
        self.card_dummy.cardList = [c for c in self.card_dummy.cardList if c.name != name]
        self.trash_card.cardList = [c for c in self.trash_card.cardList if c.name != name]
        after = (
            len(self.card_on_hand.cardList)
            + len(self.card_dummy.cardList)
            + len(self.trash_card.cardList)
        )
        return before - after

    # -------------------------
    # 카드 획득 / 뽑기 처리
    # -------------------------
    def raw_draw_logic(self):
        """카드 1장을 손패로 가져온다. 즉발 카드는 손패에 남지만 획득 순간 1회 발동한다."""
        if len(self.card_on_hand.cardList) >= MAX_HAND_CARDS:
            self.add_log("손패가 너무 많아 더 뽑을 수 없습니다.")
            return None

        if not self.ensure_dummy_has_card():
            return None

        new_card = self.card_dummy.pop()
        if not new_card:
            return None

        # 버린더미에서 재사용된 즉발 카드도 다시 뽑히면 1회 발동 가능하게 초기화.
        new_card.instant_triggered = False
        self.card_on_hand.cardList.append(new_card)
        draw_index = len(self.card_on_hand.cardList) - 1
        self.pending_draw_cards.append(new_card)
        self.queue_visual_event("draw", new_card, hand_index=draw_index)
        self.on_card_acquired(new_card)
        # 카드 수 달성형 함정은 연출이 모두 끝난 뒤 판정하지만,
        # 우진/묵비권/토큰처럼 카드 수와 무관한 조건형 함정은
        # 뽑기 처리 중에도 즉시 반응하게 한다.
        self.check_reactive_traps()
        return new_card

    def on_card_acquired(self, card):
        """카드를 손패에 얻는 순간 발동해야 하는 효과들을 한 곳에서 처리한다."""
        if not card:
            return

        self.apply_acquire_traps(card)

        if card.name == "대훈이의 거북목":
            self.turtle_neck_active = True
            self.turtle_neck_counter = 5
            self.queue_activation_effect(card)
            self.effect_log(card, "5턴 안에 호현이를 얻지 못하면 모든 카드를 버립니다.")

        if card.card_type == "즉발":
            self.trigger_instant_card(card)

    def apply_acquire_traps(self, acquired_card):
        """카드 획득 순간 조건을 보는 함정 처리."""
        if not acquired_card:
            return

        # 그리다 만: 게임 카드 획득 시 그리다 만과 방금 얻은 게임만 남긴다.
        if acquired_card.name == "게임":
            grida = next(
                (c for c in self.card_on_hand.cardList if c.name == "그리다 만" and c is not acquired_card),
                None,
            )
            if grida:
                self.queue_activation_effect(grida)
                discarded = self.discard_all_hand(exclude_cards=[grida, acquired_card])
                self.effect_log(grida, f"게임 카드를 얻어서 다른 카드 {discarded}장을 모두 버립니다.")

    def draw_card_from_dummy(self, count=1):
        count = max(0, int(count))
        self.draw_queue_count += count
        if self.is_resolving_draws:
            return 0

        self.is_resolving_draws = True
        resolved = 0
        while self.draw_queue_count > 0 and resolved < MAX_SINGLE_DRAW_RESOLVE:
            self.draw_queue_count -= 1
            self.raw_draw_logic()
            resolved += 1
            if len(self.card_on_hand.cardList) >= MAX_HAND_CARDS:
                self.draw_queue_count = 0
                break

        if self.draw_queue_count > 0:
            self.add_log(f"한 번에 너무 많은 뽑기 요청이 있어 {self.draw_queue_count}장은 생략했습니다.")
            self.draw_queue_count = 0
        self.is_resolving_draws = False
        return resolved

    def recover_top_trash_except(self, excluded_card=None):
        """버린더미 맨 위 카드 회수. 방금 사용한 환경지킴이를 바로 다시 가져오는 문제를 막는다."""
        for idx in range(len(self.trash_card.cardList) - 1, -1, -1):
            target = self.trash_card.cardList[idx]
            if target is excluded_card:
                continue
            recovered = self.trash_card.cardList.pop(idx)
            recovered.instant_triggered = False
            self.card_on_hand.cardList.append(recovered)
            draw_index = len(self.card_on_hand.cardList) - 1
            self.pending_draw_cards.append(recovered)
            self.queue_visual_event("draw", recovered, hand_index=draw_index)
            self.add_log(f"결과: 버린더미에서 '{recovered.name}' 카드를 회수했습니다.")
            self.on_card_acquired(recovered)
            return recovered
        self.add_log("결과: 회수할 카드가 없습니다.")
        return None

    # -------------------------
    # 즉발 카드
    # -------------------------
    def trigger_instant_card(self, card):
        """즉발 카드 효과. 카드는 손패에 남고 직접 낼 수 없다."""
        if not card or getattr(card, "instant_triggered", False):
            return

        card.instant_triggered = True
        self.queue_activation_effect(card)
        self.effect_log(card, card.desc)
        keep_self = [card]

        if card.name == "중간고사":
            discarded = self.discard_random_cards(3, exclude_cards=keep_self)
            self.add_log(f"결과: 가장 최근에 얻은 카드부터 {discarded}장을 버렸습니다.")


        elif card.name == "거북목 치료사 호현이":
            if self.turtle_neck_active:
                self.add_log("결과: 거북목 디버프를 해제했습니다.")
            else:
                self.add_log("결과: 현재 해제할 거북목 디버프가 없습니다.")
            self.turtle_neck_active = False
            self.turtle_neck_counter = 0

        elif card.name == "민기의 프로젝트":
            self.mingi_project_turns = 3
            self.add_log("결과: 3턴 동안 클리어 판정을 잠시 막습니다.")

        elif card.name == "도둑이야!":
            discarded = self.discard_random_cards(8, exclude_cards=keep_self)
            self.add_log(f"결과: 가장 최근에 얻은 카드부터 {discarded}장을 버렸습니다.")

        elif card.name == "임산부야!":
            self.add_log("결과: 카드 1장을 추가로 뽑습니다.")
            self.raw_draw_logic()

        elif card.name == "깜짝이야!":
            actions = [c for c in reversed(self.card_on_hand.cardList[:]) if c.card_type == "행동"]
            self.add_log(f"결과: 손패의 행동카드 {len(actions)}장을 순서대로 사용합니다.")
            for act in actions:
                if act in self.card_on_hand.cardList:
                    self.add_action(act)

        elif card.name == "크리퍼":
            targets = [c for c in reversed(self.card_on_hand.cardList[:]) if c.card_type != "함정" and c is not card]
            discarded = 0
            for target in targets:
                if self.discard_card(target):
                    discarded += 1
            self.add_log(f"결과: 함정카드와 이 즉발카드를 제외하고 {discarded}장을 버렸습니다.")

        elif card.name == "사지절단":
            targets = [c for c in reversed(self.card_on_hand.cardList[:]) if c.card_type == "행동"]
            discarded = 0
            for target in targets:
                if self.discard_card(target):
                    discarded += 1
            self.add_log(f"결과: 손패의 행동카드 {discarded}장을 버렸습니다.")

        elif card.name == "ADHD":
            drawn = 0
            found_action = None
            for _ in range(MAX_SINGLE_DRAW_RESOLVE):
                new_card = self.raw_draw_logic()
                if not new_card:
                    break
                drawn += 1
                if new_card.card_type == "행동":
                    found_action = new_card
                    break
            if found_action:
                self.add_log(f"결과: {drawn}장째에 나온 행동카드 '{found_action.name}'을 즉시 사용합니다.")
                self.add_action(found_action)
            else:
                self.add_log(f"결과: {drawn}장을 뽑았지만 행동카드를 찾지 못했습니다.")

        elif card.name == "준민이의 퍼리박스":
            animals = ["대훈이의 거북목", "공룡 멸망 동윤 등장", "개한테 물렸어!"]
            targets = [c for c in reversed(self.card_on_hand.cardList[:]) if c.name in animals and c is not card]
            self.add_log(f"결과: 동물 관련 카드 {len(targets)}장을 조건 없이 발동합니다.")
            for target in targets:
                if target.card_type == "행동":
                    if target in self.card_on_hand.cardList:
                        self.add_action(target)
                elif target.card_type == "함정":
                    self.trigger_trap_card(target, forced=True, remove_when_used=False)

        elif card.name == "히히 오줌!":
            self.add_log("결과: 아무 일도 일어나지 않았습니다.")

        elif card.name == "메카드 한장이면 충분해 파이널 어빌리티 스파크여 작렬하라 볼트 스파이크":
            discarded = self.discard_all_hand(exclude_cards=keep_self)
            self.add_log(f"결과: 이 카드 1장만 남기고 {discarded}장을 버렸습니다.")

    # -------------------------
    # 행동 카드
    # -------------------------
    def add_action(self, card):
        if not card:
            return
        self.action_queue.append(card)
        if not self.is_processing_actions:
            self.process_action_queue()

    def process_action_queue(self):
        self.is_processing_actions = True
        safety = 0
        while self.action_queue and safety < 100:
            safety += 1
            action_card = self.action_queue.pop(0)
            try:
                self.play_action_card(action_card)
            except Exception as e:
                self.add_log(f"액션 실행 오류: {e}")
        if self.action_queue:
            self.action_queue.clear()
            # 내부 무한 루프 방지용 중단. 플레이 로그에는 표시하지 않는다.
        self.is_processing_actions = False

    def execute_action_card(self, card, show_animation=True):
        if not card:
            return

        # 묵비권 함정은 행동카드 효과를 1회 무시한다.
        silence = next((c for c in self.card_on_hand.cardList if c.name == "당신은 묵비권을 행사할 수 있으며"), None)
        if silence:
            self.discard_card(silence)
            self.queue_activation_effect(silence)
            self.effect_log(silence, f"'{card.name}'의 행동카드 효과를 무시합니다.")
            self.last_played_card_name = card.name
            self.tick_turn_counters()
            return

        if show_animation:
            self.queue_activation_effect(card)
        self.effect_log(card, card.desc)

        if card.name == "게임":
            self.add_log("결과: 카드 3장을 뽑습니다.")
            self.draw_card_from_dummy(3)

        elif card.name in ["소리 질러", "하투하투"]:
            self.add_log("결과: 카드 2장을 뽑습니다.")
            self.draw_card_from_dummy(2)

        elif card.name == "밥 먹을 시간이다":
            amount = len(self.card_on_hand.cardList) * 2
            self.add_log(f"결과: 현재 손패 수의 2배인 카드 {amount}장을 뽑습니다.")
            self.draw_card_from_dummy(amount)

        elif card.name == "빛 빚 빗":
            if random.random() < 0.5:
                self.add_log("결과: 성공! 카드 4장을 뽑습니다.")
                self.draw_card_from_dummy(4)
            else:
                discarded = self.discard_random_cards(3)
                self.add_log(f"결과: 실패! 카드 {discarded}장을 버렸습니다.")

        elif card.name == "준민이는 씨리얼 1짱":
            if self.last_played_card_name == "집 나간 승찬이":
                before = len(self.card_on_hand.cardList)
                while len(self.card_on_hand.cardList) > 6:
                    self.discard_card(self.card_on_hand.cardList[-1])
                safety = 0
                while len(self.card_on_hand.cardList) < 6 and safety < MAX_SINGLE_DRAW_RESOLVE:
                    self.raw_draw_logic()
                    safety += 1
                self.add_log(f"결과: 직전 카드 연계 성공. 손패 {before}장 → {len(self.card_on_hand.cardList)}장")
            else:
                self.add_log("결과: 직전에 '집 나간 승찬이'를 쓰지 않아 효과 없음.")

        elif card.name == "집 나간 승찬이":
            self.add_log("결과: 카드 15장을 뽑습니다.")
            self.draw_card_from_dummy(15)

        elif card.name == "윤규는 숫돌이":
            discarded = self.discard_random_cards(5)
            self.add_log(f"결과: 카드 {discarded}장을 버렸습니다.")

        elif card.name == "공룡 멸망 동윤 등장":
            curr = len(self.card_on_hand.cardList)
            discarded = self.discard_all_hand()
            self.add_log(f"결과: 손패 {discarded}장을 모두 버리고 {curr}장을 새로 뽑습니다.")
            self.draw_card_from_dummy(curr)

        elif card.name in ["어떻게 토큰이 1억개야", "무명 카드"]:
            self.add_log("결과: 카드 100장을 뽑습니다.")
            self.draw_card_from_dummy(100)

        elif card.name == "나는야 환경지킴이":
            self.recover_top_trash_except(card)

        elif card.name == "윤규의 축복":
            discarded = self.discard_random_cards(4)
            self.add_log(f"결과: 윤규의 축복을 거부하고 카드 {discarded}장을 버렸습니다.")

        elif card.name == "지금 몇시지":
            hr = datetime.datetime.now().hour or 12
            self.add_log(f"결과: 현재 시각 기준으로 카드 {hr}장을 뽑습니다.")
            self.draw_card_from_dummy(hr)

        elif card.name == "뽑으세요!":
            amount = random.randint(2, 5)
            self.add_log(f"결과: 카드 {amount}장을 뽑습니다.")
            self.draw_card_from_dummy(amount)

        elif card.name == "저는 이승찬입니다":
            removed = self.remove_card_from_all_zones("거북목 치료사 호현이")
            self.add_log(f"결과: 모든 구역에서 '거북목 치료사 호현이' {removed}장을 제거합니다.")

        elif card.name == "개한테 물렸어!":
            self.dog_bite_turns = 3
            self.add_log("결과: 3턴 동안 매 턴 카드 1장을 잃습니다.")

        elif card.name == "변신이다!":
            cnt = len(self.card_on_hand.cardList)
            discarded = self.discard_all_hand()
            self.add_log(f"결과: 손패 {discarded}장을 버리고 {cnt}장을 새로 뽑습니다.")
            self.draw_card_from_dummy(cnt)

        elif card.name == "지뢰해체전문가":
            traps = [c for c in self.card_on_hand.cardList if c.card_type == "함정"]
            if traps:
                trap = traps[-1]
                self.discard_card(trap)
                self.add_log(f"결과: 함정 '{trap.name}' 1장을 버렸습니다.")
            else:
                self.add_log("결과: 제거할 함정카드가 없습니다.")


        elif card.name == "종이접기":
            amount = len(self.card_on_hand.cardList) // 2
            discarded = self.discard_random_cards(amount)
            self.add_log(f"결과: 손패의 절반인 카드 {discarded}장을 버렸습니다.")

        elif card.name == "퉤!":
            discarded = self.discard_random_cards(1)
            self.add_log(f"결과: 카드 {discarded}장을 버렸습니다.")

        elif card.name == "마우가 정신":
            drawn = 0
            found_trap = None
            for _ in range(MAX_SINGLE_DRAW_RESOLVE):
                new_card = self.raw_draw_logic()
                if not new_card:
                    break
                drawn += 1
                if new_card.card_type == "함정":
                    found_trap = new_card
                    break
            if found_trap:
                self.add_log(f"결과: {drawn}장째에 나온 함정카드 '{found_trap.name}'을 조건 무시 발동합니다.")
                self.trigger_trap_card(found_trap, forced=True, remove_when_used=False)
            else:
                self.add_log(f"결과: {drawn}장을 뽑았지만 함정카드를 찾지 못했습니다.")

        elif card.name == "이승찬의 신음소리":
            amount = random.randint(2, 8)
            discarded = self.discard_random_cards(amount)
            self.add_log(f"결과: 카드 {discarded}장을 버렸습니다.")

        elif card.name == "난 이제 부자야":
            before = len(self.card_on_hand.cardList)
            safety = 0
            while len(self.card_on_hand.cardList) < 20 and safety < MAX_SINGLE_DRAW_RESOLVE:
                self.raw_draw_logic()
                safety += 1
            self.add_log(f"결과: 손패가 20장이 될 때까지 뽑습니다. {before}장 → {len(self.card_on_hand.cardList)}장")

        elif card.name == "우진":
            names_2_5 = ["준민", "승찬", "윤규", "동윤", "민기", "대훈", "호현", "우진"]
            targets = [c for c in reversed(self.card_on_hand.cardList[:]) if any(n in c.name for n in names_2_5)]
            removed = 0
            for target in targets:
                if self.discard_card(target):
                    removed += 1
            self.add_log(f"결과: 2-5반 이름이 들어간 카드 {removed}장을 버렸습니다.")

        elif card.name == "히히 똥!":
            self.add_log("결과: 아무 일도 일어나지 않았습니다.")

        else:
            self.add_log("결과: 아직 등록되지 않은 행동카드라 아무 일도 일어나지 않았습니다.")

        self.last_played_card_name = card.name
        self.tick_turn_counters()

    # -------------------------
    # 함정 카드
    # -------------------------
    def trigger_trap_card(self, card, forced=False, remove_when_used=True):
        """함정 효과를 실제로 실행한다.

        forced=True는 '마우가 정신'처럼 조건을 무시하고 발동하는 경우다.
        remove_when_used=True는 조건형 함정이 발동 후 버린더미로 가야 할 때 사용한다.
        """
        if not card:
            return False

        name = card.name
        self.queue_activation_effect(card)

        if name == "그리다 만":
            if forced:
                discarded = self.discard_all_hand(exclude_cards=[card])
                self.effect_log(card, f"조건 무시 발동. 이 카드만 남기고 {discarded}장을 버립니다.")
                return True
            return False

        if name == "신데렐라는 아쉬워 벌써 12시":
            if forced or len(self.card_on_hand.cardList) == 12:
                if self.mingi_project_turns > 0:
                    # 민기의 프로젝트는 게임 종료 조건을 면제하므로,
                    # 이 순간의 승리 조건을 나중에 저장해두지 않는다.
                    self.force_clear = False
                    self.effect_log(card, "승리 조건이 만족됐지만 민기의 프로젝트로 이번 클리어 판정을 막습니다.")
                else:
                    self.force_clear = True
                    self.effect_log(card, "승리 조건을 만족하여 게임을 클리어합니다.")
                return True
            return False

        if name == "대훈이의 거북목":
            self.turtle_neck_active = True
            self.turtle_neck_counter = 5
            self.effect_log(card, "거북목 카운트를 5턴으로 시작합니다.")
            return True

        if name == "토큰을 다 쓴 이승찬":
            if forced or not any(c.card_type == "행동" for c in self.card_on_hand.cardList):
                discarded = self.discard_all_hand()
                reason = "조건 무시 발동" if forced else "행동카드가 없어"
                self.effect_log(card, f"{reason} 손패 {discarded}장을 모두 버립니다.")
                return True
            return False

        if name == "9와 4분의3 승강장":
            if forced or len(self.card_on_hand.cardList) == 9:
                if remove_when_used:
                    self.discard_card(card)
                discarded = self.discard_random_cards(3, exclude_cards=[] if remove_when_used else [card])
                reason = "조건 무시 발동. " if forced else ""
                self.effect_log(card, f"{reason}카드 {discarded}장을 버리고 4장을 뽑습니다.")
                self.draw_card_from_dummy(4)
                return True
            return False

        if name == "당신은 묵비권을 행사할 수 있으며":
            self.effect_log(card, "다음에 사용하는 행동카드 효과를 1회 무시합니다.")
            return True

        if name == "악마의 숫자":
            if forced or len(self.card_on_hand.cardList) == 6:
                discarded = self.discard_all_hand()
                reason = "조건 무시 발동" if forced else "손패가 6장이 되어"
                self.effect_log(card, f"{reason} 카드 {discarded}장을 모두 버립니다.")
                return True
            return False

        if name == "설":
            if forced or any(c.name == "우진" for c in self.card_on_hand.cardList):
                if remove_when_used:
                    self.discard_card(card)
                reason = "조건 무시 발동으로" if forced else "우진 카드가 있어서"
                self.effect_log(card, f"{reason} 카드 3장을 뽑습니다.")
                self.draw_card_from_dummy(3)
                return True
            return False

        if name == "정":
            if forced or any(c.name == "우진" for c in self.card_on_hand.cardList):
                if remove_when_used:
                    self.discard_card(card)
                reason = "조건 무시 발동으로" if forced else "우진 카드가 있어서"
                self.effect_log(card, f"{reason} 카드 1장을 뽑습니다.")
                self.draw_card_from_dummy(1)
                return True
            return False

        if name == "이":
            if forced or any(c.name == "우진" for c in self.card_on_hand.cardList):
                if remove_when_used:
                    self.discard_card(card)
                discarded = self.discard_random_cards(2, exclude_cards=[] if remove_when_used else [card])
                reason = "조건 무시 발동으로" if forced else "우진 카드가 있어서"
                self.effect_log(card, f"{reason} 카드 {discarded}장을 버립니다.")
                return True
            return False

        if name == "히히 방구!":
            self.effect_log(card, "아무런 효과가 없습니다.")
            return True

        return False

    def check_reactive_traps(self):
        """카드 수 달성형이 아닌 조건형 함정만 즉시 확인한다.

        뽑기/버리기 연출은 나중에 재생되지만, 게임 로직상 카드가 얻어지거나
        버려진 순간 바로 반응해야 하는 함정들이 있다. 예를 들어 손패에 우진과
        설/정/이가 같이 있거나, 토큰을 다 쓴 이승찬 조건이 만족되는 경우다.

        반대로 6장/9장/12장처럼 '정확히 n장 달성'을 보는 함정은
        check_count_based_traps()에서만 처리한다. 이 함수에서는 절대 처리하지 않는다.
        """
        if self.game_state != "game" or self.passive_lock:
            return False

        fired_any = False
        self.passive_lock = True
        try:
            # 한 조건 처리로 다른 조건이 새로 만족될 수 있으므로 짧게 반복한다.
            for _ in range(30):
                fired = False

                # 호현이는 거북목 상태가 켜진 뒤 손패에 있으면 즉시 해제한다.
                healer = next((c for c in self.card_on_hand.cardList if c.name == "거북목 치료사 호현이"), None)
                if self.turtle_neck_active and healer:
                    self.queue_activation_effect(healer)
                    self.turtle_neck_active = False
                    self.turtle_neck_counter = 0
                    self.effect_log(healer, "손패에 호현이가 있어 거북목 디버프를 해제합니다.")
                    fired = True

                if fired:
                    fired_any = True
                    continue

                # 토큰을 다 쓴 이승찬은 '카드 수'가 아니라 행동카드 존재 여부 조건이므로 즉시 발동한다.
                token_trap = next((c for c in self.card_on_hand.cardList if c.name == "토큰을 다 쓴 이승찬"), None)
                if token_trap and not any(c.card_type == "행동" for c in self.card_on_hand.cardList):
                    if self.trigger_trap_card(token_trap, forced=False):
                        fired = True

                if fired:
                    fired_any = True
                    continue

                # 우진 조건 함정은 카드 수 달성이 아니므로 뽑기/버리기 중에도 즉시 발동한다.
                has_woojin = any(c.name == "우진" for c in self.card_on_hand.cardList)
                if has_woojin:
                    for trap_name in ["설", "정", "이"]:
                        trap = next((x for x in self.card_on_hand.cardList[:] if x.name == trap_name), None)
                        if trap and self.trigger_trap_card(trap, forced=False, remove_when_used=True):
                            fired = True
                            break

                if fired:
                    fired_any = True
                    continue

                break
        finally:
            self.passive_lock = False

        return fired_any

    def check_count_based_traps(self):
        """정확히 n장 달성 조건을 보는 함정만 확인한다.

        이 함수는 main.py에서 모든 연출 이벤트가 끝난 뒤 호출된다.
        따라서 뽑기/버리기 중간에 손패가 잠깐 6/9/12장이 되어도 바로 발동하지 않고,
        전체 효과 처리 후 최종 손패 수를 기준으로 판정한다.
        """
        if self.game_state != "game" or self.passive_lock:
            return False

        fired = False
        self.passive_lock = True
        try:
            cinderella = next((c for c in self.card_on_hand.cardList if c.name == "신데렐라는 아쉬워 벌써 12시"), None)
            if cinderella and len(self.card_on_hand.cardList) == 12:
                fired = self.trigger_trap_card(cinderella, forced=False, remove_when_used=False) or fired
                return fired

            devil_trap = next((c for c in self.card_on_hand.cardList if c.name == "악마의 숫자"), None)
            if devil_trap and len(self.card_on_hand.cardList) == 6:
                fired = self.trigger_trap_card(devil_trap, forced=False) or fired
                return fired

            platform_trap = next((c for c in self.card_on_hand.cardList if c.name == "9와 4분의3 승강장"), None)
            if platform_trap and len(self.card_on_hand.cardList) == 9:
                fired = self.trigger_trap_card(platform_trap, forced=False, remove_when_used=True) or fired
                return fired
        finally:
            self.passive_lock = False

        return fired

    def check_passive_traps(self):
        """프레임 단위 자동 함정 체크.

        main.py가 연출이 모두 끝난 시점에 호출한다.
        즉시 반응형 함정은 먼저 확인하고, 그 다음 n장 달성형 함정을 최종 손패 기준으로 확인한다.
        """
        if self.game_state != "game":
            return
        self.check_reactive_traps()
        self.check_count_based_traps()

    def tick_turn_counters(self):
        if self.turtle_neck_active:
            self.turtle_neck_counter -= 1
            if self.turtle_neck_counter <= 0:
                if self.mingi_project_turns > 0:
                    self.turtle_neck_active = False
                    self.turtle_neck_counter = 0
                    self.add_log("거북목 카운트 종료: 민기의 프로젝트로 손패 상실을 막았습니다.")
                else:
                    turtle_trap = next((c for c in self.card_on_hand.cardList if c.name == "대훈이의 거북목"), None)
                    self.queue_activation_effect(turtle_trap)
                    discarded = self.discard_all_hand()
                    self.effect_log(turtle_trap, f"5턴 안에 호현이를 찾지 못해 손패 {discarded}장을 모두 버립니다.")
                    self.turtle_neck_active = False
                    self.turtle_neck_counter = 0

        if self.mingi_project_turns > 0:
            self.mingi_project_turns -= 1

        if self.dog_bite_turns > 0:
            self.dog_bite_turns -= 1
            popped_card = self.card_on_hand.cardList[-1] if self.card_on_hand.cardList else None
            if popped_card and self.discard_card(popped_card):
                self.add_log(f"상처 지속 효과: 가장 최근에 얻은 카드 1장을 버립니다. 남은 지속 {self.dog_bite_turns}회")

import pygame
import random
import datetime
from constants import CARD_POOL
from models import Card, CardDummy, CardOnHand, TrashCard

class GameManager:
    def __init__(self):
        self.game_state = "menu"
        self.score = 0
        self.total_actions = 0
        self.start_ticks = 0
        self.final_time = 0

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

    def add_log(self, msg):
        self.log_queue.append(msg)
        if len(self.log_queue) > 7: 
            self.log_queue.pop(0)

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
        self.log_queue = []
        self.start_ticks = pygame.time.get_ticks()

        self.card_dummy = CardDummy()
        self.card_on_hand = CardOnHand()
        self.trash_card = TrashCard()

        for _ in range(60): 
            self.card_dummy.push(Card(random.choice(CARD_POOL)))

        self.add_log("게임을 시작합니다! 목표는 정확히 7장 맞추기.")
        for _ in range(3):  
            self.raw_draw_logic()

        self.game_state = "game"

    def raw_draw_logic(self):
        if len(self.card_on_hand.cardList) >= 1000:
            return

        if self.card_dummy.isEmpty():
            if len(self.trash_card.cardList) == 0:
                for _ in range(30): 
                    self.card_dummy.push(Card(random.choice(CARD_POOL)))
            else:
                random.shuffle(self.trash_card.cardList)
                for c in self.trash_card.cardList: 
                    self.card_dummy.push(c)
                self.trash_card.cardList = []
                self.add_log("덱 소진으로 버린 더미를 섞어 채웠습니다.")

        new_card = self.card_dummy.pop()
        if not new_card: 
            return

        if new_card.card_type == "즉발":
            self.add_log(f"즉발 발동: [{new_card.name}]")
            self.trash_card.cardList.append(new_card)
            
            if new_card.name == "중간고사":
                for _ in range(3):
                    if self.card_on_hand.cardList: 
                        self.trash_card.cardList.append(self.card_on_hand.cardList.pop(random.randrange(len(self.card_on_hand.cardList))))
                self.add_log("무작위 카드 3장을 버렸습니다.")
            elif new_card.name == "현재 게임이 재밌나요?":
                count = random.randint(1, 3)
                for _ in range(count): 
                    self.raw_draw_logic()
            elif new_card.name == "거북목 치료사 호현이":
                if self.turtle_neck_active: 
                    self.turtle_neck_active = False
                    self.add_log("거북목 완치!")
            elif new_card.name == "민기의 프로젝트":
                self.mingi_project_turns = 3
            elif new_card.name == "도둑이야!":
                self.add_log("도둑 습격! 카드를 8장 유실합니다.")
                for _ in range(8):
                    if self.card_on_hand.cardList: 
                        self.trash_card.cardList.append(self.card_on_hand.cardList.pop(random.randrange(len(self.card_on_hand.cardList))))
            elif new_card.name == "임산부야!":
                self.raw_draw_logic()
            elif new_card.name == "깜짝이야!":
                actions = [c for c in self.card_on_hand.cardList if c.card_type == "행동"]
                self.add_log(f"깜짝 효과! 패의 행동카드 {len(actions)}장을 일제히 연쇄 작동합니다.")
                for act in actions:
                    if act in self.card_on_hand.cardList:
                        self.card_on_hand.cardList.remove(act)
                        self.trash_card.cardList.append(act)
                        self.execute_action_card(act)
            elif new_card.name == "크리퍼":
                kept = [c for c in self.card_on_hand.cardList if c.card_type == "함정"]
                self.trash_card.cardList.extend([c for c in self.card_on_hand.cardList if c.card_type != "함정"])
                self.card_on_hand.cardList = kept
                self.add_log("크리퍼 폭발! 함정 제외 올 디스카드!")
            elif new_card.name == "사지절단":
                kept = [c for c in self.card_on_hand.cardList if c.card_type != "행동"]
                self.trash_card.cardList.extend([c for c in self.card_on_hand.cardList if c.card_type == "행동"])
                self.card_on_hand.cardList = kept
                self.add_log("사지절단! 패의 모든 행동 카드를 버립니다.")
            elif new_card.name == "ADHD":
                self.add_log("ADHD 각성! 행동 카드가 나올 때까지 뽑아 즉시 전개합니다.")
                while True:
                    if self.card_dummy.isEmpty() and not self.trash_card.cardList: 
                        break
                    old_cnt = len(self.card_on_hand.cardList)
                    self.raw_draw_logic()
                    if len(self.card_on_hand.cardList) > old_cnt:
                        last_c = self.card_on_hand.cardList[-1]
                        if last_c.card_type == "행동":
                            self.card_on_hand.cardList.pop()
                            self.trash_card.cardList.append(last_c)
                            self.execute_action_card(last_c)
                            break
            elif new_card.name == "준민이의 퍼리박스":
                animals = ["대훈이의 거북목", "공룡 멸망 동윤 등장", "개한테 물렸어!", "아기상어"]
                targets = [c for c in self.card_on_hand.cardList if c.name in animals]
                self.add_log(f"퍼리박스 오픈! 동물 관련 카드 {len(targets)}개의 효과가 조건무시 폭발합니다.")
                for tc in targets:
                    if tc.card_type == "행동": 
                        self.execute_action_card(tc)
                    elif tc.name == "대훈이의 거북목": 
                        self.turtle_neck_active = True
                        self.turtle_neck_counter = 5
            elif new_card.name == "메카드 한장이면 충분해 파이널 어빌리티 스파크여 작렬하라 볼트 스파이크":
                self.add_log("파이널 어빌리티 스파크 작렬!! 모든 패를 소멸시킵니다.")
                while self.card_on_hand.cardList: 
                    self.trash_card.cardList.append(self.card_on_hand.cardList.pop())
        else:
            self.card_on_hand.cardList.append(new_card)
            
            if new_card.name == "대훈이의 거북목":
                self.turtle_neck_active = True
                self.turtle_neck_counter = 5
                self.add_log("거북목 저주 발동!")
            if new_card.name == "게임":
                if any(c.name == "그리다 만" for c in self.card_on_hand.cardList):
                    self.card_on_hand.cardList = [c for c in self.card_on_hand.cardList if c.name == "게임"]

    def draw_card_from_dummy(self):
        self.total_actions += 1
        self.raw_draw_logic()
        self.tick_turn_counters()

    def execute_action_card(self, card):
        if any(c.name == "당신은 묵비권을 행사할 수 있으며" for c in self.card_on_hand.cardList):
            silence = next(c for c in self.card_on_hand.cardList if c.name == "당신은 묵비권을 행사할 수 있으며")
            self.card_on_hand.cardList.remove(silence)
            self.trash_card.cardList.append(silence)
            self.add_log(f"함정 [묵비권] 발동: {card.name}의 효과가 차단당했습니다.")
            return

        self.add_log(f"카드 사용: {card.name}")
        
        if card.name == "게임":
            for _ in range(3): 
                self.raw_draw_logic()
        elif card.name == "소리 질러" or card.name == "하루하루":
            for _ in range(2): 
                self.raw_draw_logic()
        elif card.name == "밥 먹을 시간이다":
            for _ in range(len(self.card_on_hand.cardList) * 2): 
                self.raw_draw_logic()
        elif card.name == "빛 빛 빛":
            if random.random() < 0.5:
                for _ in range(4): 
                    self.raw_draw_logic()
            else:
                for _ in range(3):
                    if self.card_on_hand.cardList: 
                        self.trash_card.cardList.append(self.card_on_hand.cardList.pop())
        elif card.name == "준민이는 씨리얼 1짱":
            if self.last_played_card_name == "집 나간 승찬이":
                while len(self.card_on_hand.cardList) > 6: 
                    self.trash_card.cardList.append(self.card_on_hand.cardList.pop())
                while len(self.card_on_hand.cardList) < 6: 
                    self.raw_draw_logic()
        elif card.name == "집 나간 승찬이":
            for _ in range(15): 
                self.raw_draw_logic()
        elif card.name == "윤규는 숫돌이":
            for _ in range(5):
                if self.card_on_hand.cardList: 
                    self.trash_card.cardList.append(self.card_on_hand.cardList.pop())
        elif card.name == "공룡 멸망 동윤 등장":
            curr = len(self.card_on_hand.cardList)
            self.trash_card.cardList.extend(self.card_on_hand.cardList)
            self.card_on_hand.cardList = []
            for _ in range(curr): 
                self.raw_draw_logic()
        elif card.name == "어떻게 토큰이 1억개야?" or card.name == "무명 카드":
            for _ in range(100): 
                self.raw_draw_logic()
        elif card.name == "나는야 환경지킴이":
            if self.trash_card.cardList: 
                self.card_on_hand.cardList.append(self.trash_card.cardList.pop())
        elif card.name == "윤규의 축복":
            for _ in range(4):
                if self.card_on_hand.cardList: 
                    self.trash_card.cardList.append(self.card_on_hand.cardList.pop(random.randrange(len(self.card_on_hand.cardList))))
        elif card.name == "지금 몇시지?":
            hr = datetime.datetime.now().hour
            if hr == 0: 
                hr = 12
            self.add_log(f"현재 시각 연동 ({hr}시) -> {hr}장 뽑습니다.")
            for _ in range(hr): 
                self.raw_draw_logic()
        elif card.name == "뽑으세요!":
            for _ in range(random.randint(2, 5)): 
                self.raw_draw_logic()
        elif card.name == "저는 이승찬입니다":
            self.card_on_hand.cardList = [c for c in self.card_on_hand.cardList if c.name != "거북목 치료사 호현이"]
            self.card_dummy.cardList = [c for c in self.card_dummy.cardList if c.name != "거북목 치료사 호현이"]
            self.trash_card.cardList = [c for c in self.trash_card.cardList if c.name != "거북목 치료사 호현이"]
            self.add_log("호현이 카드가 차원에서 추방되었습니다.")
        elif card.name == "개한테 물렸어!":
            self.dog_bite_turns = 3
        elif card.name == "변신이다!":
            cnt = len(self.card_on_hand.cardList)
            self.trash_card.cardList.extend(self.card_on_hand.cardList)
            self.card_on_hand.cardList = []
            for _ in range(cnt): 
                self.raw_draw_logic()
        elif card.name == "지뢰해체전문가":
            traps = [c for c in self.card_on_hand.cardList if c.card_type == "함정"]
            if traps: 
                self.card_on_hand.cardList.remove(traps[0])
                self.trash_card.cardList.append(traps[0])
        elif card.name == "아기상어":
            for _ in range(35): 
                self.raw_draw_logic()
        elif card.name == "종이접기":
            for _ in range(len(self.card_on_hand.cardList) // 2):
                if self.card_on_hand.cardList: 
                    self.trash_card.cardList.append(self.card_on_hand.cardList.pop(random.randrange(len(self.card_on_hand.cardList))))
        elif card.name == "퉤":
            if self.card_on_hand.cardList: 
                self.trash_card.cardList.append(self.card_on_hand.cardList.pop(random.randrange(len(self.card_on_hand.cardList))))
        elif card.name == "마우가 정신":
            while True:
                if self.card_dummy.isEmpty() and not self.trash_card.cardList: 
                    break
                old_len = len(self.card_on_hand.cardList)
                self.raw_draw_logic()
                if len(self.card_on_hand.cardList) > old_len and self.card_on_hand.cardList[-1].card_type == "함정":
                    break
        elif card.name == "이승찬의 신음소리":
            for _ in range(random.randint(2, 8)):
                if self.card_on_hand.cardList: 
                    self.trash_card.cardList.append(self.card_on_hand.cardList.pop(random.randrange(len(self.card_on_hand.cardList))))
        elif card.name == "난 이제 부자야":
            while len(self.card_on_hand.cardList) < 20:
                if self.card_dummy.isEmpty() and not self.trash_card.cardList: 
                    break
                self.raw_draw_logic()
        elif card.name == "우진":
            names_2_5 = ["준민", "승찬", "윤규", "동윤", "민기", "대훈", "호현", "우진"]
            kept = []
            for c in self.card_on_hand.cardList:
                if any(n in c.name for n in names_2_5): 
                    self.trash_card.cardList.append(c)
                else: 
                    kept.append(c)
            self.card_on_hand.cardList = kept

        self.last_played_card_name = card.name
        self.tick_turn_counters()

    def check_passive_traps(self):
        if self.game_state != "game": 
            return
        
        has_action = any(c.card_type == "행동" for c in self.card_on_hand.cardList)
        has_woojin = any(c.name == "우진" for c in self.card_on_hand.cardList)
        h_len = len(self.card_on_hand.cardList)

        # 1. 토큰을 다 쓴 이승찬
        if any(c.name == "토큰을 다 쓴 이승찬" for c in self.card_on_hand.cardList) and not has_action:
            self.add_log("[토큰을 다 쓴 이승찬] 발동! 행동 카드가 없어 올 디스카드!")
            while self.card_on_hand.cardList: 
                self.trash_card.cardList.append(self.card_on_hand.cardList.pop())
            return

        # 2. 악마의 숫자???
        if any(c.name == "악마의 숫자???" for c in self.card_on_hand.cardList) and h_len == 6:
            self.add_log("[악마의 숫자???] 조건 충족! 모든 패를 버립니다.")
            while self.card_on_hand.cardList: 
                self.trash_card.cardList.append(self.card_on_hand.cardList.pop())
            return

        # 3. 9 ¾ 승강장
        if any(c.name == "9 ¾ 승강장" for c in self.card_on_hand.cardList) and h_len == 9:
            self.add_log("[9 ¾ 승강장] 충돌! 3장 유실 후 4장 드로우합니다.")
            for _ in range(3):
                if self.card_on_hand.cardList: 
                    self.trash_card.cardList.append(self.card_on_hand.cardList.pop(random.randrange(len(self.card_on_hand.cardList))))
            for _ in range(4): 
                self.raw_draw_logic()

        # 4. 우진 연계 트리오 (설, 정, 이)
        if has_woojin:
            for c in [x for x in self.card_on_hand.cardList if x.name == "설"]:
                self.card_on_hand.cardList.remove(c)
                self.trash_card.cardList.append(c)
                self.add_log("[설] 발동 (+3장)")
                for _ in range(3):
                    self.raw_draw_logic()
                    
            for c in [x for x in self.card_on_hand.cardList if x.name == "정"]:
                self.card_on_hand.cardList.remove(c)
                self.trash_card.cardList.append(c)
                self.add_log("[정] 발동 (+1장)")
                self.raw_draw_logic()
                
            for c in [x for x in self.card_on_hand.cardList if x.name == "이"]:
                self.card_on_hand.cardList.remove(c)
                self.trash_card.cardList.append(c)
                self.add_log("[이] 발동 (-2장)")
                for _ in range(2):
                    if self.card_on_hand.cardList: 
                        self.trash_card.cardList.append(self.card_on_hand.cardList.pop(random.randrange(len(self.card_on_hand.cardList))))

    def tick_turn_counters(self):
        if self.turtle_neck_active:
            self.turtle_neck_counter -= 1
            if self.turtle_neck_counter <= 0:
                if self.mingi_project_turns > 0: 
                    self.turtle_neck_active = False
                else:
                    self.add_log("거북목 말기 현상! 모든 패를 버립니다.")
                    self.card_on_hand.cardList = []
                    self.turtle_neck_active = False

        if self.mingi_project_turns > 0: 
            self.mingi_project_turns -= 1
        
        if self.dog_bite_turns > 0:
            self.dog_bite_turns -= 1
            if self.card_on_hand.cardList:
                self.trash_card.cardList.append(self.card_on_hand.cardList.pop(random.randrange(len(self.card_on_hand.cardList))))
                self.add_log(f"댕댕이 상처 도짐! 카드 1장 자동 소실 (남은 지속: {self.dog_bite_turns}회)")
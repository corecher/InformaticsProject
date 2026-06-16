import pygame
import random
import sys
import datetime

pygame.init()

# =========================
# 설정 및 상수
# =========================
WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("준민이의 디스크 - 통합 안정화 버전")

font = pygame.font.SysFont("malgungothic", 25)
big_font = pygame.font.SysFont("malgungothic", 60)
log_font = pygame.font.SysFont("malgungothic", 13)

WHITE = (240, 240, 240)
GRAY = (200, 200, 200)
DARK = (50, 50, 50)
BLUE = (70, 130, 180)
RED = (220, 20, 60)
GREEN = (46, 139, 87)

HAND_X = 265
HAND_Y = 460

# =========================
# 카드 데이터 풀 정의
# =========================
CARD_POOL = [
    # 기존 원본 카드 리스트
    {"name": "그리다 만", "type": "함정", "desc": "'게임' 카드 획득 시 모든 타 카드 버림"},
    {"name": "게임", "type": "행동", "desc": "카드 3장을 얻는다"},
    {"name": "소리 질러", "type": "행동", "desc": "카드를 2장 얻는다"},
    {"name": "신데렐らは 아쉬워 벌써 12시", "type": "함정", "desc": "카드 수가 12개가 되면 즉시 승리"},
    {"name": "중간고사", "type": "즉발", "desc": "카드를 3장 버립니다"},
    {"name": "밥 먹을 시간이다", "type": "행동", "desc": "현재 카드 수의 2배를 추가 획득"},
    {"name": "하루하루", "type": "행동", "desc": "두장을 얻습니다"},
    {"name": "빛 빛 빛", "type": "행동", "desc": "50% 확률로 4장 획득 혹은 3장 상실"},
    {"name": "현재 게임이 재밌나요?", "type": "즉발", "desc": "재미 체크 피드백 후 1~3장 랜덤 획득"},
    {"name": "준민이는 씨리얼 1짱", "type": "행동", "desc": "'집나간 승찬' 후 사용 시 카드를 6장으로 맞춤"},
    {"name": "집 나간 승찬이", "type": "행동", "desc": "15장의 카드를 얻습니다"},
    {"name": "대훈이의 거북목", "type": "함정", "desc": "5턴 안에 '호현' 못 얻으면 모든 카드 상실"},
    {"name": "거북목 치료사 호현이", "type": "즉발", "desc": "저는 호현이 입니다 (거북목 디버프 해제)"},
    {"name": "윤규는 숫돌이", "type": "행동", "desc": "윤규의 실수로 카드 5장을 버립니다"},
    {"name": "공룡 멸망 동윤 등장", "type": "행동", "desc": "모든 카드를 버리고 그만큼 새로 획득"},
    {"name": "민기의 프로젝트", "type": "즉발", "desc": "3턴 동안 게임종료 조건이 면제됨"},
    {"name": "어떻게 토큰이 1억개야?", "type": "행동", "desc": "100개의 카드를 대량 획득"},
    {"name": "무명 카드", "type": "행동", "desc": "100개의 카드를 대량 획득"},

    # [image_57b7a1.jpg] 추가 카드 데이터 리스트
    {"name": "나는야 환경지킴이", "type": "행동", "desc": "버린더미의 맨 위 카드를 가져온다"},
    {"name": "윤규의 축복", "type": "행동", "desc": "윤규의 축복을 거부하고 카드를 4장 버립니다"},
    {"name": "도둑이야!", "type": "즉발", "desc": "카드를 8장 버린다"},
    {"name": "지금 몇시지?", "type": "행동", "desc": "현재 시각만큼 카드를 뽑습니다 (시 기준)"},
    {"name": "토큰을 다 쓴 이승찬", "type": "함정", "desc": "손에 행동카드가 없다면 모든 카드를 버립니다"},
    {"name": "뽑으세요!", "type": "행동", "desc": "N장 뽑는다 (랜덤 2~5장)"},
    {"name": "임산부야!", "type": "즉발", "desc": "카드를 한장 더 뽑는다"},
    {"name": "9 ¾ 승강장", "type": "함정", "desc": "카드가 9장이 되면 3장 버리고 4장 뽑는다"},
    {"name": "저는 이승찬입니다", "type": "행동", "desc": "'거북목 치료사 호현이' 카드를 게임에서 제거합니다"},
    {"name": "개한테 물렸어!", "type": "행동", "desc": "3턴동안 매 턴 1장씩 버립니다"},
    {"name": "변신이다!", "type": "행동", "desc": "손에 든 카드를 모두 버리고 들고 있던 수만큼 새로 뽑습니다"},
    {"name": "당신은 묵비권을 행사할 수 있으며", "type": "함정", "desc": "행동카드를 사용할 때 해당 행동카드의 효과를 무시합니다"},
    {"name": "깜짝이야!", "type": "즉발", "desc": "손에 든 모든 행동카드를 즉시 사용합니다"},
    {"name": "크리퍼", "type": "즉발", "desc": "손에 든 함정카드를 제외한 모든 카드를 버립니다"},
    {"name": "사지절단", "type": "즉발", "desc": "손에 든 모든 행동카드를 버립니다"},
    {"name": "지뢰해체전문가", "type": "행동", "desc": "손에 든 함정카드 한 장을 버립니다"},
    {"name": "ADHD", "type": "즉발", "desc": "행동카드를 뽑을때까지 계속 카드를 뽑아 손에 들고 즉시 사용합니다"},
    {"name": "아기상어", "type": "행동", "desc": "뮤비 조회수만큼 폭발적인 양(35장)의 카드를 뽑습니다"},
    {"name": "종이접기", "type": "행동", "desc": "손에 든 카드의 절반을 버립니다"},
    {"name": "퉤", "type": "행동", "desc": "카드 1장을 버립니다"},
    {"name": "마우가 정신", "type": "행동", "desc": "함정카드를 뽑을때까지 계속 뽑아 조건 무시 즉시 발동"},
    {"name": "준민이의 퍼리박스", "type": "즉발", "desc": "손에 든 동물 이름 카드들의 효과가 조건 없이 즉시 발동"},
    {"name": "히히 똥!", "type": "행동", "desc": "아무런 효과가 없습니다"},
    {"name": "악마의 숫자???", "type": "함정", "desc": "손에 든 카드가 6장이 되면 손에 든 카드를 모두 버립니다"},
    {"name": "설", "type": "함정", "desc": "만약 손에 '우진' 카드가 있다면 3장 뽑습니다"},
    {"name": "이승찬의 신음소리", "type": "행동", "desc": "승찬이의 신음 데시벨만큼 카드를 버립니다"},
    {"name": "히히 방구!", "type": "함정", "desc": "아무런 효과가 없습니다"},
    {"name": "난 이제 부자야", "type": "행동", "desc": "손에 든 카드가 20장이 될때까지 계속 뽑습니다"},
    {"name": "정", "type": "함정", "desc": "만약 손에 '우진' 카드가 있다면 1장 뽑습니다"},
    {"name": "히히 오줌!", "type": "즉발", "desc": "아무런 효과가 없습니다"},
    {"name": "우진", "type": "행동", "desc": "2-5반 학생의 이름이 들어간 모든 카드를 버립니다"},
    {"name": "이", "type": "함정", "desc": "만약 손에 '우진' 카드가 있다면 2장 버립니다"},
    {"name": "메카드 한장이면 충분해 파이널 어빌리티 스파크여 작렬하라 볼트 스파이크", "type": "즉발", "desc": "이 카드 1장만 남기고 모든 카드를 버립니다"}
]

# =========================
# 클래스 설계
# =========================
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
            
        self.rect = pygame.Rect(0, 0, 75, 100)
        self.dragging = False
        self.offset_x = 0
        self.offset_y = 0

    def draw(self, screen, x, y):
        if not self.dragging:
            self.rect.x = x
            self.rect.y = y
            
        pygame.draw.rect(screen, self.color, self.rect, border_radius=6)
        pygame.draw.rect(screen, DARK, self.rect, 2, border_radius=6)
        
        c_font = pygame.font.SysFont("malgungothic", 10, bold=True)
        t_font = pygame.font.SysFont("malgungothic", 8)
        d_font = pygame.font.SysFont("malgungothic", 7)
        
        disp_name = self.name if len(self.name) <= 7 else self.name[:6] + ".."
        screen.blit(c_font.render(disp_name, True, DARK), (self.rect.x + 4, self.rect.y + 5))
        screen.blit(t_font.render(f"[{self.card_type}]", True, (80, 80, 80)), (self.rect.x + 4, self.rect.y + 22))
        
        words = self.desc.split()
        lines = []
        curr_line = ""
        for w in words:
            if d_font.size(curr_line + w)[0] < 68:
                curr_line += w + " "
            else:
                lines.append(curr_line)
                curr_line = w + " "
        if curr_line: 
            lines.append(curr_line)
        
        for idx, line in enumerate(lines[:5]):
            screen.blit(d_font.render(line.strip(), True, DARK), (self.rect.x + 4, self.rect.y + 36 + idx * 11))

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

# =========================
# 게임 전역 상태 변수
# =========================
game_state = "menu"
score = 0
total_actions = 0
start_ticks = 0
final_time = 0

card_dummy = CardDummy()
card_on_hand = CardOnHand()
trash_card = TrashCard()

drag_card = None
scroll_index = 0  
show_preview = False

last_played_card_name = ""
turtle_neck_active = False
turtle_neck_counter = 0
mingi_project_turns = 0
dog_bite_turns = 0
log_queue = []

def add_log(msg):
    global log_queue
    log_queue.append(msg)
    if len(log_queue) > 7: 
        log_queue.pop(0)

start_button = pygame.Rect(450, 300, 300, 80)
exit_button = pygame.Rect(450, 410, 300, 80)
restart_button = pygame.Rect(450, 450, 300, 80)
draw_pile_rect = pygame.Rect(380, 100, 130, 180)
preview_button_rect = pygame.Rect(380, 300, 130, 40)
play_zone_rect = pygame.Rect(650, 100, 160, 220)
quit_game_button = pygame.Rect(50, 420, 250, 50)

clock = pygame.time.Clock()

def start_game():
    global score, total_actions, start_ticks, game_state, scroll_index, drag_card, show_preview
    global card_dummy, card_on_hand, trash_card, last_played_card_name, turtle_neck_active, turtle_neck_counter, mingi_project_turns, dog_bite_turns, log_queue

    score = 0
    total_actions = 0
    scroll_index = 0
    drag_card = None
    show_preview = False
    last_played_card_name = ""
    turtle_neck_active = False
    turtle_neck_counter = 0
    mingi_project_turns = 0
    dog_bite_turns = 0
    log_queue = []
    start_ticks = pygame.time.get_ticks()

    card_dummy = CardDummy()
    card_on_hand = CardOnHand()
    trash_card = TrashCard()

    for _ in range(60): 
        card_dummy.push(Card(random.choice(CARD_POOL)))

    add_log("게임을 시작합니다! 목표는 정확히 7장 맞추기.")
    for _ in range(3):  
        raw_draw_logic()

    game_state = "game"

def raw_draw_logic():
    global turtle_neck_active, turtle_neck_counter, mingi_project_turns
    
    if len(card_on_hand.cardList) >= 1000:
        return

    if card_dummy.isEmpty():
        if len(trash_card.cardList) == 0:
            for _ in range(30): 
                card_dummy.push(Card(random.choice(CARD_POOL)))
        else:
            random.shuffle(trash_card.cardList)
            for c in trash_card.cardList: 
                card_dummy.push(c)
            trash_card.cardList = []
            add_log("덱 소진으로 버린 더미를 섞어 채웠습니다.")

    new_card = card_dummy.pop()
    if not new_card: 
        return

    if new_card.card_type == "즉발":
        add_log(f"즉발 발동: [{new_card.name}]")
        trash_card.cardList.append(new_card)
        
        if new_card.name == "중간고사":
            for _ in range(3):
                if card_on_hand.cardList: 
                    trash_card.cardList.append(card_on_hand.cardList.pop(random.randrange(len(card_on_hand.cardList))))
            add_log("무작위 카드 3장을 버렸습니다.")
        elif new_card.name == "현재 게임이 재밌나요?":
            count = random.randint(1, 3)
            for _ in range(count): 
                raw_draw_logic()
        elif new_card.name == "거북목 치료사 호현이":
            if turtle_neck_active: 
                turtle_neck_active = False
                add_log("거북목 완치!")
        elif new_card.name == "민기의 프로젝트":
            mingi_project_turns = 3
        elif new_card.name == "도둑이야!":
            add_log("도둑 습격! 카드를 8장 유실합니다.")
            for _ in range(8):
                if card_on_hand.cardList: 
                    trash_card.cardList.append(card_on_hand.cardList.pop(random.randrange(len(card_on_hand.cardList))))
        elif new_card.name == "임산부야!":
            raw_draw_logic()
        elif new_card.name == "깜짝이야!":
            actions = [c for c in card_on_hand.cardList if c.card_type == "행동"]
            add_log(f"깜짝 효과! 패의 행동카드 {len(actions)}장을 일제히 연쇄 작동합니다.")
            for act in actions:
                if act in card_on_hand.cardList:
                    card_on_hand.cardList.remove(act)
                    trash_card.cardList.append(act)
                    execute_action_card(act)
        elif new_card.name == "크리퍼":
            kept = [c for c in card_on_hand.cardList if c.card_type == "함정"]
            trash_card.cardList.extend([c for c in card_on_hand.cardList if c.card_type != "함정"])
            card_on_hand.cardList = kept
            add_log("크리퍼 폭발! 함정 제외 올 디스카드!")
        elif new_card.name == "사지절단":
            kept = [c for c in card_on_hand.cardList if c.card_type != "행동"]
            trash_card.cardList.extend([c for c in card_on_hand.cardList if c.card_type == "행동"])
            card_on_hand.cardList = kept
            add_log("사지절단! 패의 모든 행동 카드를 버립니다.")
        elif new_card.name == "ADHD":
            add_log("ADHD 각성! 행동 카드가 나올 때까지 뽑아 즉시 전개합니다.")
            while True:
                if card_dummy.isEmpty() and not trash_card.cardList: 
                    break
                old_cnt = len(card_on_hand.cardList)
                raw_draw_logic()
                if len(card_on_hand.cardList) > old_cnt:
                    last_c = card_on_hand.cardList[-1]
                    if last_c.card_type == "행동":
                        card_on_hand.cardList.pop()
                        trash_card.cardList.append(last_c)
                        execute_action_card(last_c)
                        break
        elif new_card.name == "준민이의 퍼리박스":
            animals = ["대훈이의 거북목", "공룡 멸망 동윤 등장", "개한테 물렸어!", "아기상어"]
            targets = [c for c in card_on_hand.cardList if c.name in animals]
            add_log(f"퍼리박스 오픈! 동물 관련 카드 {len(targets)}개의 효과가 조건무시 폭발합니다.")
            for tc in targets:
                if tc.card_type == "행동": 
                    execute_action_card(tc)
                elif tc.name == "대훈이의 거북목": 
                    turtle_neck_active = True
                    turtle_neck_counter = 5
        elif new_card.name == "메카드 한장이면 충분해 파이널 어빌리티 스파크여 작렬하라 볼트 스파이크":
            add_log("파이널 어빌리티 스파크 작렬!! 모든 패를 소멸시킵니다.")
            while card_on_hand.cardList: 
                trash_card.cardList.append(card_on_hand.cardList.pop())
    else:
        card_on_hand.cardList.append(new_card)
        
        if new_card.name == "대훈이의 거북목":
            turtle_neck_active = True
            turtle_neck_counter = 5
            add_log("거북목 저주 발동!")
        if new_card.name == "게임":
            if any(c.name == "그리다 만" for c in card_on_hand.cardList):
                card_on_hand.cardList = [c for c in card_on_hand.cardList if c.name == "게임"]

def draw_card_from_dummy():
    global total_actions
    total_actions += 1
    raw_draw_logic()
    tick_turn_counters()

def execute_action_card(card):
    global last_played_card_name, dog_bite_turns
    
    if any(c.name == "당신은 묵비권을 행사할 수 있으며" for c in card_on_hand.cardList):
        silence = next(c for c in card_on_hand.cardList if c.name == "당신은 묵비권을 행사할 수 있으며")
        card_on_hand.cardList.remove(silence)
        trash_card.cardList.append(silence)
        add_log(f"함정 [묵비권] 발동: {card.name}의 효과가 차단당했습니다.")
        return

    add_log(f"카드 사용: {card.name}")
    
    if card.name == "게임":
        for _ in range(3): 
            raw_draw_logic()
    elif card.name == "소리 질러" or card.name == "하루하루":
        for _ in range(2): 
            raw_draw_logic()
    elif card.name == "밥 먹을 시간이다":
        for _ in range(len(card_on_hand.cardList) * 2): 
            raw_draw_logic()
    elif card.name == "빛 빛 빛":
        if random.random() < 0.5:
            for _ in range(4): 
                raw_draw_logic()
        else:
            for _ in range(3):
                if card_on_hand.cardList: 
                    trash_card.cardList.append(card_on_hand.cardList.pop())
    elif card.name == "준민이는 씨리얼 1짱":
        if last_played_card_name == "집 나간 승찬이":
            while len(card_on_hand.cardList) > 6: 
                trash_card.cardList.append(card_on_hand.cardList.pop())
            while len(card_on_hand.cardList) < 6: 
                raw_draw_logic()
    elif card.name == "집 나간 승찬이":
        for _ in range(15): 
            raw_draw_logic()
    elif card.name == "윤규는 숫돌이":
        for _ in range(5):
            if card_on_hand.cardList: 
                trash_card.cardList.append(card_on_hand.cardList.pop())
    elif card.name == "공룡 멸망 동윤 등장":
        curr = len(card_on_hand.cardList)
        trash_card.cardList.extend(card_on_hand.cardList)
        card_on_hand.cardList = []
        for _ in range(curr): 
            raw_draw_logic()
    elif card.name == "어떻게 토큰이 1억개야?" or card.name == "무명 카드":
        for _ in range(100): 
            raw_draw_logic()
    elif card.name == "나는야 환경지킴이":
        if trash_card.cardList:
            trash_card.cardList.pop()
            card_on_hand.cardList.append(trash_card.cardList.pop())
    elif card.name == "윤규의 축복":
        for _ in range(4):
            if card_on_hand.cardList: 
                trash_card.cardList.append(card_on_hand.cardList.pop(random.randrange(len(card_on_hand.cardList))))
    elif card.name == "지금 몇시지?":
        hr = datetime.datetime.now().hour
        if hr == 0: 
            hr = 12
        add_log(f"현재 시각 연동 ({hr}시) -> {hr}장 뽑습니다.")
        for _ in range(hr): 
            raw_draw_logic()
    elif card.name == "뽑으세요!":
        for _ in range(random.randint(2, 5)): 
            raw_draw_logic()
    elif card.name == "저는 이승찬입니다":
        card_on_hand.cardList = [c for c in card_on_hand.cardList if c.name != "거북목 치료사 호현이"]
        card_dummy.cardList = [c for c in card_dummy.cardList if c.name != "거북목 치료사 호현이"]
        trash_card.cardList = [c for c in trash_card.cardList if c.name != "거북목 치료사 호현이"]
        add_log("호현이 카드가 차원에서 추방되었습니다.")
    elif card.name == "개한테 물렸어!":
        dog_bite_turns = 3
    elif card.name == "변신이다!":
        cnt = len(card_on_hand.cardList)
        trash_card.cardList.extend(card_on_hand.cardList)
        card_on_hand.cardList = []
        for _ in range(cnt): 
            raw_draw_logic()
    elif card.name == "지뢰해체전문가":
        traps = [c for c in card_on_hand.cardList if c.card_type == "함정"]
        if traps: 
            card_on_hand.cardList.remove(traps[0])
            trash_card.cardList.append(traps[0])
    elif card.name == "아기상어":
        for _ in range(35): 
            raw_draw_logic()
    elif card.name == "종이접기":
        for _ in range(len(card_on_hand.cardList) // 2):
            if card_on_hand.cardList: 
                trash_card.cardList.append(card_on_hand.cardList.pop(random.randrange(len(card_on_hand.cardList))))
    elif card.name == "퉤":
        if card_on_hand.cardList: 
            trash_card.cardList.append(card_on_hand.cardList.pop(random.randrange(len(card_on_hand.cardList))))
    elif card.name == "마우가 정신":
        while True:
            if card_dummy.isEmpty() and not trash_card.cardList: 
                break
            old_len = len(card_on_hand.cardList)
            raw_draw_logic()
            if len(card_on_hand.cardList) > old_len and card_on_hand.cardList[-1].card_type == "함정":
                break
    elif card.name == "이승찬의 신음소리":
        for _ in range(random.randint(2, 8)):
            if card_on_hand.cardList: 
                trash_card.cardList.append(card_on_hand.cardList.pop(random.randrange(len(card_on_hand.cardList))))
    elif card.name == "난 이제 부자야":
        while len(card_on_hand.cardList) < 20:
            if card_dummy.isEmpty() and not trash_card.cardList: 
                break
            raw_draw_logic()
    elif card.name == "우진":
        names_2_5 = ["준민", "승찬", "윤규", "동윤", "민기", "대훈", "호현", "우진"]
        kept = []
        for c in card_on_hand.cardList:
            if any(n in c.name for n in names_2_5): 
                trash_card.cardList.append(c)
            else: 
                kept.append(c)
        card_on_hand.cardList = kept

    last_played_card_name = card.name
    tick_turn_counters()

# --- [패시브 실시간 모니터링 함정 함수] ---
def check_passive_traps():
    if game_state != "game": 
        return
    
    has_action = any(c.card_type == "행동" for c in card_on_hand.cardList)
    has_woojin = any(c.name == "우진" for c in card_on_hand.cardList)
    h_len = len(card_on_hand.cardList)

    # 1. 토큰을 다 쓴 이승찬
    if any(c.name == "토큰을 다 쓴 이승찬" for c in card_on_hand.cardList) and not has_action:
        add_log("[토큰을 다 쓴 이승찬] 발동! 행동 카드가 없어 올 디스카드!")
        while card_on_hand.cardList: 
            trash_card.cardList.append(card_on_hand.cardList.pop())
        return

    # 2. 악마의 숫자???
    if any(c.name == "악마의 숫자???" for c in card_on_hand.cardList) and h_len == 6:
        add_log("[악마의 숫자???] 조건 충족! 모든 패를 버립니다.")
        while card_on_hand.cardList: 
            trash_card.cardList.append(card_on_hand.cardList.pop())
        return

    # 3. 9 ¾ 승강장
    if any(c.name == "9 ¾ 승강장" for c in card_on_hand.cardList) and h_len == 9:
        add_log("[9 ¾ 승강장] 충돌! 3장 유실 후 4장 드로우합니다.")
        for _ in range(3):
            if card_on_hand.cardList: 
                trash_card.cardList.append(card_on_hand.cardList.pop(random.randrange(len(card_on_hand.cardList))))
        for _ in range(4): 
            raw_draw_logic()

    # 4. 우진 연계 트리오 (설, 정, 이)
    if has_woojin:
        for c in [x for x in card_on_hand.cardList if x.name == "설"]:
            card_on_hand.cardList.remove(c)
            trash_card.cardList.append(c)
            add_log("[설] 발동 (+3장)")
            for _ in range(3):
                raw_draw_logic()
                
        for c in [x for x in card_on_hand.cardList if x.name == "정"]:
            card_on_hand.cardList.remove(c)
            trash_card.cardList.append(c)
            add_log("[정] 발동 (+1장)")
            raw_draw_logic()
            
        for c in [x for x in card_on_hand.cardList if x.name == "이"]:
            card_on_hand.cardList.remove(c)
            trash_card.cardList.append(c)
            add_log("[이] 발동 (-2장)")
            for _ in range(2):
                if card_on_hand.cardList: 
                    trash_card.cardList.append(card_on_hand.cardList.pop(random.randrange(len(card_on_hand.cardList))))

def tick_turn_counters():
    global turtle_neck_active, turtle_neck_counter, mingi_project_turns, dog_bite_turns
    
    if turtle_neck_active:
        turtle_neck_counter -= 1
        if turtle_neck_counter <= 0:
            if mingi_project_turns > 0: 
                turtle_neck_active = False
            else:
                add_log("거북목 말기 현상! 모든 패를 버립니다.")
                card_on_hand.cardList = []
                turtle_neck_active = False

    if mingi_project_turns > 0: 
        mingi_project_turns -= 1
    
    if dog_bite_turns > 0:
        dog_bite_turns -= 1
        if card_on_hand.cardList:
            trash_card.cardList.append(card_on_hand.cardList.pop(random.randrange(len(card_on_hand.cardList))))
            add_log(f"댕댕이 상처 도짐! 카드 1장 자동 소실 (남은 지속: {dog_bite_turns}회)")

# =========================
# 메인 루프 실행 및 UI 드로잉
# =========================
running = True
while running:
    screen.fill(WHITE)
    current_time_sec = 0
    if game_state == "game":
        current_time_sec = (pygame.time.get_ticks() - start_ticks) // 1000
        check_passive_traps()

    if game_state == "menu":
        title = big_font.render("JUNMIN'S DISK", True, DARK)
        screen.blit(title, (410, 160))
        pygame.draw.rect(screen, (120, 220, 120), start_button, border_radius=5)
        screen.blit(font.render("게임 시작", True, DARK), (540, 325))
        pygame.draw.rect(screen, (240, 128, 128), exit_button, border_radius=5)
        screen.blit(font.render("게임 종료", True, DARK), (540, 435))

    elif game_state == "game":
        pygame.draw.rect(screen, GRAY, (50, 50, 250, 350), border_radius=5)
        screen.blit(font.render(f"현재 카드 : {len(card_on_hand.cardList)} / 1000", True, DARK), (70, 125))
        screen.blit(font.render(f"목표 카드 : 7장 완료", True, GREEN if len(card_on_hand.cardList)==7 else DARK), (70, 175))
        screen.blit(font.render(f"행동 횟수 : {total_actions}", True, DARK), (70, 225))
        
        if turtle_neck_active: 
            screen.blit(font.render(f"거북목 카운트: {turtle_neck_counter}", True, RED), (70, 325))
        elif dog_bite_turns > 0: 
            screen.blit(font.render(f"상처 지속: {dog_bite_turns}턴", True, RED), (70, 325))

        pygame.draw.rect(screen, RED, quit_game_button, border_radius=5)
        screen.blit(font.render("중도 포기", True, WHITE), (120, 430))

        pygame.draw.rect(screen, BLUE, draw_pile_rect, border_radius=5)
        screen.blit(font.render("뽑기 더미", True, WHITE), (395, 160))
        screen.blit(font.render(f"({len(card_dummy.cardList)})", True, WHITE), (425, 200))

        pygame.draw.rect(screen, DARK, preview_button_rect, border_radius=5)
        screen.blit(font.render("다음 카드 보기", True, WHITE), (385, 307))

        if show_preview and not card_dummy.isEmpty():
            next_c = card_dummy.peek()
            pygame.draw.rect(screen, next_c.color, (380, 350, 130, 45), border_radius=5)
            screen.blit(log_font.render(f"이름: {next_c.name}", True, DARK), (385, 353))

        pygame.draw.rect(screen, (230, 230, 230), play_zone_rect, border_radius=5)
        screen.blit(font.render("카드 내기", True, DARK), (680, 190))

        pygame.draw.rect(screen, (245, 245, 245), (840, 100, 320, 220), border_radius=5)
        screen.blit(font.render("실시간 로그", True, DARK), (850, 105))
        for idx, log in enumerate(log_queue):
            screen.blit(log_font.render(log, True, (30, 30, 30)), (850, 142 + idx * 22))

        # 하단 대용량 카드 시트 (그리드뷰)
        pygame.draw.rect(screen, (220, 220, 220), (250, 450, 700, 220), border_radius=5)
        cards_per_row = 8  
        start_card_idx = scroll_index * cards_per_row
        visible_cards = card_on_hand.cardList[start_card_idx: start_card_idx + 16] 
        
        for idx, card in enumerate(visible_cards):
            row, col = idx // cards_per_row, idx % cards_per_row
            card.draw(screen, HAND_X + col * 85, HAND_Y + row * 105)

        if len(card_on_hand.cardList) > 0:
            total_rows = (len(card_on_hand.cardList) + 7) // cards_per_row
            screen.blit(font.render(f"행: {scroll_index + 1}/{max(1, total_rows)} ({len(card_on_hand.cardList)}장 보유)", True, DARK), (480, 642))

        # 승리 판정 루프
        if mingi_project_turns <= 0:
            if any(c.name == "신데렐라는 아쉬워 벌써 12시" for c in card_on_hand.cardList) and len(card_on_hand.cardList) == 12:
                final_time = current_time_sec
                game_state = "clear"
            elif len(card_on_hand.cardList) == 7:
                final_time = current_time_sec
                game_state = "clear"

    elif game_state == "clear":
        screen.blit(big_font.render("GAME CLEAR", True, GREEN), (430, 150))
        screen.blit(font.render(f"최종 행동 횟수 : {total_actions}회", True, DARK), (490, 320))
        pygame.draw.rect(screen, (120, 220, 120), restart_button, border_radius=5)
        screen.blit(font.render("다시 하기", True, DARK), (550, 475))

    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT: 
            running = False
        if game_state == "menu" and event.type == pygame.MOUSEBUTTONDOWN:
            if start_button.collidepoint(event.pos): 
                start_game()
            elif exit_button.collidepoint(event.pos): 
                running = False
        elif game_state == "game":
            if event.type == pygame.MOUSEBUTTONDOWN:
                if draw_pile_rect.collidepoint(event.pos): 
                    draw_card_from_dummy()
                elif preview_button_rect.collidepoint(event.pos):
                    show_preview = not show_preview
                    total_actions += 1
                    tick_turn_counters()
                elif quit_game_button.collidepoint(event.pos): 
                    game_state = "menu"
                else:
                    visible_cards = card_on_hand.cardList[scroll_index * 8: scroll_index * 8 + 16]
                    for card in reversed(visible_cards):
                        if card.rect.collidepoint(event.pos):
                            drag_card = card
                            card.dragging = True
                            card.offset_x = card.rect.x - event.pos[0]
                            card.offset_y = card.rect.y - event.pos[1]
                            break
            elif event.type == pygame.MOUSEMOTION and drag_card and drag_card.dragging:
                drag_card.rect.x = event.pos[0] + drag_card.offset_x
                drag_card.rect.y = event.pos[1] + drag_card.offset_y
            elif event.type == pygame.MOUSEBUTTONUP and drag_card:
                drag_card.dragging = False
                if play_zone_rect.colliderect(drag_card.rect) and drag_card in card_on_hand.cardList:
                    if drag_card.card_type == "함정": 
                        add_log("함정 카드는 낼 수 없습니다!")
                    else:
                        card_on_hand.cardList.remove(drag_card)
                        trash_card.cardList.append(drag_card)
                        score += 1
                        total_actions += 1
                        execute_action_card(drag_card)
                        scroll_index = min(scroll_index, max(0, ((len(card_on_hand.cardList) + 7) // 8) - 2))
                drag_card = None
            elif event.type == pygame.MOUSEWHEEL:
                scroll_index = max(0, min(scroll_index + (-1 if event.y > 0 else 1), max(0, ((len(card_on_hand.cardList) + 7) // 8) - 2)))
        elif game_state == "clear" and event.type == pygame.MOUSEBUTTONDOWN and restart_button.collidepoint(event.pos):
            start_game()

    clock.tick(60)

pygame.quit()
sys.exit()
import pygame
import os
from constants import DARK

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
            
        # 1. [변경] 정사각형 이미지(130x130) 공간 확보를 위해 카드 높이 연장 (150x200 -> 150x240)
        self.rect = pygame.Rect(0, 0, 150, 240)
        self.dragging = False
        self.offset_x = 0
        self.offset_y = 0

        self.image = None
        img_path = os.path.join("images", f"{self.name}.png")
        
        if os.path.exists(img_path):
            try:
                raw_img = pygame.image.load(img_path).convert_alpha()
                # 2. [변경] 이미지 크기를 1:1 비율인 정사각형(130x130)으로 스케일링
                self.image = pygame.transform.scale(raw_img, (130, 130))
            except Exception as e:
                print(f"[{self.name}] 이미지 로드 실패: {e}")

    def draw(self, screen, x, y):
        if not self.dragging:
            self.rect.x = x
            self.rect.y = y
            
        # 카드 배경 및 외곽선 두께 조정
        pygame.draw.rect(screen, self.color, self.rect, border_radius=10)
        pygame.draw.rect(screen, DARK, self.rect, 3, border_radius=10)
        
        # 폰트 설정
        c_font = pygame.font.SysFont("malgungothic", 16, bold=True)
        t_font = pygame.font.SysFont("malgungothic", 12)
        d_font = pygame.font.SysFont("malgungothic", 11)
        
        # 상단 텍스트 배치
        disp_name = self.name if len(self.name) <= 10 else self.name[:9] + ".."
        screen.blit(c_font.render(disp_name, True, DARK), (self.rect.x + 10, self.rect.y + 10))
        # 3. [변경] Y좌표를 살짝 올려 상단 여백 최적화 (32 -> 30)
        screen.blit(t_font.render(f"[{self.card_type}]", True, (60, 60, 60)), (self.rect.x + 10, self.rect.y + 30))
        
        # 4. [변경] 중간 정사각형 일러스트 영역 배치 (Y좌표 55 -> 50, 높이 75 -> 130)
        img_y = self.rect.y + 50
        if self.image:
            screen.blit(self.image, (self.rect.x + 10, img_y))
        else:
            pygame.draw.rect(screen, (215, 215, 215), (self.rect.x + 10, img_y, 130, 130), border_radius=5)
            pygame.draw.rect(screen, (160, 160, 160), (self.rect.x + 10, img_y, 130, 130), 1, border_radius=5)
        
        # 하단 설명 텍스트 자동 줄바꿈
        words = self.desc.split()
        lines = []
        curr_line = ""
        for w in words:
            if d_font.size(curr_line + w)[0] < 130:
                curr_line += w + " "
            else:
                lines.append(curr_line)
                curr_line = w + " "
        if curr_line: 
            lines.append(curr_line)
        
        # 5. [변경] 설명 출력 Y좌표를 커진 이미지 아래로 내림 (140 -> 190)
        for idx, line in enumerate(lines[:4]):
            screen.blit(d_font.render(line.strip(), True, DARK), (self.rect.x + 10, self.rect.y + 190 + idx * 14))

# 아래 데이터 구조 클래스(CardDummy, CardOnHand, TrashCard)는 기존과 동일하게 유지하시면 됩니다.
class CardDummy:
    def __init__(self): self.cardList = []
    def push(self, card): self.cardList.append(card)
    def pop(self): return self.cardList.pop() if not self.isEmpty() else None
    def isEmpty(self): return len(self.cardList) == 0
    def peek(self): return self.cardList[-1] if not self.isEmpty() else None

class CardOnHand:
    def __init__(self): self.cardList = []

class TrashCard:
    def __init__(self): self.cardList = []
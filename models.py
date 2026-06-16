import pygame
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
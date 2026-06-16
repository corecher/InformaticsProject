import pygame
import sys
from constants import WIDTH, HEIGHT, WHITE, GRAY, DARK, BLUE, RED, GREEN, HAND_X, HAND_Y
from manager import GameManager

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("준민이의 디스크 - 통합 안정화 버전")

# 폰트 구성
font = pygame.font.SysFont("malgungothic", 25)
big_font = pygame.font.SysFont("malgungothic", 60)
log_font = pygame.font.SysFont("malgungothic", 13)

# UI 버튼 및 구역 설정
start_button = pygame.Rect(450, 300, 300, 80)
exit_button = pygame.Rect(450, 410, 300, 80)
restart_button = pygame.Rect(450, 450, 300, 80)
draw_pile_rect = pygame.Rect(380, 100, 130, 180)
preview_button_rect = pygame.Rect(380, 300, 130, 40)
play_zone_rect = pygame.Rect(650, 100, 160, 220)
quit_game_button = pygame.Rect(50, 420, 250, 50)

clock = pygame.time.Clock()
manager = GameManager()

running = True
while running:
    screen.fill(WHITE)
    current_time_sec = 0
    
    if manager.game_state == "game":
        current_time_sec = (pygame.time.get_ticks() - manager.start_ticks) // 1000
        manager.check_passive_traps()

    # 1. 메뉴 화면 그리기
    if manager.game_state == "menu":
        title = big_font.render("JUNMIN'S DISK", True, DARK)
        screen.blit(title, (410, 160))
        pygame.draw.rect(screen, (120, 220, 120), start_button, border_radius=5)
        screen.blit(font.render("게임 시작", True, DARK), (540, 325))
        pygame.draw.rect(screen, (240, 128, 128), exit_button, border_radius=5)
        screen.blit(font.render("게임 종료", True, DARK), (540, 435))

    # 2. 인게임 화면 그리기
    elif manager.game_state == "game":
        pygame.draw.rect(screen, GRAY, (50, 50, 250, 350), border_radius=5)
        screen.blit(font.render(f"현재 카드 : {len(manager.card_on_hand.cardList)} / 1000", True, DARK), (70, 125))
        screen.blit(font.render(f"목표 카드 : 7장 완료", True, GREEN if len(manager.card_on_hand.cardList)==7 else DARK), (70, 175))
        screen.blit(font.render(f"행동 횟수 : {manager.total_actions}", True, DARK), (70, 225))
        
        if manager.turtle_neck_active: 
            screen.blit(font.render(f"거북목 카운트: {manager.turtle_neck_counter}", True, RED), (70, 325))
        elif manager.dog_bite_turns > 0: 
            screen.blit(font.render(f"상처 지속: {manager.dog_bite_turns}턴", True, RED), (70, 325))

        pygame.draw.rect(screen, RED, quit_game_button, border_radius=5)
        screen.blit(font.render("중도 포기", True, WHITE), (120, 430))

        pygame.draw.rect(screen, BLUE, draw_pile_rect, border_radius=5)
        screen.blit(font.render("뽑기 더미", True, WHITE), (395, 160))
        screen.blit(font.render(f"({len(manager.card_dummy.cardList)})", True, WHITE), (425, 200))

        pygame.draw.rect(screen, DARK, preview_button_rect, border_radius=5)
        screen.blit(font.render("다음 카드 보기", True, WHITE), (385, 307))

        if manager.show_preview and not manager.card_dummy.isEmpty():
            next_c = manager.card_dummy.peek()
            pygame.draw.rect(screen, next_c.color, (380, 350, 130, 45), border_radius=5)
            screen.blit(log_font.render(f"이름: {next_c.name}", True, DARK), (385, 353))

        pygame.draw.rect(screen, (230, 230, 230), play_zone_rect, border_radius=5)
        screen.blit(font.render("카드 내기", True, DARK), (680, 190))

        pygame.draw.rect(screen, (245, 245, 245), (840, 100, 320, 220), border_radius=5)
        screen.blit(font.render("실시간 로그", True, DARK), (850, 105))
        for idx, log in enumerate(manager.log_queue):
            screen.blit(log_font.render(log, True, (30, 30, 30)), (850, 142 + idx * 22))

        # 하단 핸드 그리드뷰 구현
        pygame.draw.rect(screen, (220, 220, 220), (250, 450, 700, 220), border_radius=5)
        cards_per_row = 8  
        start_card_idx = manager.scroll_index * cards_per_row
        visible_cards = manager.card_on_hand.cardList[start_card_idx: start_card_idx + 16] 
        
        for idx, card in enumerate(visible_cards):
            row, col = idx // cards_per_row, idx % cards_per_row
            card.draw(screen, HAND_X + col * 85, HAND_Y + row * 105)

        if len(manager.card_on_hand.cardList) > 0:
            total_rows = (len(manager.card_on_hand.cardList) + 7) // cards_per_row
            screen.blit(font.render(f"행: {manager.scroll_index + 1}/{max(1, total_rows)} ({len(manager.card_on_hand.cardList)}장 보유)", True, DARK), (480, 642))

        # 게임 클리어 조건 실시간 감지
        if manager.mingi_project_turns <= 0:
            if any(c.name == "신데렐라는 아쉬워 벌써 12시" for c in manager.card_on_hand.cardList) and len(manager.card_on_hand.cardList) == 12:
                manager.final_time = current_time_sec
                manager.game_state = "clear"
            elif len(manager.card_on_hand.cardList) == 7:
                manager.final_time = current_time_sec
                manager.game_state = "clear"

    # 3. 클리어 화면 그리기
    elif manager.game_state == "clear":
        screen.blit(big_font.render("GAME CLEAR", True, GREEN), (430, 150))
        screen.blit(font.render(f"최종 행동 횟수 : {manager.total_actions}회", True, DARK), (490, 320))
        pygame.draw.rect(screen, (120, 220, 120), restart_button, border_radius=5)
        screen.blit(font.render("다시 하기", True, DARK), (550, 475))

    pygame.display.flip()

    # 이벤트 바인딩 제어
    for event in pygame.event.get():
        if event.type == pygame.QUIT: 
            running = False
            
        if manager.game_state == "menu" and event.type == pygame.MOUSEBUTTONDOWN:
            if start_button.collidepoint(event.pos): 
                manager.start_game()
            elif exit_button.collidepoint(event.pos): 
                running = False
                
        elif manager.game_state == "game":
            if event.type == pygame.MOUSEBUTTONDOWN:
                if draw_pile_rect.collidepoint(event.pos): 
                    manager.draw_card_from_dummy()
                elif preview_button_rect.collidepoint(event.pos):
                    manager.show_preview = not manager.show_preview
                    manager.total_actions += 1
                    manager.tick_turn_counters()
                elif quit_game_button.collidepoint(event.pos): 
                    manager.game_state = "menu"
                else:
                    visible_cards = manager.card_on_hand.cardList[manager.scroll_index * 8: manager.scroll_index * 8 + 16]
                    for card in reversed(visible_cards):
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
                    if manager.drag_card.card_type == "함정": 
                        manager.add_log("함정 카드는 낼 수 없습니다!")
                    else:
                        manager.card_on_hand.cardList.remove(manager.drag_card)
                        manager.trash_card.cardList.append(manager.drag_card)
                        manager.score += 1
                        manager.total_actions += 1
                        manager.execute_action_card(manager.drag_card)
                        manager.scroll_index = min(manager.scroll_index, max(0, ((len(manager.card_on_hand.cardList) + 7) // 8) - 2))
                manager.drag_card = None
                
            elif event.type == pygame.MOUSEWHEEL:
                manager.scroll_index = max(0, min(manager.scroll_index + (-1 if event.y > 0 else 1), max(0, ((len(manager.card_on_hand.cardList) + 7) // 8) - 2)))
                
        elif manager.game_state == "clear" and event.type == pygame.MOUSEBUTTONDOWN and restart_button.collidepoint(event.pos):
            manager.start_game()

    clock.tick(60)

pygame.quit()
sys.exit()
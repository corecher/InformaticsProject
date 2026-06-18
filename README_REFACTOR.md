# 준민이의 디스크 리팩토링 버전 v25

기존 `main.py / manager.py / models.py / constants.py` 중심 구조를 역할별 패키지 구조로 정리했습니다.

## 실행 방법

```bash
pip install pygame
python main.py
```

## 새 파일 구조

```text
InformaticsProject/
├─ main.py                 # 실행 진입점
├─ constants.py            # 구버전 호환용 re-export 파일
├─ images/                 # 카드 이미지 폴더, 카드이름.png 형식
├─ Sound/                  # 카드 이동 효과음 폴더, mp3 사용
└─ game/
   ├─ __init__.py
   ├─ app.py               # Pygame 화면, 입력, 애니메이션 처리
   ├─ audio.py             # 효과음 로딩/재생
   ├─ card_data.py         # 카드 이름/타입/설명 데이터
   ├─ config.py            # 화면 크기, 색상, 기본 규칙 설정
   ├─ manager.py           # 게임 규칙, 카드 효과, 덱/손패/버린더미 처리
   ├─ models.py            # Card 클래스와 카드 컨테이너
   └─ utils.py             # 보간, 시간 포맷 등 공용 함수
```

## 리팩토링 기준

- 화면 관련 코드는 `game/app.py`로 모았습니다.
- 게임 규칙과 카드 효과는 `game/manager.py`에만 남겼습니다.
- 카드 데이터는 `game/card_data.py`로 분리했습니다.
- 효과음 처리는 `game/audio.py`로 분리했습니다.
- 카드 이미지 경로는 루트 `images/` 폴더를 우선 확인하게 수정했습니다.
- 기존 `constants.py` import가 깨지지 않도록 호환 파일을 남겼습니다.

## 핵심 규칙 주석

코드 내부에 다음 내용을 중심으로 주석을 추가했습니다.

- 손패가 스택처럼 관리되는 이유
- 드로우/버리기/발동 연출 큐의 역할
- 논리 손패와 화면용 손패를 분리한 이유
- 즉발 카드와 함정 카드의 발동 타이밍
- n장 달성형 함정이 최종 이벤트 종료 후 판정되는 이유
- Sound 폴더 mp3 효과음 로딩 방식

## 이미지/효과음

카드 이미지는 다음처럼 넣으면 자동으로 표시됩니다.

```text
images/게임.png
images/소리 질러.png
```

효과음은 다음처럼 넣으면 됩니다.

```text
Sound/card.mp3
```

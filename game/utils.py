"""여러 모듈에서 함께 쓰는 작은 유틸 함수 모음입니다."""

def clamp(value, min_value=0.0, max_value=1.0):
    """value를 min_value~max_value 범위 안으로 제한합니다."""
    return max(min_value, min(max_value, value))


def ease_out_cubic(t):
    """처음에는 빠르고 끝으로 갈수록 천천히 움직이는 보간 함수."""
    t = clamp(t)
    return 1 - pow(1 - t, 3)


def ease_in_out(t):
    """시작과 끝은 부드럽고 중간은 빠른 보간 함수."""
    t = clamp(t)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    """숫자 a에서 b까지 t 비율만큼 선형 보간합니다."""
    return a + (b - a) * t


def lerp_pos(a, b, t):
    """2차원 좌표 a에서 b까지 t 비율만큼 선형 보간합니다."""
    return (lerp(a[0], b[0], t), lerp(a[1], b[1], t))


def format_time(total_seconds):
    """초 단위 시간을 'n분 ss초' 문자열로 변환합니다."""
    total_seconds = max(0, int(total_seconds))
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}분 {seconds:02d}초"

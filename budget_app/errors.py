"""사용자에게 안전하게 표시할 애플리케이션 오류."""


class BudgetAppError(Exception):
    """원인과 해결 힌트를 함께 전달하는 도메인 오류."""

    def __init__(self, message: str, hint: str = "입력값을 확인한 뒤 다시 시도하세요.") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


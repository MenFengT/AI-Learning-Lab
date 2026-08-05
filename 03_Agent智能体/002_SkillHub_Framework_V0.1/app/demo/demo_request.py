"""运行MVP文本请求。"""

from app.adapters.telegram import TelegramMessage, TelegramResponse

from .demo_bootstrap import create_demo_application


def run_demo_request() -> TelegramResponse:
    application = create_demo_application()
    return application.container.telegram_adapter.handle(
        TelegramMessage(
            message_id="1",
            chat_id="10001",
            user_id="20001",
            text="生成一份项目开工报告",
        )
    )


if __name__ == "__main__":
    print(run_demo_request())

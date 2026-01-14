import logging
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError

logger = logging.getLogger(__name__)

class LineClient:
    def __init__(self, channel_access_token, user_id):
        self.line_bot_api = LineBotApi(channel_access_token)
        self.user_id = user_id

    def send_message(self, text):
        """LINEにメッセージを送信"""
        try:
            self.line_bot_api.push_message(
                self.user_id,
                TextSendMessage(text=text[:5000]) # LINEの制限に合わせる
            )
            logger.info("LINE送信成功")
            return True
        except LineBotApiError as e:
            logger.error(f"LINE送信失敗: {e.status_code} {e.error.message}")
            return False
        except Exception as e:
            logger.error(f"LINE送信エラー: {e}")
            return False

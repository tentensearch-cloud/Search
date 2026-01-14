import os
import json
import time
import feedparser
import logging
import sys
from pathlib import Path
from datetime import datetime
import utils
from line_client import LineClient

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class NewsBotLine:
    def __init__(self):
        self.google_api_key = os.environ.get('GOOGLE_API_KEY')
        self.line_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
        self.line_user_id = os.environ.get('LINE_USER_ID')
        self.rss_feeds = os.environ.get('RSS_FEEDS', '').split(',')
        
        self.history_file = Path('history.json')
        self.history = self.load_history()
        self.excluded_models = []
        
        self.line = LineClient(self.line_token, self.line_user_id)
        
        # モデル初期化
        self.model, self.model_name = utils.get_smart_gemini_model(
            self.google_api_key, excluded_models=self.excluded_models
        )

    def load_history(self):
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"ids": [], "titles": []}
        return {"ids": [], "titles": []}

    def save_history(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def fetch_new_entries(self):
        new_entries = []
        for url in self.rss_feeds:
            if not url: continue
            try:
                feed = feedparser.parse(url.strip())
                for entry in feed.entries:
                    entry_id = entry.get('id', entry.get('link'))
                    title = utils.clean_html_tags(entry.title)
                    
                    # ID重複チェック
                    if entry_id in self.history["ids"]:
                        continue
                    
                    # 類似度チェック
                    if utils.is_similar(title, self.history.get("titles", [])):
                        logger.info(f"類似記事をスキップ: {title}")
                        self.history["ids"].append(entry_id) # スキップしたものも再送しないよう記録
                        continue
                        
                    new_entries.append(entry)
            except Exception as e:
                logger.error(f"RSS取得エラー ({url}): {e}")
        return new_entries

    def process_entry(self, entry):
        title = utils.clean_html_tags(entry.title)
        link = entry.link
        summary_text = utils.clean_html_tags(entry.get('summary', ''))
        
        logger.info(f"処理中: {title}")
        
        # 緊急度判定
        urgent = utils.is_urgent(title, summary_text)
        prefix = "🚨【緊急】" if urgent else "📌【ニュース】"
        
        prompt = utils.get_analyst_prompt(f"タイトル: {title}\n本文: {summary_text}\nURL: {link}")
        
        max_retries = 3
        for attempt in range(max_retries):
            if not self.model:
                self.model, self.model_name = utils.get_smart_gemini_model(
                    self.google_api_key, excluded_models=self.excluded_models
                )
            
            if not self.model:
                logger.error("利用可能なGeminiモデルがありません。")
                return None

            try:
                response = self.model.generate_content(prompt)
                result_text = response.text
                
                if "除外対象" in result_text:
                    return None
                    
                full_message = f"{prefix}\n{title}\n\n{result_text}\n\n記事URL: {link}"
                return full_message
            except Exception as e:
                error_str = str(e)
                logger.error(f"Geminiエラー ({self.model_name}): {e}")
                
                if "429" in error_str or "quota" in error_str.lower():
                    self.excluded_models.append(self.model_name)
                    self.model = None # 次のループで再選択
                    time.sleep(5)
                else:
                    time.sleep(2)
        return None

    def run(self):
        new_entries = self.fetch_new_entries()
        logger.info(f"新規記事: {len(new_entries)}件")
        
        for entry in new_entries:
            try:
                result = self.process_entry(entry)
                if result:
                    if self.line.send_message(result):
                        self.history["ids"].append(entry.get('id', entry.get('link')))
                        self.history["titles"].append(utils.clean_html_tags(entry.title))
                        # 履歴が大きくなりすぎないよう調整 (直近200件)
                        self.history["titles"] = self.history["titles"][-200:]
                        self.save_history()
                        time.sleep(5) # 送信間隔
            except Exception as e:
                logger.error(f"記事処理エラー: {e}")

if __name__ == "__main__":
    bot = NewsBotLine()
    bot.run()

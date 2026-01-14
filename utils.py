import google.generativeai as genai
import logging
import re
import time
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ユーザー指定のターゲット企業リスト (プロンプト表示用)
TARGET_COMPANIES_STR = "Anduril,スカパーJSAT,GSユアサ,ミネベアミツミ,ニコン,マクニカHD,伊藤忠,NEC,住友商事,信越化学工業,KDDI,古野電気,ハーモニック・ドライブ・システムズ,ACSL,レンゾ,三菱重工業,ニデック,TDK,双葉電子工業,浜松ホトニクス,東レ,Anduril,ソニー,メタプラネット,アスター,航空電子工業,エクセディ,ジェイテクト"

# 緊急ニュースキーワード
URGENT_KEYWORDS = ["IPO", "上場", "国家プロジェクト", "受注", "政府", "防衛省", "JAXA", "M&A", "合併"]

def clean_html_tags(text):
    """HTMLタグを除去する"""
    if not text:
        return ""
    clean = re.sub(r'<.*?>', '', text)
    return clean

def get_smart_gemini_model(api_key, preferred_model=None, excluded_models=None):
    """
    利用可能なGeminiモデルを自動選択して返す (429制限回避用)
    """
    genai.configure(api_key=api_key)
    if excluded_models is None:
        excluded_models = []
    
    candidates = []
    if preferred_model and preferred_model not in excluded_models:
        candidates.append(preferred_model)
        if not preferred_model.startswith("models/"):
            candidates.append(f"models/{preferred_model}")
            
    default_candidates = [
        "models/gemini-1.5-flash",      # 1500 RPM / 1M TPM (最も安定)
        "models/gemini-1.5-flash-8b",   # 高速かつ高クォータ
        "models/gemini-2.0-flash-lite", # 最新軽量モデル
        "models/gemini-2.0-flash",      # 最新高速モデル
        "models/gemini-2.5-flash-lite", # 2.5系は現在クォータが極端に少ない
        "models/gemini-2.5-flash",
    ]
    for m in default_candidates:
        if m not in candidates and m not in excluded_models:
            candidates.append(m)
            
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            # 接続テスト
            response = model.generate_content("Hi", generation_config={"max_output_tokens": 1})
            if response:
                return model, model_name
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                logger.warning(f"モデル {model_name} はレート制限中です (429)")
            continue
            
    return None, None

def get_analyst_prompt(news_text):
    """投資アナリストのロールプレイプロンプトを生成"""
    prompt = f"""
あなたはプロの防衛・技術アナリストであり、世界的な投資家です。
以下のニュースを日本語に翻訳し、ポジティブかネガティブか判定した上で、ポジティブ要素とネガティブ要素それぞれ3行程度で簡潔に要約してください。
そしてその結果から({TARGET_COMPANIES_STR})は買い目であるか売り目であるか判断してください。
更に、Andurilに関連する日本企業が({TARGET_COMPANIES_STR})以外であった時はその企業名を最後に記載してください。
なお、入力されたニュースが日本の事業会社（例：NEC 日本電気等）に関するものではなく、海外のスポーツチームや無関係な同名組織に関するニュースは除外してください。

対象ニュース:
{news_text}
"""
    return prompt

def is_urgent(title, summary):
    """緊急性が高いニュースかどうかを判定"""
    text = f"{title} {summary}"
    for kw in URGENT_KEYWORDS:
        if kw in text:
            return True
    return False

def is_similar(new_title, history_titles, threshold=0.8):
    """
    新しいタイトルが履歴にあるタイトルと酷似しているか判定
    """
    if not history_titles:
        return False
    
    titles = history_titles + [new_title]
    try:
        vectorizer = TfidfVectorizer().fit_transform(titles)
        vectors = vectorizer.toarray()
        
        # 最後の要素（new_title）とそれ以外の類似度を計算
        new_vec = vectors[-1].reshape(1, -1)
        history_vecs = vectors[:-1]
        
        cosine_sim = cosine_similarity(new_vec, history_vecs)
        max_sim = cosine_sim.max()
        
        if max_sim >= threshold:
            return True
    except:
        # 学習データ不足などでエラーが出る場合は無視
        pass
    
    return False

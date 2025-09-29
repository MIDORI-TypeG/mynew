import os
import easyocr
import re
import logging
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import threading

# --- ログ設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 設定 ---
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

# 検索するキーワード
KEYWORDS = {
    "日付": "date",
    "牛乳": "milk",
    "卵": "egg",
    "バター": "butter",
    "ピザ": "pizza",
    "パン": "bread",
    "冷蔵": "refrigerated_sweets",
    "冷凍": "frozen_sweets",
}

def allowed_file(filename):
    """ファイル拡張子が許可されているかチェック"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# OCRリーダーの遅延初期化
reader = None
reader_lock = threading.Lock()

def get_ocr_reader():
    """OCRリーダーの遅延初期化（スレッドセーフ）"""
    global reader
    if reader is None:
        with reader_lock:
            if reader is None:  # ダブルチェック
                logger.info("OCRリーダーを初期化中...")
                try:
                    reader = easyocr.Reader(['ja', 'en'], verbose=False)
                    logger.info("OCRリーダーの準備完了")
                except Exception as e:
                    logger.error(f"OCRリーダーの初期化失敗: {e}")
                    raise e
    return reader

def extract_stock_from_image(image_data):
    """
    画像のバイトデータからOCRを使い在庫情報を抽出
    """
    try:
        ocr_reader = get_ocr_reader()
        results = ocr_reader.readtext(image_data, paragraph=False)
    except Exception as e:
        logger.error(f"OCR処理エラー: {e}")
        return {"error": f"OCR処理中にエラーが発生しました: {str(e)}"}

    logger.info(f"OCRで{len(results)}個のテキストブロックを検出")

    stock = {}
    used_indices = set()
    zenkaku_to_hankaku = str.maketrans('０１２３４５６７８９', '0123456789')

    for i, (bbox, text, prob) in enumerate(results):
        for ja_keyword in KEYWORDS.keys():
            if ja_keyword in text:
                for j in range(i + 1, min(i + 6, len(results))):
                    if j in used_indices:
                        continue

                    next_text = results[j][1]
                    number_match = re.match(r'\s*[:：\s]*([\d０-９]+)\s*', next_text)
                    
                    if number_match:
                        number_str = number_match.group(1)
                        try:
                            number = int(number_str.translate(zenkaku_to_hankaku))
                            if ja_keyword not in stock:
                                stock[ja_keyword] = number
                            used_indices.add(j)
                            break
                        except ValueError:
                            continue
    
    return stock

# --- Flaskアプリのセットアップ ---
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "ファイルサイズが大きすぎます（上限: 16MB）"}), 413

@app.route('/', methods=['GET'])
def index():
    """ルートエンドポイント - API情報を返す"""
    return jsonify({
        "service": "OCR Stock Scanner API",
        "version": "1.0",
        "status": "ready",
        "endpoints": {
            "/health": "ヘルスチェック",
            "/scan": "画像からOCR処理（POST）"
        },
        "supported_formats": list(ALLOWED_EXTENSIONS),
        "max_file_size": "16MB"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        "status": "healthy",
        "ocr_initialized": reader is not None,
        "message": "OCRリーダーは初回リクエスト時に初期化されます" if reader is None else "OCRリーダー準備完了"
    }), 200

@app.route('/scan', methods=['POST'])
def scan_image():
    """画像ファイルを受け取り、OCR処理を実行"""
    
    # ファイルの存在確認
    if 'file' not in request.files:
        return jsonify({"error": "ファイルがありません"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "ファイルが選択されていません"}), 400

    # ファイル拡張子の確認
    if not allowed_file(file.filename):
        return jsonify({
            "error": "サポートされていないファイル形式です。対応形式: PNG, JPG, JPEG, GIF, BMP, TIFF"
        }), 400

    try:
        filename = secure_filename(file.filename)
        logger.info(f"Processing file: {filename}")
        
        # 画像データの読み込み
        image_data = file.read()
        
        if len(image_data) == 0:
            return jsonify({"error": "空のファイルです"}), 400
        
        # OCR処理の実行（ここで初回初期化される）
        stock_data = extract_stock_from_image(image_data)
        
        if "error" in stock_data:
            return jsonify(stock_data), 500
        
        logger.info(f"OCR処理完了: {len(stock_data)}個のアイテムを検出")
        return jsonify({
            "success": True,
            "data": stock_data,
            "count": len(stock_data)
        })
        
    except Exception as e:
        logger.error(f"処理中にエラーが発生: {e}")
        return jsonify({"error": "サーバー内部エラーが発生しました"}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting server on port {port}, debug={debug_mode}")
    logger.info("OCRリーダーは初回API呼び出し時に初期化されます")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

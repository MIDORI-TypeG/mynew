import easyocr
import re
import io
from flask import Flask, request, jsonify

# --- OCR機能の準備 ---

# 検索するキーワード
KEYWORDS = {
    "日付q": "date",
    "牛乳": "milk",
    "卵": "egg",
    "バター": "butter",
    "ピザ": "pizza",
    "パン": "bread",
    "冷蔵": "refrigerated_sweets",
    "冷凍": "frozen_sweets",
}

# OCRリーダーを起動時に一度だけ初期化して、効率化します
print("OCRリーダーを初期化しています... (初回実行時はモデルのダウンロードに時間がかかります)")
reader = easyocr.Reader(['ja', 'en'])
print("OCRリーダーの準備ができました。")

def extract_stock_from_image(image_data):
    """
    画像のバイトデータからOCRを使い在庫情報を抽出します。
    テキストブロックのシーケンスを解析して、キーワードと数値の関連付けを行います。
    Args:
        image_data (bytes): 画像のバイトデータ。
    Returns:
        dict: 抽出された在庫アイテムと数の辞書。
    """
    try:
        # paragraph=Falseにすることで、個別のテキストブロックとして結果を取得します
        results = reader.readtext(image_data, paragraph=False)
    except Exception as e:
        return {"error": f"OCR処理中にエラーが発生しました: {e}"}

    # デバッグ用に、検出されたすべてのテキストブロックを表示します
    print("\n--- OCR Results ---")
    for (bbox, text, prob) in results:
        print(f'Detected text: "{text}"')
    print("---------------------\n")

    stock = {}
    used_indices = set()  # 値として使用されたテキストブロックのインデックスを記録
    zenkaku_to_hankaku = str.maketrans('０１２３４５６７８９', '0123456789')

    # 検出された各テキストブロックをループ処理
    for i, (bbox, text, prob) in enumerate(results):
        # 現在のテキストブロックにキーワードが含まれているかチェック
        for ja_keyword in KEYWORDS.keys():
            if ja_keyword in text:
                # キーワードが見つかったので、後続のテキストブロックで数値を探します
                # 直後の5ブロックを検索対象とします
                for j in range(i + 1, min(i + 6, len(results))):
                    if j in used_indices:
                        continue  # この数値は既に使用済み

                    next_text = results[j][1]
                    
                    # テキストが数値で構成されているかチェック
                    number_match = re.match(r'\s*[:：\s]*([\d０-９]+)\s*', next_text)
                    
                    if number_match:
                        number_str = number_match.group(1)
                        number = int(number_str.translate(zenkaku_to_hankaku))
                        
                        # 同じキーワードがすでに見つかっていても、新しい数値を上書きしない
                        if ja_keyword not in stock:
                            stock[ja_keyword] = number
                        
                        used_indices.add(j)
                        
                        # このキーワードに対する数値が見つかったので、次のキーワードの検索に移る
                        break
    return stock

# --- Flaskアプリのセットアップ ---

app = Flask(__name__)

@app.route('/scan', methods=['POST'])
def scan_image():
    """
    画像ファイルを受け取り、OCR処理を実行して結果をJSONで返します。
    """
    if 'file' not in request.files:
        return jsonify({"error": "ファイルがありません"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "ファイルが選択されていません"}), 400

    if file:
        image_data = file.read()
        stock_data = extract_stock_from_image(image_data)
        
        if "error" in stock_data:
            return jsonify(stock_data), 500
            
        return jsonify(stock_data)

if __name__ == "__main__":
    # 本番環境ではGunicornなどを使用してください
    app.run(debug=True, host='0.0.0.0', port=5000)
import discord
import easyocr
import re
import os
import io
from dotenv import load_dotenv

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

# --- Discordボットのセットアップ ---

intents = discord.Intents.default()
intents.message_content = True  # メッセージの内容を読み取るために必要
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    """ボットがログインしたときに呼ばれるイベント"""
    print("------------------------------------------------------")
    print(f'{client.user} としてDiscordにログインしました。')
    print("画像が投稿されるのを待っています...")
    print("------------------------------------------------------")

@client.event
async def on_message(message):
    """メッセージが投稿されたときに呼ばれるイベント"""
    if message.author == client.user:
        return

    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                print(f"{message.channel}チャンネルに画像が投稿されました: {attachment.filename}")
                
                async with message.channel.typing():
                    await message.add_reaction('🤔')  # 考え中...
                    
                    image_data = await attachment.read()
                    stock_data = extract_stock_from_image(image_data)

                    await message.remove_reaction('🤔', client.user)

                    if "error" in stock_data:
                        await message.channel.send(f"エラーが発生しました: {stock_data['error']}")
                        await message.add_reaction('❌')
                        continue

                    if not stock_data:
                        response = "画像から在庫情報を読み取れませんでした。😭"
                        await message.add_reaction('🤷')
                    else:
                        response = "📄 **在庫サマリー** 📄\n" + "-" * 20 + "\n"
                        for item, count in stock_data.items():
                            response += f"**{item}**: {count}\n"
                        response += "-" * 20
                        await message.add_reaction('✅')

                    await message.reply(response, mention_author=False)

def main():
    """メイン関数。ボットを起動します。"""
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("エラー: DISCORD_TOKENが設定されていません。")
        print("プロジェクトフォルダに '.env' という名前のファイルを作成し、")
        print("その中に 'DISCORD_TOKEN=あなたのボットのトークン' と記述してください。")
        return

    try:
        client.run(token)
    except discord.errors.LoginFailure:
        print("エラー: 無効なDiscordトークンです。トークンが正しいか確認してください。")

if __name__ == "__main__":
    main()

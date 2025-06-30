import websocket
import json
import telegram
import threading
import time

TOKEN = "7997920015:AAGymUB4jMIGwIkwctWZh4QmKbGN_TicW1E"
CHAT_ID = 6952277012  # Remplace par ton vrai chat_id

alertes = {
    "R_75": 3300.0,
    "R_100": 9800.0,
    "step_index": 80.0,
    "R_50_1s": 500.0,
    "multi_step_2": 2500.0
}

bot = telegram.Bot(token=TOKEN)

def create_ws(symbol, seuil):
    def on_message(ws, message):
        data = json.loads(message)
        if 'tick' in data:
            prix = float(data['tick']['quote'])
            print(f"[{symbol}] prix: {prix}")
            if prix >= seuil:
                bot.send_message(chat_id=CHAT_ID, text=f"🔔 {symbol} a atteint {prix} (seuil: {seuil})")
                ws.close()

    def on_open(ws):
        ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))

    ws = websocket.WebSocketApp("wss://ws.deriv.com/websockets/v3",
                                on_open=on_open,
                                on_message=on_message)
    ws.run_forever()

threads = []
for symbol, seuil in alertes.items():
    t = threading.Thread(target=create_ws, args=(symbol, seuil))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
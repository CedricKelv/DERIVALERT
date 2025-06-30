import threading
import json
import websocket
from telegram import Bot
from telegram.ext import Updater, CommandHandler, Filters

# === CONFIGURATION ===
TOKEN   = "7997920015:AAGymUB4jMIGwIkwctWZh4QmKbGN_TicW1E"    # ← remplace par ton token BotFather
CHAT_ID = 6952277012             # ← remplace par ton chat_id

# Structure pour stocker les alertes actives { chat_id: { symbol: seuil, … } }
alerts = {}

bot = Bot(token=TOKEN)

# ——————— Fonctions utilitaires ———————

def subscribe_ws(symbol, chat_id, seuil):
    """Ouvre une connexion WebSocket et surveille un symbole."""
    def on_open(ws):
        ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))

    def on_message(ws, message):
        data = json.loads(message)
        if 'tick' in data:
            price = float(data['tick']['quote'])
            if price >= seuil:
                bot.send_message(chat_id=chat_id,
                                 text=f"🔔 {symbol} a atteint {price} (seuil : {seuil})")
                ws.close()
    ws = websocket.WebSocketApp(
        "wss://ws.deriv.com/websockets/v3",
        on_open=on_open,
        on_message=on_message
    )
    ws.run_forever()

def start_all_threads(chat_id):
    """Relance un thread WebSocket pour chaque alerte de cet utilisateur."""
    user_alerts = alerts.get(chat_id, {})
    for sym, sl in user_alerts.items():
        t = threading.Thread(target=subscribe_ws, args=(sym, chat_id, sl))
        t.daemon = True
        t.start()

# ——————— Handlers Telegram ———————

def cmd_prix(update, context):
    sym = context.args[0].upper()
    # requête unique WebSocket pour prix actuel
    def on_message(ws, message):
        data = json.loads(message)
        if 'tick' in data:
            price = data['tick']['quote']
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"{sym} est à {price}")
            ws.close()
    ws = websocket.WebSocketApp(
        "wss://ws.deriv.com/websockets/v3",
        on_message=on_message,
        on_open=lambda ws: ws.send(json.dumps({"ticks": sym, "subscribe": 1}))
    )
    ws.run_forever()

def cmd_alerte(update, context):
    chat_id = update.effective_chat.id
    sym = context.args[0].upper()
    seuil = float(context.args[1])
    alerts.setdefault(chat_id, {})[sym] = seuil
    update.message.reply_text(f"Alerte enregistrée : {sym} ≥ {seuil}")
    # lancer immédiatement le monitoring
    t = threading.Thread(target=subscribe_ws, args=(sym, chat_id, seuil))
    t.daemon = True
    t.start()

def cmd_annule(update, context):
    chat_id = update.effective_chat.id
    sym = context.args[0].upper()
    if alerts.get(chat_id, {}).pop(sym, None) is not None:
        update.message.reply_text(f"Alerte supprimée pour {sym}")
    else:
        update.message.reply_text(f"Aucune alerte active pour {sym}")

def cmd_list(update, context):
    user_alerts = alerts.get(update.effective_chat.id, {})
    if not user_alerts:
        update.message.reply_text("Aucune alerte active.")
    else:
        lines = [f"{s} ≥ {v}" for s, v in user_alerts.items()]
        update.message.reply_text("🔔 Alertes actives :\n" + "\n".join(lines))

def cmd_pause(update, context):
    # simple pause : vide toutes les alertes en mémoire
    alerts.pop(update.effective_chat.id, None)
    update.message.reply_text("Toutes les alertes ont été mises en pause.")

# ——————— Configuration du bot ———————

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("prix",    cmd_prix,   Filters.chat_type.private, pass_args=True))
    dp.add_handler(CommandHandler("alerte",  cmd_alerte, Filters.chat_type.private, pass_args=True))
    dp.add_handler(CommandHandler("annule",  cmd_annule, Filters.chat_type.private, pass_args=True))
    dp.add_handler(CommandHandler("list",    cmd_list,   Filters.chat_type.private))
    dp.add_handler(CommandHandler("pause",   cmd_pause,  Filters.chat_type.private))
    dp.add_handler(CommandHandler("stop",    cmd_pause,  Filters.chat_type.private))

    # relancer les threads sur un redémarrage (inutile sur Render, mais sans mal)
    for chat_id in alerts:
        start_all_threads(chat_id)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from google_calendar import criar_evento, listar_eventos
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import dateparser
import re
import json
import os



TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Token do Telegram não configurado!")
FUSO = ZoneInfo("America/Recife")

ARQUIVO_LEMBRETES = "lembretes_enviados.json"
ARQUIVO_CHAT = "chat_id.json"



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    with open(ARQUIVO_CHAT, "w", encoding="utf-8") as arquivo:
        json.dump({"chat_id": chat_id}, arquivo)

    await update.message.reply_text(
        "Olá! 👋 Eu sou o Genius Agenda AI!\n\n"
        "Você pode me pedir para agendar um compromisso.\n"
        "Exemplo: Marque uma reunião com Yuri amanhã às 14h.\n\n"
        "Seu Telegram foi registrado para receber lembretes automáticos!"
    )



async def teste_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agora = datetime.now(FUSO)
    inicio = agora + timedelta(minutes=10)
    fim = inicio + timedelta(minutes=30)

    try:
        link = criar_evento(
            titulo="Teste do Genius Agenda AI",
            inicio=inicio.isoformat(),
            fim=fim.isoformat(),
            descricao="Evento criado para testar a integração."
        )
        await update.message.reply_text(
            f"Evento de teste criado com sucesso! 🎉\n{link}"
        )
    except Exception as erro:
        print(f"Erro ao criar evento: {erro}")
        await update.message.reply_text(
            "Não consegui criar o evento. Confira o terminal do VS Code."
        )


async def verificar_lembretes(context: ContextTypes.DEFAULT_TYPE):
    try:
        if not os.path.exists(ARQUIVO_CHAT):
            return

        with open(ARQUIVO_CHAT, "r", encoding="utf-8") as arquivo:
            dados_chat = json.load(arquivo)

        chat_id = dados_chat.get("chat_id")
        if not chat_id:
            return

        agora = datetime.now(FUSO)
        inicio_busca = agora + timedelta(minutes=29)
        fim_busca = agora + timedelta(minutes=31)

        eventos = listar_eventos(inicio_busca, fim_busca)

        if os.path.exists(ARQUIVO_LEMBRETES):
            with open(ARQUIVO_LEMBRETES, "r", encoding="utf-8") as arquivo:
                enviados = json.load(arquivo)
        else:
            enviados = []

        for evento in eventos:
            evento_id = evento.get("id")
            titulo = evento.get("summary", "Compromisso")
            inicio_evento = evento.get("start", {}).get("dateTime")

            if not evento_id or evento_id in enviados or not inicio_evento:
                continue

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "⏰ Lembrete do Genius Agenda AI!\n\n"
                    f"Seu compromisso '{titulo}' começa em aproximadamente 30 minutos."
                )
            )

            enviados.append(evento_id)

        with open(ARQUIVO_LEMBRETES, "w", encoding="utf-8") as arquivo:
            json.dump(enviados, arquivo, ensure_ascii=False)

    except Exception as erro:
        print(f"Erro ao verificar lembretes: {erro}")

async def receber_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = update.message.text.strip()

    
    # Consulta os compromissos de hoje ou amanhã
    texto = mensagem.lower()
    agora = datetime.now(FUSO)

    if "compromissos" in texto or "agenda" in texto:
        if "amanhã" in texto or "amanha" in texto:
            inicio_consulta = (agora + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            inicio_consulta = agora.replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        fim_consulta = inicio_consulta + timedelta(days=1)

        try:
            eventos = listar_eventos(inicio_consulta, fim_consulta)

            if not eventos:
                await update.message.reply_text(
                    "Você não tem compromissos nesse período. 😊"
                )
                return

            resposta = "📅 Seus compromissos:\n\n"

            for evento in eventos:
                titulo_evento = evento.get("summary", "Sem título")
                comeco = evento.get("start", {})
                horario = comeco.get("dateTime")

                if horario:
                    data_hora = datetime.fromisoformat(
                        horario.replace("Z", "+00:00")
                    ).astimezone(FUSO)
                    horario_texto = data_hora.strftime("%H:%M")
                else:
                    horario_texto = "Dia inteiro"

                resposta += f"🕒 {horario_texto} — {titulo_evento}\n"

            await update.message.reply_text(resposta)
            return

        except Exception as erro:
            print(f"Erro ao consultar agenda: {erro}")
            await update.message.reply_text(
                "Não consegui consultar sua agenda. Confira o terminal do VS Code."
            )
            return


    # Procura um horário como 14h, 14:30 ou 14 horas
    padrao_hora = re.search(
        r"\b(?:às?\s*)?(\d{1,2})(?::(\d{2}))?\s*(h|horas)?\b",
        mensagem.lower()
    )

    if not padrao_hora:
        await update.message.reply_text(
            "Não consegui identificar o horário. 😊\n"
            "Tente, por exemplo: Marque uma reunião amanhã às 14h."
        )
        return

    hora = int(padrao_hora.group(1))
    minuto = int(padrao_hora.group(2) or 0)

    if hora > 23 or minuto > 59:
        await update.message.reply_text(
            "Esse horário parece inválido. Envie um horário como 14h ou 14:30."
        )
        return

    
    # Interpreta a data em português
    agora = datetime.now(FUSO)
    texto = mensagem.lower()

    # Reconhece hoje e amanhã diretamente.
    if re.search(r"\bhoje\b", texto):
        data = agora

    elif re.search(r"\bamanhã\b|\bamanha\b", texto):
        data = agora + timedelta(days=1)

    else:
        # Reconhece os dias da semana.
        dias_semana = {
            "segunda-feira": 0,
            "segunda": 0,
            "terça-feira": 1,
            "terca-feira": 1,
            "terça": 1,
            "terca": 1,
            "quarta-feira": 2,
            "quarta": 2,
            "quinta-feira": 3,
            "quinta": 3,
            "sexta-feira": 4,
            "sexta": 4,
            "sábado": 5,
            "sabado": 5,
            "domingo": 6
        }

        data = None

        for dia, numero_dia in dias_semana.items():
            if re.search(r"\b" + re.escape(dia) + r"\b", texto):
                diferenca = (numero_dia - agora.weekday()) % 7
                data = agora + timedelta(days=diferenca)
                break

        # Se não reconhecer uma expressão conhecida,
        # tenta interpretar a mensagem com dateparser.
        if data is None:
            data = dateparser.parse(
                mensagem,
                languages=["pt"],
                settings={
                    "TIMEZONE": "America/Recife",
                    "RETURN_AS_TIMEZONE_AWARE": True,
                    "PREFER_DATES_FROM": "future",
                    "RELATIVE_BASE": agora
                }
            )

    if data is None:
        await update.message.reply_text(
            "Não consegui entender a data. Tente usar 'hoje', "
            "'amanhã' ou o dia da semana."
        )
        return


    inicio = data.replace(hour=hora, minute=minuto, second=0, microsecond=0)

    # Se o horário já passou hoje, não agenda sem confirmação.
    agora = datetime.now(FUSO)
    if inicio <= agora:
        await update.message.reply_text(
            "Esse horário já passou. Informe uma data e um horário futuros."
        )
        return

    fim = inicio + timedelta(minutes=30)

    # Remove instruções comuns para formar um título simples.
    titulo = re.sub(
        r"\b(marca|marque|marcar|agenda|agende|agendar|"
        r"uma|um|reunião|compromisso|para|com|amanhã|hoje|"
        r"segunda-feira|terça-feira|quarta-feira|quinta-feira|"
        r"sexta-feira|sábado|domingo|às|as|horas)\b",
        "",
        mensagem,
        flags=re.IGNORECASE
    )
    titulo = re.sub(r"\b\d{1,2}(?::\d{2})?\s*h?\b", "", titulo)
    titulo = " ".join(titulo.split()).strip(" ,.-")

    if not titulo:
        titulo = "Compromisso"

    try:
        link = criar_evento(
            titulo=titulo.capitalize(),
            inicio=inicio.isoformat(),
            fim=fim.isoformat(),
            descricao=f"Agendado pelo Genius Agenda AI via Telegram."
        )
        await update.message.reply_text(
            "Compromisso criado com sucesso! 🎉\n\n"
            f"📌 {titulo.capitalize()}\n"
            f"📅 {inicio.strftime('%d/%m/%Y')}\n"
            f"🕒 {inicio.strftime('%H:%M')} às {fim.strftime('%H:%M')}\n"
            f"🔗 {link}"
        )
    except Exception as erro:
        print(f"Erro ao criar evento: {erro}")
        await update.message.reply_text(
            "Não consegui criar o compromisso. Confira o terminal do VS Code."
        )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("testeagenda", teste_agenda))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, receber_mensagem)
    )

    app.job_queue.run_repeating(verificar_lembretes, interval=60, first=10)
    print("Bot iniciado. Aguardando mensagens...")
    app.run_polling()


if __name__ == "__main__":
    main()

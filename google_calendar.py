from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def conectar_google_calendar():
    credenciais = None

    if os.path.exists("token.json"):
        credenciais = Credentials.from_authorized_user_file(
            "token.json", SCOPES
        )

    if not credenciais or not credenciais.valid:
        if credenciais and credenciais.expired and credenciais.refresh_token:
            credenciais.refresh(Request())
        else:
            fluxo = InstalledAppFlow.from_client_secrets_file(
                "google_credentials.json",
                SCOPES
            )

            credenciais = fluxo.run_local_server(port=0)

        with open("token.json", "w") as arquivo:
            arquivo.write(credenciais.to_json())

    servico = build(
        "calendar",
        "v3",
        credentials=credenciais
    )

    return servico



def criar_evento(titulo, inicio, fim, descricao=""):
    servico = conectar_google_calendar()

    evento = {
        "summary": titulo,
        "description": descricao,
        "start": {
            "dateTime": inicio,
            "timeZone": "America/Recife"
        },
        "end": {
            "dateTime": fim,
            "timeZone": "America/Recife"
        }
    }

    evento_criado = servico.events().insert(
        calendarId="primary",
        body=evento
    ).execute()

    return evento_criado.get("htmlLink")


def listar_eventos(inicio, fim):
    servico = conectar_google_calendar()

    resposta = servico.events().list(
        calendarId="primary",
        timeMin=inicio.isoformat(),
        timeMax=fim.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    return resposta.get("items", [])


if __name__ == "__main__":
    servico = conectar_google_calendar()

    print("Conexão com o Google Calendar realizada com sucesso!")
    
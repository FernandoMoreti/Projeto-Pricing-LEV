import pandas as pd
import re

def convertValues(value):
    valor_str = value

    v = str(value).replace("R$", "").strip()
    if "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:
        v = v.replace(",", ".")
    valor_str = float(v)

    return valor_str

import unicodedata

def remover_acentos(texto):
    processado = unicodedata.normalize('NFD', str(texto))
    return "".join(c for c in processado if unicodedata.category(c) != 'Mn').upper().strip()

def get_payload_events(events, client):

    import logging

    logger = logging.getLogger(__name__)
    all_payloads = []

    for page in events:
        for event in page:
            id = event["id"]
            attempts = event["attempts"] + 1

            try:
                client.update_status(
                    queue_id=id,
                    status_id=2,
                    process="events/operations",
                    attempts=attempts
                )
                logger.debug(f"Status atualizado para PROCESSING: event_id={id}, attempts={attempts}")
            except Exception as e:
                logger.error(f"Erro ao atualizar status para event_id={id}: {str(e)}")
                raise

            all_payloads.append({
                "payload": event["payload"],
                "event_id": id,
                "attempts": attempts
            })

    return all_payloads

def agroup_payload_in_excel(all_payloads):
    import pandas as pd
    import json
    import logging

    logger = logging.getLogger(__name__)
    list_payload = []

    for index, item in enumerate(all_payloads):
        if item in ["\"erro\"", "erro", None]:
            logger.debug(f"Payload inválido no índice {index}: {item}")
            continue

        try:
            parsed_item = json.loads(item)
            list_payload.append(parsed_item)
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON no índice {index}: {str(e)}. Item: {item[:100]}...")
            continue
        except Exception as e:
            logger.error(f"Erro inesperado ao processar payload no índice {index}: {str(e)}")
            continue

    if not list_payload:
        logger.warning("Nenhum payload válido encontrado para processar")
        return pd.DataFrame()

    df = pd.DataFrame(list_payload)

    return df

def formatar_br(valor):
    if pd.isna(valor) or valor == "" or valor is None:
        return "0,00"
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def limpar_zeros(texto):
    return re.sub(r'\b0+', '', texto)

def rename_duplicates(cols):
    counts = {}
    new_cols = []
    for col in cols:
        if col in counts:
            counts[col] += 1
            new_cols.append(f"{col}.{counts[col]}")
        else:
            counts[col] = 0
            new_cols.append(col)
    return new_cols
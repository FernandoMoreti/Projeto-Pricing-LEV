def convertValues(value):
    valor_str = value

    if type(value) == str :

        valor_str = str(value)
        valor_teste = valor_str.replace("R$", "")
        valor_teste = valor_teste.replace(".", "")
        valor_teste = valor_teste.replace(",", ".")
        valor_str = float(valor_teste)

    valor_str = round(valor_str, 2)

    return valor_str

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

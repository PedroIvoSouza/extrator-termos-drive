import json
import requests
import time
import os

SOURCE_FILE = "dados_extraidos_openai.json"
OUTPUT_FILE = "dados_prontos_para_importar.json"

def enrich_data_from_cnpj(cnpj):
    """Busca dados adicionais de um CNPJ usando a BrasilAPI."""
    if not cnpj or not isinstance(cnpj, str):
        return None
    
    cleaned_cnpj = "".join(filter(str.isdigit, cnpj))
    
    if len(cleaned_cnpj) != 14:
        return None
        
    print(f"    -> Buscando dados para o CNPJ: {cleaned_cnpj}...")
    try:
        # A BrasilAPI tem um rate limit, então uma pausa é prudente.
        # Gratuito: 3 req/min. Vamos esperar mais para garantir.
        time.sleep(21) 
        response = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cleaned_cnpj}")
        response.raise_for_status() 
        return response.json()
    except requests.RequestException as e:
        print(f"    -> Erro ao consultar a API para o CNPJ {cleaned_cnpj}: {e}")
        return None

def sanitize_and_review_data():
    """Lê os dados extraídos, enriquece, aplica regras e salva para revisão."""
    
    try:
        with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo de origem '{SOURCE_FILE}' não encontrado.")
        print(f"Por favor, execute o script 'process_documents.py' primeiro para gerar o arquivo '{SOURCE_FILE}'.")
        return

    print("Iniciando processo de sanitização e enriquecimento de dados...")
    
    final_data_for_import = []

    for i, record in enumerate(all_data):
        print(f"\n[ Processando registro {i+1}/{len(all_data)} ] Arquivo: {record.get('arquivo_origem')}")
        
        client_data = record.get('cliente')
        event_list = record.get('eventos')

        if not client_data or not event_list:
            print("    - Registro ignorado: dados de cliente ou evento ausentes.")
            continue
            
        # --- ETAPA DE ENRIQUECIMENTO E PÓS-PROCESSAMENTO ---
        
        if client_data and client_data.get('tipo_pessoa') == 'PJ':
            enriched_info = enrich_data_from_cnpj(client_data.get('documento'))
            if enriched_info:
                print("    -> Dados da API recebidos. Atualizando registro.")
                # Usa a razão social oficial da API
                client_data['nome_razao_social_oficial'] = enriched_info.get('razao_social')
                # Preenche o endereço estruturado
                client_data['cep'] = enriched_info.get('cep')
                client_data['logradouro'] = enriched_info.get('logradouro')
                client_data['numero'] = enriched_info.get('numero')
                client_data['complemento'] = enriched_info.get('complemento')
                client_data['bairro'] = enriched_info.get('bairro')
                client_data['cidade'] = enriched_info.get('municipio')
                client_data['uf'] = enriched_info.get('uf')
                # Se o responsável não foi encontrado no termo, tenta usar o da API
                if not client_data.get('nome_responsavel'):
                    # A API retorna uma lista de sócios (qsa), pegamos o primeiro
                    qsa = enriched_info.get('qsa', [])
                    if qsa:
                        client_data['nome_responsavel'] = qsa[0].get('nome_socio')
                        print(f"    -> Responsável preenchido via API: {client_data.get('nome_responsavel')}")

        if client_data and client_data.get('tipo_pessoa') == 'PF' and not client_data.get('nome_responsavel'):
             client_data['nome_responsavel'] = client_data.get('nome_razao_social')
             print("    -> Regra PF aplicada: nome do responsável preenchido.")

        # Adiciona o cliente e seus eventos à lista final
        final_data_for_import.append({
            "cliente": client_data,
            "eventos": event_list,
            "arquivo_origem": record.get('arquivo_origem'),
            "id_arquivo_drive": record.get('id_arquivo_drive')
        })

    # Salva o resultado final em um novo arquivo JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data_for_import, f, indent=2, ensure_ascii=False)

    print(f"\n--- Processo Concluído ---")
    print(f"Os dados foram sanitizados, enriquecidos e salvos em '{OUTPUT_FILE}'.")
    print("Por favor, abra este arquivo e revise os dados antes da importação final.")

if __name__ == "__main__":
    sanitize_and_review_data()
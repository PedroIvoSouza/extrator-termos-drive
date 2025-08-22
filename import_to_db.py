import json
import sqlite3
import requests
import time
import os

# Altere para "sistemacipt.db" para a importação final
DB_PATH = "sistemacipt_teste.db" 
SOURCE_FILE = "dados_prontos_para_importar.json"

def enrich_data_from_cnpj(cnpj):
    """Busca dados adicionais de um CNPJ usando a BrasilAPI."""
    if not cnpj or not isinstance(cnpj, str): return None
    cleaned_cnpj = "".join(filter(str.isdigit, cnpj))
    if len(cleaned_cnpj) != 14: return None
    print(f"    -> Buscando dados para o CNPJ: {cleaned_cnpj}...")
    try:
        time.sleep(1) 
        response = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cleaned_cnpj}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"    -> Erro ao consultar a API para o CNPJ {cleaned_cnpj}: {e}")
        return None

def import_final_data():
    """Lê os dados finais, aplica regras e os importa para o banco de dados."""
    
    if not os.path.exists(SOURCE_FILE):
        print(f"Erro: Arquivo de dados '{SOURCE_FILE}' não encontrado.")
        return

    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        all_data = json.load(f)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        print(f"Conexão com o banco de dados '{DB_PATH}' estabelecida.")
    except sqlite3.Error as e:
        print(f"Erro fatal ao conectar ao banco de dados: {e}")
        return

    clients_imported = 0
    clients_found = 0
    events_imported = 0
    records_skipped = []
    
    permissionario_cnpjs = ["01703922000128", "03370669000163", "04007216000130", "05314972000174", "05301393000197", "06935095000111", "08911934000197", "09584747000109", "10771790000162", "10882812000161", "12439637000168", "12257462000178", "13055903000111", "14876384000115", "16918665000119", "21950824000100", "22080376000196", "28207096000182", "29500928000117", "30441031000220", "31639572000149", "32860087000163", "37432689000133", "40411089000101", "43150497000137", "46731465000113"]
    keywords_governo = ["UNIVERSIDADE FEDERAL", "UFAL", "IFAL", "SECRETARIA DE ESTADO", "SESAU", "SENAI", "SEBRAE", "SENAC", "SESI", "FEPESA", "FUNDEPES", "OAB", "CRA/AL", "ASSEMBLEIA LEGISLATIVA"]

    for i, record in enumerate(all_data):
        client_data = record.get('cliente')
        event_list = record.get('eventos')
        
        print(f"\n[ Processando registro {i+1}/{len(all_data)} ] Arquivo: {record.get('arquivo_origem')}")

        if not client_data or not client_data.get('documento'):
            print("    - IGNORADO: Registro de modelo ou sem documento.")
            records_skipped.append({'arquivo': record.get('arquivo_origem'), 'motivo': 'Modelo ou sem documento'})
            continue
            
        # --- LÓGICA DE CLIENTE: ENCONTRAR OU CRIAR ---
        client_id = None
        doc_cliente = client_data.get('documento')
        
        cursor.execute("SELECT id FROM Clientes_Eventos WHERE documento = ?", (doc_cliente,))
        existing_client = cursor.fetchone()
        
        if existing_client:
            client_id = existing_client[0]
            clients_found += 1
            print(f"    -> Cliente com documento '{doc_cliente}' já existe (ID: {client_id}). Usando cliente existente.")
        else:
            # --- Aplica regras de negócio apenas para clientes novos ---
            tipo_cliente = "Geral"
            doc_cliente_clean = "".join(filter(str.isdigit, doc_cliente))
            if doc_cliente_clean in permissionario_cnpjs:
                tipo_cliente = "Permissionario"
            else:
                nome_cliente_raw = client_data.get('nome_razao_social', '')
                for keyword in keywords_governo:
                    if keyword in nome_cliente_raw.upper():
                        tipo_cliente = "Governo"
                        break
            client_data['tipo_cliente'] = tipo_cliente
            
            if client_data.get('tipo_pessoa') == 'PJ':
                # (A etapa de enriquecimento já foi feita no script anterior, aqui só usamos os dados)
                pass

            if client_data.get('tipo_pessoa') == 'PF' and not client_data.get('nome_responsavel'):
                 client_data['nome_responsavel'] = client_data.get('nome_razao_social')

            if client_data.get('tipo_pessoa') == 'PJ' and not client_data.get('nome_responsavel'):
                if client_data.get('nome_razao_social') and 2 <= len(client_data['nome_razao_social'].split()) <= 4:
                    client_data['nome_responsavel'] = client_data['nome_razao_social']
            
            try:
                cursor.execute("""
                    INSERT INTO Clientes_Eventos (
                        nome_razao_social, tipo_pessoa, documento, nome_responsavel, tipo_cliente,
                        cep, logradouro, numero, complemento, bairro, cidade, uf
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client_data.get('nome_razao_social_oficial') or client_data.get('nome_razao_social'),
                    client_data.get('tipo_pessoa'), client_data.get('documento'),
                    client_data.get('nome_responsavel'), client_data.get('tipo_cliente', 'Geral'),
                    client_data.get('cep'), client_data.get('logradouro'), client_data.get('numero'),
                    client_data.get('complemento'), client_data.get('bairro'), client_data.get('cidade'),
                    client_data.get('uf')
                ))
                client_id = cursor.lastrowid
                clients_imported += 1
                print(f"    -> NOVO Cliente '{client_data.get('nome_razao_social')}' importado com ID: {client_id}.")
            except sqlite3.Error as e:
                print(f"    - ERRO GRAVE ao inserir novo cliente: {e}")
                records_skipped.append({'arquivo': record.get('arquivo_origem'), 'motivo': f"Erro no DB ao inserir cliente: {e}"})
                continue
        
        # --- INSERÇÃO DOS EVENTOS (VINCULADOS AO CLIENTE NOVO OU EXISTENTE) ---
        if client_id and event_list:
            tipo_cliente = client_data.get('tipo_cliente', 'Geral')
            try:
                for evento in event_list:
                    valor_final = evento.get('valor_final')
                    if valor_final is None: valor_final = 0.0

                    desconto_percentual = 0.0
                    if tipo_cliente == 'Governo': desconto_percentual = 0.20
                    elif tipo_cliente == 'Permissionario': desconto_percentual = 0.60
                    
                    valor_bruto = 0.0
                    if valor_final > 0:
                        valor_bruto = valor_final / (1 - desconto_percentual) if desconto_percentual > 0 else valor_final
                    
                    cursor.execute("""
                        INSERT INTO Eventos (
                            id_cliente, nome_evento, datas_evento, total_diarias, valor_bruto, 
                            valor_final, status, data_vigencia_final, numero_processo, numero_termo,
                            espaco_utilizado, numero_oficio_sei, hora_inicio, hora_fim, tipo_desconto_auto
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        client_id, evento.get('nome_evento'), json.dumps(evento.get('datas_evento')),
                        len(evento.get('datas_evento', [])), round(valor_bruto, 2), valor_final,
                        'Pendente', evento.get('data_vigencia_final'), 
                        evento.get('numero_processo'), evento.get('numero_termo'),
                        evento.get('espaco_utilizado'), evento.get('numero_oficio_sei'),
                        evento.get('hora_inicio'), evento.get('hora_fim'), 
                        tipo_cliente if desconto_percentual > 0 else "Nenhum"
                    ))
                    events_imported += 1
                print(f"    -> {len(event_list)} evento(s) associado(s) ao cliente ID {client_id} importado(s).")
            except sqlite3.Error as e:
                print(f"    - ERRO GRAVE ao inserir evento para o cliente ID {client_id}: {e}")
                records_skipped.append({'arquivo': record.get('arquivo_origem'), 'motivo': f"Erro no DB ao inserir evento: {e}"})

    conn.commit()
    conn.close()

    print("\n\n--- RELATÓRIO FINAL DA IMPORTAÇÃO ---")
    print(f"Total de documentos processados: {len(all_data)}")
    print(f"Clientes novos criados: {clients_imported}")
    print(f"Clientes existentes reutilizados: {clients_found}")
    print(f"Eventos novos importados: {events_imported}")
    
    if records_skipped:
        print(f"\n--- Relatório de Registros Ignorados ({len(records_skipped)}) ---")
        for skipped in records_skipped:
            print(f"- Arquivo: {skipped['arquivo']} | Motivo: {skipped['motivo']}")

    print("\n✨ Processo de importação concluído! ✨")


if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        if DB_PATH == "sistemacipt_teste.db":
             print("Limpando banco de dados de teste para uma nova importação...")
             conn = sqlite3.connect(DB_PATH)
             cursor = conn.cursor()
             cursor.execute("DELETE FROM Eventos;")
             cursor.execute("DELETE FROM Clientes_Eventos;")
             cursor.execute("DELETE FROM sqlite_sequence WHERE name='Eventos';")
             cursor.execute("DELETE FROM sqlite_sequence WHERE name='Clientes_Eventos';")
             conn.commit()
             conn.close()
             print("Banco de teste limpo.")

        confirm = input(f"Este script irá modificar o banco de dados '{DB_PATH}'.\nVocê fez um backup? Deseja continuar? (s/n): ")
        if confirm.lower() == 's':
            import_final_data()
        else:
            print("Importação cancelada pelo usuário.")
    else:
        print(f"Erro: Banco de dados '{DB_PATH}' não encontrado no diretório.")
import json

def validate_data(filepath="dados_extraidos_openai.json"):
    """
    Lê o arquivo JSON com os dados extraídos pela IA e gera um relatório de campos faltantes.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Erro: O arquivo '{filepath}' não foi encontrado.")
        print("Por favor, execute o script 'process_documents.py' primeiro.")
        return

    total_records = len(data)
    if total_records == 0:
        print("Nenhum dado encontrado no arquivo para validar.")
        return
    
    total_events = sum(len(record.get('eventos', [])) for record in data)

    # Dicionário para contar os campos faltantes
    missing_counts = {
        'cliente.nome_razao_social': 0,
        'cliente.documento': 0,
        'cliente.tipo_pessoa': 0,
        'cliente.nome_responsavel': 0,
        'evento.nome_evento': 0,
        'evento.datas_evento': 0,
        'evento.valor_final': 0,
        'evento.espaco_utilizado': 0
    }

    # Itera sobre cada documento extraído
    for record in data:
        # Validação do Cliente
        cliente = record.get('cliente', {})
        if not cliente or not cliente.get('nome_razao_social'): missing_counts['cliente.nome_razao_social'] += 1
        if not cliente or not cliente.get('documento'): missing_counts['cliente.documento'] += 1
        if not cliente or not cliente.get('tipo_pessoa'): missing_counts['cliente.tipo_pessoa'] += 1
        if not cliente or not cliente.get('nome_responsavel'): missing_counts['cliente.nome_responsavel'] += 1
        
        # Validação do(s) Evento(s)
        eventos = record.get('eventos', [])
        if not eventos:
             # Se a lista de eventos estiver vazia, todos os campos de evento contam como faltantes
            for key in missing_counts:
                if key.startswith('evento.'):
                    missing_counts[key] += 1
        else:
            for evento in eventos:
                if not evento.get('nome_evento'): missing_counts['evento.nome_evento'] += 1
                # Verifica se a lista de datas está vazia ou ausente
                if not evento.get('datas_evento'): missing_counts['evento.datas_evento'] += 1
                if evento.get('valor_final') is None: missing_counts['evento.valor_final'] += 1
                if not evento.get('espaco_utilizado'): missing_counts['evento.espaco_utilizado'] += 1
    
    # Imprime o Relatório Final
    print("--- Relatório de Qualidade da Extração com OpenAI ---")
    print(f"Total de documentos analisados: {total_records}")
    print(f"Total de eventos individuais identificados: {total_events}")
    print("\n--- Contagem de Campos Nulos ou Vazios ---")
    print("(Mostrando apenas campos que faltaram ao menos uma vez)\n")

    found_missing = False
    for field, count in missing_counts.items():
        if count > 0:
            found_missing = True
            target_total = total_events if field.startswith('evento.') else total_records
            print(f"- {field}: {count} de {target_total} registros.")
    
    if not found_missing:
        print("🎉🎉🎉 RESULTADO PERFEITO! Nenhum campo essencial foi identificado como faltante em toda a base de dados!")

if __name__ == "__main__":
    validate_data()
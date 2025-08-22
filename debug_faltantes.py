import json
import os

# Reutilizaremos as funções de conexão e download do nosso script principal
from process_documents import get_drive_service, get_docx_text

def debug_missing_fields(input_file="dados_extraidos_openai.json", output_file="debug_faltantes.txt", field_to_debug="cliente.nome_responsavel"):
    """
    Identifica registros com um campo específico faltando, baixa os documentos
    originais e compila seus textos em um único arquivo de depuração.
    """
    print(f"Iniciando a depuração do campo faltante: '{field_to_debug}'")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo de dados '{input_file}' não encontrado.")
        return

    # Filtra para encontrar os registros com o campo faltante
    keys = field_to_debug.split('.')
    records_with_missing_data = []
    for record in all_data:
        value = record
        try:
            for key in keys:
                value = value[key]
            # Considera faltante se for None ou uma string vazia
            if not value:
                records_with_missing_data.append(record)
        except (KeyError, TypeError):
            # Se a estrutura de chaves não existir, também é considerado faltante
            records_with_missing_data.append(record)

    if not records_with_missing_data:
        print(f"Nenhum registro encontrado com o campo '{field_to_debug}' faltando. Ótimo trabalho!")
        return

    print(f"Encontrados {len(records_with_missing_data)} documentos com o campo '{field_to_debug}' faltante.")
    print("Baixando o conteúdo desses documentos para análise...")

    # Conecta ao Google Drive
    service = get_drive_service()
    if not service:
        print("Não foi possível conectar ao Google Drive.")
        return

    # Salva o texto completo dos documentos problemáticos em um arquivo
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, record in enumerate(records_with_missing_data):
            file_name = record.get('arquivo_origem', 'Nome não encontrado')
            file_id = record.get('id_arquivo_drive')

            if not file_id:
                f.write(f"\n--- ERRO: Documento '{file_name}' não possui ID do Drive registrado. ---\n\n")
                continue

            print(f"  ({i+1}/{len(records_with_missing_data)}) Baixando: {file_name}")
            
            f.write(f"======================================================================\n")
            f.write(f"DOCUMENTO: {file_name}\n")
            f.write(f"ID DO DRIVE: {file_id}\n")
            f.write(f"======================================================================\n\n")
            
            text_content = get_docx_text(service, file_id)
            
            if text_content:
                f.write(text_content)
                f.write("\n\n")
            else:
                f.write("--- FALHA AO BAIXAR O CONTEÚDO DESTE DOCUMENTO ---\n\n")

    print(f"\nAnálise concluída! O texto completo dos {len(records_with_missing_data)} documentos foi salvo em '{output_file}'.")
    print("Por favor, revise este arquivo para determinar se a informação realmente está ausente nos textos.")

if __name__ == "__main__":
    debug_missing_fields()
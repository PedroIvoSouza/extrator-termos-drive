-- Remove a tabela antiga se ela existir de uma tentativa anterior, para evitar erros
DROP TABLE IF EXISTS Clientes_Eventos_old;

-- Renomeia a tabela atual para um backup temporário
ALTER TABLE Clientes_Eventos RENAME TO Clientes_Eventos_old;

-- Cria a nova tabela 'Clientes_Eventos' com a estrutura correta, permitindo email nulo
CREATE TABLE "Clientes_Eventos" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "nome_razao_social" TEXT NOT NULL,
    "tipo_pessoa" TEXT NOT NULL CHECK(tipo_pessoa IN ('PF', 'PJ')),
    "documento" TEXT NOT NULL UNIQUE,
    "email" TEXT, -- << ALTERAÇÃO: email agora pode ser NULO
    "telefone" TEXT,
    "endereco" TEXT,
    "nome_responsavel" TEXT,
    "senha_hash" TEXT,
    "tipo_cliente" TEXT NOT NULL DEFAULT 'Geral' CHECK(tipo_cliente IN ('Geral', 'Governo', 'Permissionario')),
    "token_definir_senha" TEXT,
    "documento_responsavel" TEXT,
    "cep" TEXT, "logradouro" TEXT, "numero" TEXT, "complemento" TEXT, "bairro" TEXT, "cidade" TEXT, "uf" TEXT
);

-- Copia todos os dados da tabela antiga para a nova
INSERT INTO Clientes_Eventos (id, nome_razao_social, tipo_pessoa, documento, email, telefone, endereco, nome_responsavel, senha_hash, tipo_cliente, token_definir_senha, documento_responsavel, cep, logradouro, numero, complemento, bairro, cidade, uf)
SELECT id, nome_razao_social, tipo_pessoa, documento, email, telefone, endereco, nome_responsavel, senha_hash, tipo_cliente, token_definir_senha, documento_responsavel, cep, logradouro, numero, complemento, bairro, cidade, uf FROM Clientes_Eventos_old;

-- Remove a tabela de backup antiga
DROP TABLE Clientes_Eventos_old;
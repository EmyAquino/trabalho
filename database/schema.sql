-- Schema PostgreSQL do PEnsE-Submite (conforme diagrama de 6 tabelas)

CREATE TABLE IF NOT EXISTS funcoes (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    funcao_id INTEGER NOT NULL REFERENCES funcoes(id),
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    cpf VARCHAR(14) NOT NULL DEFAULT '',
    instituicao VARCHAR(150) NOT NULL DEFAULT '',
    senha VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS modalidades_formularios (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS autores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    area VARCHAR(100) NOT NULL,
    cidade VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS instituicoes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    cidade VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS formularios (
    id SERIAL PRIMARY KEY,
    autor_id INTEGER NOT NULL REFERENCES autores(id),
    modalidade_id INTEGER NOT NULL REFERENCES modalidades_formularios(id),
    instituicao_id INTEGER NOT NULL REFERENCES instituicoes(id),
    titulo VARCHAR(50) NOT NULL,
    resumo TEXT NOT NULL,
    arquivo BYTEA NOT NULL,
    palavra_chave VARCHAR(100) NOT NULL,
    area_conhecimento VARCHAR(255) NOT NULL,
    data_envio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'Pendente'
);

-- Seed inicial de funções e modalidades
INSERT INTO funcoes (descricao)
SELECT 'Admin' WHERE NOT EXISTS (SELECT 1 FROM funcoes WHERE descricao = 'Admin');

INSERT INTO funcoes (descricao)
SELECT 'normal' WHERE NOT EXISTS (SELECT 1 FROM funcoes WHERE descricao = 'normal');

INSERT INTO modalidades_formularios (descricao)
SELECT 'Ensino' WHERE NOT EXISTS (SELECT 1 FROM modalidades_formularios WHERE descricao = 'Ensino');

INSERT INTO modalidades_formularios (descricao)
SELECT 'Pesquisa' WHERE NOT EXISTS (SELECT 1 FROM modalidades_formularios WHERE descricao = 'Pesquisa');

INSERT INTO modalidades_formularios (descricao)
SELECT 'Extensão' WHERE NOT EXISTS (SELECT 1 FROM modalidades_formularios WHERE descricao = 'Extensão');

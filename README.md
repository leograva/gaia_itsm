# GAIA ITSM

Agente de IA para **gestão de incidentes** integrado ao **ServiceNow**, construído com o [Google ADK](https://google.github.io/adk-docs/).

---

## Visão Geral

O GAIA ITSM é um agente conversacional que permite a analistas e usuários consultar incidentes no ServiceNow usando linguagem natural. O agente interpreta a solicitação, escolhe a ferramenta adequada e retorna os dados de forma organizada.

**Exemplos de interações:**

- *"Qual o status do incidente INC0012345?"*
- *"Mostre os incidentes abertos do João Silva"*
- *"Liste os incidentes em andamento do grupo de suporte"*
- *"Quais foram as últimas atualizações do INC0009876?"*

---

## Arquitetura

```
gaia_itsm/
├── agent.py              # Definição do agente principal (root_agent)
├── tools/
│   ├── __init__.py       # Exporta todas as tools
│   └── servicenow.py     # Ferramentas de integração com a API do ServiceNow
├── .env                  # Variáveis de ambiente (não versionado)
├── __init__.py
└── README.md
```

### Componentes

| Componente | Responsabilidade |
|---|---|
| `agent.py` | Define o agente GAIA com modelo Gemini e instruções em PT-BR |
| `tools/servicenow.py` | Integração com a Table API REST do ServiceNow |
| `.env` | Credenciais e configurações de ambiente |

---

## Ferramentas (Tools)

### `get_incident_by_number(incident_number)`
Busca um incidente específico pelo número (ex: `INC0012345`).

**Retorna:** número, descrição, estado, prioridade, urgência, impacto, solicitante, responsável, grupo, datas de abertura e resolução.

---

### `search_incidents_by_caller(caller_name, limit, state)`
Busca incidentes associados a um solicitante pelo nome.

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `caller_name` | string | Nome completo ou parcial do solicitante |
| `limit` | int | Máximo de resultados (padrão: 10, máx: 50) |
| `state` | string | Filtro opcional de estado (ver tabela abaixo) |

---

### `search_incidents_by_state(state, limit, assignment_group)`
Lista incidentes pelo estado atual.

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `state` | string | Estado do incidente (ver tabela abaixo) |
| `limit` | int | Máximo de resultados (padrão: 10, máx: 50) |
| `assignment_group` | string | Filtro opcional por grupo de atribuição |

---

### `get_incident_updates(incident_number, limit)`
Retorna o histórico de notas de trabalho e comentários de um incidente.

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `incident_number` | string | Número do incidente |
| `limit` | int | Máximo de entradas (padrão: 10, máx: 50) |

---

### Estados de Incidente

| Valor | Código ServiceNow |
|---|---|
| `new` | 1 |
| `in_progress` | 2 |
| `on_hold` | 3 |
| `resolved` | 6 |
| `closed` | 7 |
| `canceled` | 8 |

---

## Configuração

### 1. Pré-requisitos

- Python 3.10+
- [Google ADK](https://google.github.io/adk-docs/) instalado
- Instância ServiceNow (Developer, staging ou produção)

### 2. Instalação de dependências

```bash
pip install google-adk requests
```

### 3. Variáveis de ambiente

Crie ou edite o arquivo `.env` na raiz do projeto:

```dotenv
# Google ADK
GOOGLE_API_KEY=sua_chave_google_aqui

# ServiceNow — autenticação básica
SERVICENOW_INSTANCE=sua_instancia        # ex: mycompany (sem .service-now.com)
SERVICENOW_USERNAME=seu_usuario
SERVICENOW_PASSWORD=sua_senha

# ServiceNow — autenticação por token (opcional, tem prioridade sobre basic auth)
# SERVICENOW_API_TOKEN=seu_bearer_token
```

> **Nunca versione o arquivo `.env`** — ele já está no `.gitignore`.

### 4. Executando o agente

```bash
adk run gaia_itsm
```

Ou via interface web:

```bash
adk web
```

---

## Autenticação com o ServiceNow

A integração suporta dois métodos de autenticação com a [Table API](https://developer.servicenow.com/dev.do#!/reference/api/vancouver/rest/c_TableAPI):

| Método | Variáveis necessárias |
|---|---|
| Basic Auth | `SERVICENOW_USERNAME` + `SERVICENOW_PASSWORD` |
| Bearer Token | `SERVICENOW_API_TOKEN` |

Se `SERVICENOW_API_TOKEN` estiver definido, ele tem prioridade sobre o Basic Auth.

---

## Boas Práticas de Segurança

- Use contas de serviço com permissão mínima necessária (somente leitura em `incident` e `sys_journal_field`).
- Prefira token-based auth em ambientes de produção.
- Nunca exponha credenciais em código-fonte ou logs.

---

## Licença

MIT

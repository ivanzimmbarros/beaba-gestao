# Épico 23 — Ambiente de gestão de utilizadores, acessos e auditoria

**ID:** `2026-05-09_E23_gestao_usuarios_acessos_audit`  
**Fase 0 (actual):** Plano faseado, alinhamento a `.cursorrules` (Constituição BeaBá Sereno + Template Master refletido no repositório), governança E17/E14 e suíte de testes em três camadas — **sem alteração a código de produção** até **aprovação explícita do Diretor** no chat (ex.: **PROSSIGA** por fase ou por tranche acordada).

## 1. Contexto técnico actual (linha de base)

- **Autenticação:** `src/ui/page_auth.py` — login e-mail/senha, MFA por e-mail, `must_change_password` na tabela `usuarios` (`src/modules/auth_db.py`).
- **Perfis em código:** `admin` e `colaborador` em `create_usuario`; RBAC em `src/ui/shell_sidebar.py` e gates em `src/app.py` (`bea_rbac_*`).
- **Requisito novo do Diretor:** perfil **«utilizador»** com âmbito **apenas** Painel de Vendas + agendamentos (hoje `colaborador` ainda vê Início, Catálogo, Colaboradores, etc.). O plano prevê **decisão de modelagem** (novo valor `usuario` vs. redefinição de `colaborador`) na Fase 1.
- **Histórico de senhas:** `update_password_clear_must_change` já impede repetir a **senha actual**; o pedido exige **não reutilizar a última senha** — provável extensão com coluna `senha_hash_anterior` (ou tabela de histórico curta, p.ex. últimas N).

## 2. Objectivos de negócio (síntese)

| # | Objectivo |
|---|-----------|
| A | «Esqueci / redefinir senha» na página inicial: gerar senha temporária, enviar por e-mail ao endereço cadastrado, forçar troca no próximo acesso, bloquear reutilização da última senha. |
| B | Área administrativa de **gestão de utilizadores e acessos**: criar, desactivar, editar nome / apelido / e-mail; listagem tabular com perfil, data de criação, indicador de senha já alterada (pós-temporária ou pós-primeiro login). |
| C | RBAC explícito: **administrador** — todo o sistema; **utilizador** — só vendas + agendamentos (e rotas derivadas estritamente necessárias, p.ex. APIs internas da mesma página). |
| D | **Auditoria** de mutações: data/hora, actor, operação, local (página/módulo), entidade e descrição do antes/depois (criar / alterar / apagar). |

## 3. Conformidade obrigatória (execução futura)

- **UI:** Constituição Visual em `.cursorrules` (horizonte 300px/150px, ilhas, sidebar Sálvia, tipografia, badges).
- **Qualidade:** actualizar **toda** a suíte — testes unitários, E2E de lógica em `tests/`, smoke UI (`tests/smoke_test_ui.py` + `pytest.ini` alinhados a novas páginas/rotas).
- **Pré push:** `.\venv\Scripts\Activate.ps1` e `python -m pytest tests/ -v` com **100% PASS** nas três camadas antes de commit/push (norma `.cursorrules`).
- **Backup/restore:** rever `scripts/backup_sqlite.py`, restore, workflows e inventário D1–D4 após cada ciclo que toque em esquema ou dados críticos.
- **Sincronização:** working copy → commit → push `origin/develop`; CI verde; alinhar local vs cloud no fecho do PC.
- **Relatório final:** documentar por etapa o detectado / feito / resultado (formato do fluxo de governança em vigor).

## 4. Faseamento lógico e entregas

### Fase 0 — Plano e aprovação (actual)

- **Entrega:** este documento + confirmação do Diretor no chat.
- **Saída:** decisão de avanço para Fase 1.

### Fase 1 — Modelo de dados e políticas

- **Entregas:**
  - Decisão gravada: perfil `usuario` (recomendado, coerente com o pedido) **ou** migração semântica de `colaborador` → `usuario` com script de dados.
  - Migração SQLite: campos em `usuarios` se necessário (ex.: `apelido`, `senha_hash_anterior`, `password_changed_at` / reutilizar `must_change_password` + metadados).
  - Tabela `auditoria_eventos` (ou nome alinhado ao projeto): `id`, `criado_em`, `actor_user_id`, `actor_email`, `operacao`, `recurso`, `recurso_id`, `pagina_ou_modulo`, `payload_json` (antes/depois redigido conforme LGPD mínima).
  - Módulo Python único de escrita de auditoria (evitar duplicação).
- **Critério de aceite:** migrações idempotentes; testes unitários do módulo de auditoria e de política de senha.

### Fase 2 — Reset de senha na página inicial

- **Entregas:**
  - UI na ilha de login: fluxo «Redefinir senha» (e-mail), mensagens genéricas para enumeração de contas.
  - Geração de senha temporária segura, hash na BD, `must_change_password=1`, envio SMTP reutilizando infra existente (`send_mfa_email` / configuração `.env`).
  - Invalidação de sessões MFA pendentes / tokens relevantes após reset.
  - Regra: na primeira sessão após reset, **obrigatório** `render_force_password_change`; nova senha ≠ última (hash anterior).
- **Critério de aceite:** testes E2E de lógica do fluxo (DB + funções); smoke UI do novo controlo no ecrã de login.

### Fase 3 — RBAC «administrador» vs «utilizador»

- **Entregas:**
  - `shell_sidebar.py`: itens visíveis só **Painel de Vendas** + **Clientes e Agendamentos** (ou página dedicada só agendamentos, se o produto separar) para `usuario`.
  - `app.py`: bloqueio de `st.session_state.page` por perfil (defesa em profundidade); mensagem alinhada ao Master.
  - Matriz de permissões documentada no código (constante única) para evitar divergência sidebar vs router.
- **Critério de aceite:** testes de navegação por perfil; smoke UI valida menu e redirecionamento.

### Fase 4 — UI de gestão de utilizadores (apenas admin)

- **Entregas:**
  - Nova página `page_*` (nome a fixar) registada em `app.py`, sidebar só para `admin`, layout BeaBá Sereno (tabela dentro de ilha; acções em formulários claros).
  - Operações: criar (senha inicial ou fluxo por convite — a fechar na Fase 1), desactivar (`ativo=0`), editar nome, apelido, e-mail, perfil.
  - Listagem: todos os registos (activos e inactivos distinguíveis), colunas perfil, `data_cadastro`, estado «senha definitiva vs pendente».
  - Todas as operações registadas na auditoria.
- **Critério de aceite:** testes unitários dos serviços DB; smoke UI percorre listagem + uma edição fictícia (AppTest).

### Fase 5 — Auditoria alargada (mutações globais)

- **Entregas:**
  - Inventário incremental: pontos de escrita nas páginas e módulos (vendas, agendamentos, catálogo, etc.) — implementação por **ondas** com prioridade (dados financeiros / PII primeiro).
  - Helper invocado nos handlers de submit / delete existentes (sem reescrever UI desnecessariamente).
  - UI admin opcional «Consultar auditoria» (filtros por data, utilizador, módulo) — pode ser Fase 5b se o Diretor preferir MVP só com BD + export.
- **Critério de aceite:** pelo menos cobertura completa das operações da **nova** área de utilizadores + amostra representativa nas páginas críticas acordadas; testes que asseguram que `INSERT` em auditoria ocorre.

### Fase 6 — QA, backup, governança e fecho

- **Entregas:**
  - `python -m pytest tests/ -v` e rotação de scripts backup/restore/workflow conforme E17.
  - Actualização `CADERNO_TESTES_MASTER` / painéis nos PCs aplicáveis (EQUIPE).
  - Relatório final estruturado (detectado / feito / resultado / riscos residuais).
- **Critério de aceite:** CI verde; push `develop`; local/cloud alinhados.

## 5. Riscos e decisões em aberto

- **Colisão de nomes:** «colaborador» no domínio de **utilizadores** vs tabela `colaboradores` (staff da clínica). Manter claro na UI e no código.
- **E-mail único:** reset e MFA assumem e-mail válido; utilizador sem e-mail cadastrado pode ficar bloqueado — política a confirmar.
- **Auditoria completa** em todas as páginas é ampla; o faseamento em **Fase 5** com ondas evita «big bang» e mantém entregas testáveis.

## 6. Pedido ao Diretor

1. Aprovar o **faseamento** e a **prioridade** da Fase 5 (MVP só gestão de utilizadores vs. auditoria alargada imediata).  
2. Confirmar que **«Clientes e Agendamentos»** satisfaz o requisito de «área de agendamento» para o perfil **utilizador**, ou especificar página exacta.  
3. Autorizar, após esta aprovação, a execução técnica com **PROSSIGA** (global ou por fase).

---

**Estado:** Fase 0 — aguardando aprovação. **Nenhuma execução de código** foi iniciada na abertura deste épico além da criação deste dossier de plano.

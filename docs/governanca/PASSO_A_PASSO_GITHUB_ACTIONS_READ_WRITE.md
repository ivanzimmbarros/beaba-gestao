# Passo a passo — permissões de escrita do GitHub Actions (Diretor)

**Repositório:** `ivanzimmbarros/beaba-gestao`  
**Objectivo:** o `GITHUB_TOKEN` dos workflows poder **fazer push** na branch `develop` (telemetria `docs/governanca/telemetry/backup_dr_history.json`). Sem isto, o `git pull` local **não** recebe ficheiros novos mesmo com runs **verdes**.

**Documentação oficial (inglês):** [Managing GitHub Actions settings for a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository#configuring-the-default-github_token-permissions) — secção *Setting the permissions of the GITHUB_TOKEN* / *Workflow permissions*.

---

## 1. Abrir a página certa no GitHub

1. Entre em **https://github.com/ivanzimmbarros/beaba-gestao** (navegador, sessão com permissão de **administrador** ou **owner** do repositório).
2. No topo do repositório, clique no separador **Settings** (Definições).  
   - Se **não** vir *Settings*, a sua conta **não** tem permissão para alterar isto — terá de o fazer o owner da organização/conta ou pedir acesso.
3. Na **barra lateral esquerda**, clique em **Actions**.
4. Na sub-área que abre, clique em **General** (é a primeira opção sob *Actions*).

**Caminho resumido:** `Repositório → Settings → Actions → General`.

---

## 2. Secção “Workflow permissions” (o que deve ver)

Na mesma página (a fazer scroll para baixo, por baixo de *Actions permissions*), localize o bloco com o título **Workflow permissions** (em contas em português o GitHub pode mostrar equivalente; o bloco trata das permissões **predefinidas** do `GITHUB_TOKEN`).

Segundo a documentação GitHub, deve **escolher** entre:

| Opção (interface normalmente em inglês) | Efeito |
|:---|:---|
| **Read and write permissions** | Permissão de **leitura e escrita** — necessário para o workflow fazer **commit/push** na `develop`. **É esta que deve ficar seleccionada.** |
| **Read repository contents and packages permissions** | Só **leitura** em `contents` (e pacotes) — **impede** o push da telemetria. |

**Passos:**

1. Seleccione o botão de opção **Read and write permissions**.
2. **Obrigatório:** clique em **Save** no fim da secção (ou no botão verde **Save** da página, conforme o layout) para **gravar**. Sem *Save*, a alteração **não** entra em vigor.

---

## 3. (Opcional) “Allow GitHub Actions to create and approve pull requests”

Ainda sob **Workflow permissions**, pode existir a opção **Allow GitHub Actions to create and approve pull requests**.  
Para o nosso caso (push directo de `github-actions[bot]` na `develop`), **não** é normalmente obrigatória; o crítico é **Read and write permissions** + *Save*.

---

## 4. Organização / empresa (se aplicável)

Se o repositório pertencer a uma **organização** ou **GitHub Enterprise**:

- A organização pode **forçar** “só leitura” a todos os repositórios. Nesse caso, na página do repositório a opção **Read and write** pode aparecer **desactivada** ou ser reposta pela política da org.  
- O owner da organização deve seguir: [Disabling or limiting GitHub Actions for your organization](https://docs.github.com/en/organizations/managing-organization-settings/disabling-or-limiting-github-actions-for-your-organization) e alinhar a política de **Workflow permissions** ao nível da org.

---

## 5. Proteção da branch `develop`

Se existir **branch protection** em `develop` que **bloqueie** pushes de `github-actions[bot]` ou exija PR obrigatório sem excepção para bots, o push da telemetria **falha** mesmo com *Read and write*.  
Nesse caso, nas regras da branch, é preciso **permitir** o bypass para GitHub Actions / o bot, ou ajustar a regra (quem gere o repositório + Diretor).

---

## 6. Como confirmar no GitHub (separador **Code**) — “prova de realidade”

Depois de **Save** e de a EQUIPE disparar um run manual de `backup_hourly`:

1. Abra **https://github.com/ivanzimmbarros/beaba-gestao/tree/develop** (branch **develop**).
2. Clique em **commits** (ou **X commits** / histórico de commits na `develop`).  
   URL directa típica: `https://github.com/ivanzimmbarros/beaba-gestao/commits/develop`
3. O commit mais recente **deve** ser de **github-actions\[bot\]** com mensagem do tipo:  
   `chore(telemetry): backup beaba-sqlite-backup-encrypted run <número>`  
4. Ao abrir esse commit, deve listar alteração em **`docs/governanca/telemetry/backup_dr_history.json`**.

Se o run em **Actions** estiver verde **mas** não aparecer **nenhum** commit novo de `github-actions[bot]` na `develop`, o problema continua a ser **permissão de escrita** ou **branch protection**.

---

## 7. Confirmação no PC do Diretor (único critério para levantar Grounding)

No clone local (PowerShell ou terminal), na pasta do repositório:

```text
git fetch origin
git pull origin develop
```

O `git pull` deve **baixar** pelo menos um commit novo (ficheiros alterados). Se aparecer **Already up to date** e no GitHub há commit novo do bot, o clone pode estar noutra pasta, noutro remoto, ou ainda sem *fetch*.

---

## 8. Referência visual (sem captura de ecrã)

O GitHub muda o desenho com frequência. Use sempre:

- **Settings → Actions → General → Workflow permissions → Read and write permissions → Save**

Se a sua interface estiver em **português**, procure o equivalente a permissões de workflow e **leitura e escrita** para o GitHub Actions.

---

*Documento criado pela EQUIPE (governança E17.1). Actualizar se a GitHub alterar os rótulos da UI.*

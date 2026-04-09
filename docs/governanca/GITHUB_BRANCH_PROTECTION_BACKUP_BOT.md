# Branch protection — permitir push de telemetria do `github-actions[bot]` na `develop`

O workflow `backup_encrypt_callable` faz **commit + push** em `develop` (`telemetry_git_branch`). Se a `develop` tiver **branch protection** com “Require a pull request before merging”, o push do bot pode ser **rejeitado**.

## O que configurar (Diretor / owner do repositório)

1. Abrir **https://github.com/ivanzimmbarros/beaba-gestao/settings/branches**
2. Em **Branch protection rules**, editar a regra que cobre **`develop`** (ou criar uma específica para `develop`).
3. Procurar **“Allow specified actors to bypass required pull requests”** (ou equivalente em português: permitir que actores específicos contornem as regras).
4. Activar e adicionar:
   - **GitHub Actions** (se disponível na lista), e/ou
   - Utilizador **`github-actions[bot]`** conforme a UI permitir.
5. Alternativa: **“Restrict who can push to matching branches”** e incluir o bot — depende da política desejada.
6. Gravar a regra.

Documentação: [About branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

## Nota

Isto só pode ser feito na **interface GitHub** (ou API com token de admin); não é definido no ficheiro YAML do workflow.

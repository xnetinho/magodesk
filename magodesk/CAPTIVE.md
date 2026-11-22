# Cliente cativo

Este fork compila um cliente que aponta sempre para um único servidor, sem troca pela interface.

## Como é configurado

Lidos na compilação por `option_env!` em `magodesk/captive.rs` (Settings → Secrets and variables → Actions):

| Nome | Tipo | Valor |
|---|---|---|
| `RD_HOST` | secret | domínio do servidor, sem porta |
| `RD_KEY` | secret | chave **pública** do servidor (`id_ed25519.pub`) |
| `RD_APP_NAME` | **variável** | nome do produto, só letras e números (ex.: `MagoDesk`) |

`RD_APP_NAME` é variável, não secret: o nome aparece no `.exe`, e um secret seria mascarado (`***`) nos logs.

A chave privada nunca entra aqui. Sem `RD_HOST` e `RD_KEY` o build não é cativo, e os jobs de release do workflow falham.

## O que fica travado

- Servidor, chave, `relay-server` e `api-server` (em `OVERWRITE_SETTINGS`).
- Verificação e instalação de atualização do upstream.
- O servidor no nome do `.exe` e o atalho `id@outroservidor` são ignorados.
- **Login, agenda de endereços e grupos ficam desligados** (`disable-account=Y` em `HARD_SETTINGS`, a mesma tabela que o `custom.txt` de um cliente personalizado preenche). O `hbbs`/`hbbr` oficial não tem API de contas, então o botão "Login" só levaria a um formulário que nunca funciona. A opção some em todas as telas que o upstream já protege com `isDisableAccount`: configurações do desktop e do celular, barra de ferramentas e as abas de agenda e grupos. Para voltar a mostrar o login (por exemplo, com um servidor que tenha API), remova `hard_options()` de `magodesk/captive.rs`.

## Proxy e WebSocket

- O proxy fica visível e editável (HTTP, HTTPS e SOCKS5, com usuário e senha Basic).
- `allow-websocket` liga sozinho quando há proxy e desliga quando não há. Com WebSocket o cliente usa `wss://<RD_HOST>/ws/id` e `/ws/relay`, pela porta 443, sempre via relay.
- `api-server` vale `https://<RD_HOST>` só para o esquema `wss`. Nenhuma API é chamada (`register-device=N`).
- NTLM e Kerberos não são suportados (`libs/hbb_common/src/proxy.rs`).

## Aviso do Windows e verificação do arquivo

Os pacotes **não têm assinatura de código**: o projeto é pessoal, sem fins comerciais e sem orçamento para certificado. O Windows mostra "O Windows protegeu o computador" e o usuário escolhe *Mais informações > Executar assim mesmo*. O Windows 11 recém-instalado pode bloquear sem esse botão (*Smart App Control*). A pesquisa de alternativas gratuitas está no `ESTADO.md` (pendência de assinatura).

Depois que os pacotes sobem, o job `release-notes` do workflow:
- gera `SHA256SUMS.txt` com o hash de cada `.exe`, `.msi` e `.apk` e o anexa à release;
- acrescenta à descrição da release o passo a passo de instalação e uma tabela com os hashes.

O texto que você escrever na descrição é preservado: o job só reescreve o bloco entre `<!-- magodesk-install:begin -->` e `<!-- magodesk-install:end -->`, então rodar de novo substitui o bloco em vez de duplicá-lo. O código está em `magodesk/release_notes.py` (`sums` e `body`).

Conferir um arquivo baixado, no PowerShell: `Get-FileHash .\magodesk-<versão>-x86_64.exe -Algorithm SHA256`.

## macOS

Sem conta Apple paga (US$ 99/ano), o app **não tem** Developer ID nem notarização. O job `build-for-macOS` gera o `.dmg` com **assinatura ad hoc**: o Apple Silicon só executa código assinado, e a assinatura local satisfaz isso. O Gatekeeper ainda avisa na primeira execução ("não pôde verificar o desenvolvedor"). A descrição da release traz o passo a passo (*Ajustes do Sistema > Privacidade e Segurança > Abrir Mesmo Assim*; no macOS 15 em diante o atalho do botão direito deixou de existir; alternativa `xattr -dr com.apple.quarantine`).

Se um dia houver os secrets `MACOS_P12_BASE64`, `MACOS_P12_PASSWORD`, `MACOS_CODESIGN_IDENTITY` e `MACOS_NOTARIZE_JSON`, o workflow volta ao caminho do upstream (Developer ID + notarização com `rcodesign`) e o passo ad hoc é pulado.

- **Marca:** `magodesk/branding.py` roda em todo job que compila, antes do build (veja "Como o fork é organizado"). No macOS grava `PRODUCT_NAME`, o identificador `<prefixo>.<app>` e o esquema de link (`magodesk://`).
- **Arquivos:** `magodesk-<tag>-x86_64.dmg` e `magodesk-<tag>-aarch64.dmg`. O `x86_64` roda em Mac Intel; o `aarch64`, em Apple Silicon.
- **Permissões:** o app precisa de Acessibilidade e Gravação de Tela. Como a assinatura ad hoc muda a cada versão, o macOS pode pedir essas permissões de novo depois de uma atualização.
- **Quando roda:** com release publicada, ou disparo manual com `windows-only=false`.
- **Validado:** o `rc4` foi instalado e usado num Mac que já tinha o RustDesk oficial instalado, e funcionou. O MagoDesk usa identificador, pasta de configuração, pasta de logs, socket e serviços próprios, então convive com o RustDesk. Se os dois estiverem abertos, podem disputar a captura de tela e o mouse: feche um antes de abrir o outro.
- **Limite:** o iOS está **fora de escopo** (o job do upstream existe, mas não é gerado aqui).

## Nome do produto (rebranding)

`RD_APP_NAME` define o nome do executável (`MagoDesk.exe`), o pipe IPC, a pasta de configuração, o nome do serviço e os metadados do arquivo. Isso permite instalar o cliente ao lado de um RustDesk oficial sem colisão. O nome é gravado em `APP_NAME` dentro de `captive::apply()`, antes de qualquer uso de `Config`. Como o nome deixa de ser `RustDesk`, `is_custom_client()` passa a ser verdadeiro; ver `CONTEXT.md` para o efeito nos padrões.

## Versão e release

A **tag define a versão**. `magodesk/set_version.py <tag>` grava a versão em `Cargo.toml`, `libs/portable/Cargo.toml`, `Cargo.lock` e `flutter/pubspec.yaml` antes de cada build; o sufixo `-rcN` fica só na tag e nos nomes dos arquivos, porque o binário, o MSI e o Flutter exigem `X.Y.Z` numérico. A base do produto é `1.0.0`.

| Tag | Uso | Release | Versão no app |
|---|---|---|---|
| `v1.0.0-rc1` | teste | **pre-release** | 1.0.0 |
| `v1.0.0-rc2` | teste | pre-release | 1.0.0 |
| `v1.0.0-rc3`, `v1.0.0-rc4` | teste | pre-release | 1.0.0 |
| `v1.0.0` | final | release normal | 1.0.0 |
| `v1.0.1` | final | release normal | 1.0.1 |

### `versionCode` do Android

`magodesk/set_version.py` calcula a base `MAJOR*1000000 + MINOR*10000 + PATCH*100 + (rcN, ou 99 na final)`. O Flutter ainda **soma um prefixo por arquitetura** nos APKs separados (`--split-per-abi`): armv7 +1000, arm64 +2000, x86 +3000, x86_64 +4000; o universal não soma nada. Valores reais (conferidos nos APKs de `v1.0.0-rc1`):

| Tag | armv7 | arm64 | x86_64 | universal |
|---|---|---|---|---|
| `v1.0.0-rc1` | 1001001 | 1002001 | 1004001 | 1000001 |
| `v1.0.0-rc2` | 1001002 | 1002002 | 1004002 | 1000002 |
| `v1.0.0` | 1001099 | 1002099 | 1004099 | 1000099 |
| `v1.0.1` | 1001199 | 1002199 | 1004199 | 1000199 |

Na **mesma arquitetura** a ordem rc1 < rc2 < final < próximo patch vale, e o Android aceita atualizar. Duas consequências:

- **Instale sempre o mesmo tipo de APK no mesmo aparelho.** O universal tem `versionCode` menor que o arm64 da mesma tag, então não atualiza um arm64 já instalado (e o contrário atualiza, mas troca de tipo).
- O prefixo (até 4000) é maior que o passo de patch (100): trocar de arquitetura no mesmo aparelho entre versões distintas pode ser recusado. Na prática um aparelho não muda de arquitetura.
- Limites: minor e patch até 99, rc de 1 a 98.

## Nomes dos arquivos

O build roda quando uma release é **publicada** (`.github/workflows/magodesk-release.yml`) e anexa os pacotes à própria release. Padrão: `<app em minúsculas>-<TAG>-<arquitetura>.<extensão>`.

| Plataforma | Exemplo |
|---|---|
| Windows portátil | `magodesk-v1.0.0-rc1-x86_64.exe`, `magodesk-v1.0.0-rc1-aarch64.exe` |
| Windows MSI | `magodesk-v1.0.0-rc1-x86_64.msi`, `...-aarch64.msi` |
| Android | `magodesk-v1.0.0-rc1-aarch64.apk`, `...-armv7.apk`, `...-x86_64.apk`, `...-universal.apk` (todos assinados; o workflow tira o sufixo `-signed` que a action de assinatura acrescenta) |

O workflow marca a release como pre-release quando a tag contém `-rc`; isso sobrescreve o que estiver na release, então a tag é que manda.

Passo a passo de um teste:

```
gh release create v1.0.0-rc1 --prerelease --target master --title "v1.0.0-rc1" --notes "teste"
```

`gh release create` cria a tag a partir de `master` e publica a release. Se o build não disparar sozinho, use o disparo manual: `gh workflow run magodesk-release.yml -f tag=v1.0.0-rc1 -f windows-only=false`.

## Android

- `applicationId` = `br.com.diomedes.magodesk` (permanente: trocar depois exige desinstalar o app nos aparelhos). O `namespace` Kotlin continua `com.carriez.flutter_hbb`; só o pacote `ffi` precisa manter o nome (ver `AGENTS.md`).
- O nome visível, o canal de notificação, o texto do `BootReceiver` e o esquema de link (`magodesk://`) vêm de `RD_APP_NAME`.
- O serviço pode subir no boot sem o Flutter. `Java_ffi_FFI_startServer` chama `captive::apply()` para que ele nunca registre no servidor público.
- O aviso de golpe antes de compartilhar a tela mantém os 12 s, mesmo com `isCustomClient` verdadeiro.
- Assinatura: o job usa os secrets `ANDROID_*`; o APK de teste e o final saem assinados com a mesma chave (alias `rustdesk`, titular `CN=RustDesk Diomedes`; o alias é só um rótulo interno, e trocá-lo mudaria a identidade de assinatura).
- Verificado abrindo o APK do `rc1` ao `rc4`: pacote `br.com.diomedes.magodesk`, nome `MagoDesk`, serviço `MagoDesk Input`, esquema `magodesk://`, mesma assinatura (SHA-256 `FD:A4:E1:07…`). O `rc4` foi instalado e usado num aparelho: **validado**.

O `flutter-nightly.yml` do upstream está desativado no GitHub; não há build noturno.

Os testes de `captive.rs` usam o `hbb_common` e só rodam junto com a árvore compilada (no CI). Os de lógica pura (opções travadas, nome do app, WebSocket por proxy, login desligado) foram rodados num crate isolado com um `hbb_common` simulado.

## Cache de compilação

O vcpkg do upstream removeu o provedor `x-gha`, então o `make_workflow.py` troca-o pelo provedor `files` mais `actions/cache`. O compilador de Rust usa o `rust-cache` do upstream. Regras:

- **Só Windows e Android têm cache.** O macOS fica sem, porque seus caches (~1,5 GB cada) estouravam os 10 GB do repositório e o tempo dele é de `flutter`/Xcode.
- **O GitHub só deixa um build ler o cache da própria branch ou da branch padrão.** Toda release nasce de uma tag nova, então ela nunca vê o cache de outra tag. Por isso o `magodesk-warm.yml` roda na `master` (manual e semanal) e é **só ele que grava** o cache do compilador (`save-if`); as releases apenas leem.
- O aquecimento não publica nada (`upload-artifact: false`) e **não roda os testes do upstream** (`run-tests`, desligado): com as configurações do cliente travado aplicadas, os testes de rede deles falham ou travam por horas.
- Depois de uma mudança grande no `Cargo.lock`, rode o aquecimento (*Actions → MagoDesk cache warm-up → Run workflow*, na `master`) antes de publicar, ou a release compila do zero.

## Como o fork é organizado

**Nenhum arquivo do RustDesk é editado.** O fork é o upstream mais estes arquivos novos, todos em `magodesk/` (exceto os dois workflows, que o GitHub só aceita em `.github/workflows/`):

| Arquivo | O que é |
|---|---|
| `magodesk/branding.py` | o motor: valida as entradas, aplica as regras e carimba a versão |
| `magodesk/rules.py` | as 48 regras (arquivo, texto do upstream, texto novo): Windows, Android, macOS, ligação do cliente cativo |
| `magodesk/captive.rs` | o cliente travado no servidor; o `rules.py` o liga em `src/lib.rs` com `#[path]` |
| `magodesk/make_workflow.py` | gera `.github/workflows/magodesk-build.yml` a partir do `flutter-build.yml` do upstream |
| `magodesk/set_version.py`, `release_notes.py` | versão pela tag; SHA-256 e instruções na release |
| `magodesk/check_upstream.py` | confere regras, workflow gerado e testes; usado pela verificação e pelo `preflight` |
| `magodesk/preview_merge.sh` | simula o merge do upstream mais novo, só no runner; usado pela verificação |
| `magodesk/tests/` | testa o motor numa cópia limpa |
| `.github/workflows/magodesk-release.yml` | o gatilho: release publicada, ou execução manual; começa pelo `preflight` |
| `.github/workflows/magodesk-check.yml` | a verificação diária e manual; só avisa por issue |

### Entradas do `branding.py`
| Origem | Nome | Observação |
|---|---|---|
| Secret | `RD_HOST`, `RD_KEY` | servidor e chave; só validados aqui (o compilador lê por `option_env!`), nunca impressos |
| Variável | `RD_APP_NAME` | letras e dígitos |
| Variável (opcional) | `RD_ANDROID_ID` | padrão `br.com.diomedes.<app>` |
| Variável (opcional) | `RD_BUNDLE_PREFIX` | padrão `br.com.diomedes`; o bundle do macOS é `<prefixo>.<app>` |

Se uma entrada faltar ou for inválida, o build para antes de compilar.

### Sync Fork (o que acontece e o que você faz)
Nada constrói sozinho. O fluxo tem uma trava humana de propósito: se o upstream mudar algo que o script não sabe ajustar, o build não deve nascer quebrado.

1. **Atualizar o upstream:** `git fetch upstream && git merge upstream/master && git push origin master`, ou **Update branch** no GitHub. **Nunca use "Discard commits"** do botão Sync Fork: ele apagaria `magodesk/` e os workflows. Não há conflito: nenhum arquivo do upstream foi editado.
2. **Verificação** (`magodesk-check.yml`): todo dia às 06:17 UTC e sob demanda (*Actions → MagoDesk upstream check → Run workflow*). O GitHub **pode não disparar o agendamento neste fork** (em 21/nov não disparou), então o uso confiável é o disparo manual, que leva segundos. Ela **simula o merge** do `rustdesk/rustdesk` mais novo dentro do próprio runner (`magodesk/preview_merge.sh`; descartável, nunca faz push) e roda `check_upstream.py` **nessa mistura**: assim vê o que está chegando, e não só o que você já mesclou. Ela **só avisa**: nunca constrói e nunca altera o repositório.
   - Tudo certo: nada acontece (o resumo mostra quantos commits novos e o commit do upstream).
   - Algo não serve mais, ou o merge tem conflito: abre **uma issue** com o arquivo e a regra. Quando passa de novo, a issue é fechada sozinha.
3. **Você decide quando construir**: publique uma release (`gh release create vX.Y.Z-rcN --prerelease`). O `preflight` do `magodesk-release.yml` repete a verificação **com os secrets reais** (`--real-inputs`) e para em segundos se algo falhar, antes de compilar.
4. Se a verificação pedir, corrija `magodesk/rules.py`, ou rode `python3 magodesk/make_workflow.py` e faça o commit do `magodesk-build.yml`. O workflow não faz esse commit sozinho: o token padrão do GitHub não pode alterar `.github/workflows/`, e preferimos não guardar um token com essa permissão.
5. **Teste nos aparelhos** antes de chamar uma versão de estável. A verificação não enxerga uma mudança de comportamento que compila e passa nas âncoras.

Os workflows do upstream que disparam sozinhos (`ci`, `flutter-ci`, `fdroid`, `flutter-tag`, `flutter-nightly`, `update-webpki-roots`) ficam **desativados pelo GitHub** (`gh workflow disable`), e não apagados: apagar o arquivo voltaria como conflito no próximo Sync Fork. Se um Sync Fork trouxer um workflow novo do upstream, rode `gh workflow list --all` e desative o que dispara sozinho.

### Limites
- Nenhum build é compilado localmente; só o CI prova que o app funciona.
- O `captive.rs` depende de APIs do `hbb_common` (`Config`, `Socks5Server`, `check_ws`). Se o upstream as mudar, o build do Rust falha no CI.
- O gerador e o motor só reconhecem o que está escrito neles: um problema novo no upstream que não toque nas âncoras passa despercebido até o CI.

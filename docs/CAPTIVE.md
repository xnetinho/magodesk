# Cliente cativo

Este fork compila um cliente que aponta sempre para um único servidor, sem troca pela interface.

## Como é configurado

Lidos na compilação por `option_env!` em `src/captive.rs` (Settings → Secrets and variables → Actions):

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

O texto que você escrever na descrição é preservado: o job só reescreve o bloco entre `<!-- magodesk-install:begin -->` e `<!-- magodesk-install:end -->`, então rodar de novo substitui o bloco em vez de duplicá-lo. O código está em `res/release_notes.py` (`sums` e `body`).

Conferir um arquivo baixado, no PowerShell: `Get-FileHash .\magodesk-<versão>-x86_64.exe -Algorithm SHA256`.

## macOS

Sem conta Apple paga (US$ 99/ano), o app **não tem** Developer ID nem notarização. O job `build-for-macOS` gera o `.dmg` com **assinatura ad hoc**: o Apple Silicon só executa código assinado, e a assinatura local satisfaz isso. O Gatekeeper ainda avisa na primeira execução ("não pôde verificar o desenvolvedor"). A descrição da release traz o passo a passo (*Ajustes do Sistema > Privacidade e Segurança > Abrir Mesmo Assim*; no macOS 15 em diante o atalho do botão direito deixou de existir; alternativa `xattr -dr com.apple.quarantine`).

Se um dia houver os secrets `MACOS_P12_BASE64`, `MACOS_P12_PASSWORD`, `MACOS_CODESIGN_IDENTITY` e `MACOS_NOTARIZE_JSON`, o workflow volta ao caminho do upstream (Developer ID + notarização com `rcodesign`) e o passo ad hoc é pulado.

- **Marca:** `res/set_macos_brand.py "$RD_APP_NAME"` roda no CI antes do build e grava nome do `.app`, `PRODUCT_NAME`, identificador `br.com.diomedes.<app>` e esquema de link (`magodesk://`) no `AppInfo.xcconfig`, `Info.plist` (via variáveis) e `Cargo.toml`. Os plists do launchd (serviço e agente) são reescritos pelo programa em execução a partir de `APP_NAME` e do identificador do bundle (`correct_app_name` em `src/platform/macos.rs`). Removi o `DEVELOPMENT_TEAM` do upstream do projeto Xcode.
- **Arquivos:** `magodesk-<tag>-x86_64.dmg` e `magodesk-<tag>-aarch64.dmg`. O `x86_64` roda em Mac Intel; o `aarch64`, em Apple Silicon.
- **Permissões:** o app precisa de Acessibilidade e Gravação de Tela. Como a assinatura ad hoc muda a cada versão, o macOS pode pedir essas permissões de novo depois de uma atualização.
- **Quando roda:** só com release publicada (ou disparo manual com `windows-only=false`). Não compila nem roda no nightly.
- **Limite:** nada disto foi compilado nem executado em um Mac. O iOS está **fora de escopo** (o job existe, mas não publica `.ipa`).

## Nome do produto (rebranding)

`RD_APP_NAME` define o nome do executável (`MagoDesk.exe`), o pipe IPC, a pasta de configuração, o nome do serviço e os metadados do arquivo. Isso permite instalar o cliente ao lado de um RustDesk oficial sem colisão. O nome é gravado em `APP_NAME` dentro de `captive::apply()`, antes de qualquer uso de `Config`. Como o nome deixa de ser `RustDesk`, `is_custom_client()` passa a ser verdadeiro; ver `CONTEXT.md` para o efeito nos padrões.

## Versão e release

A **tag define a versão**. `res/set_version.py <tag>` grava a versão em `Cargo.toml`, `libs/portable/Cargo.toml`, `Cargo.lock` e `flutter/pubspec.yaml` antes de cada build; o sufixo `-rcN` fica só na tag e nos nomes dos arquivos, porque o binário, o MSI e o Flutter exigem `X.Y.Z` numérico. A base do produto é `1.0.0`.

| Tag | Uso | Release | Versão no app |
|---|---|---|---|
| `v1.0.0-rc1` | teste | **pre-release** | 1.0.0 |
| `v1.0.0-rc2` | teste | pre-release | 1.0.0 |
| `v1.0.0` | final | release normal | 1.0.0 |
| `v1.0.1` | final | release normal | 1.0.1 |

### `versionCode` do Android

`res/set_version.py` calcula a base `MAJOR*1000000 + MINOR*10000 + PATCH*100 + (rcN, ou 99 na final)`. O Flutter ainda **soma um prefixo por arquitetura** nos APKs separados (`--split-per-abi`): armv7 +1000, arm64 +2000, x86 +3000, x86_64 +4000; o universal não soma nada. Valores reais (conferidos nos APKs de `v1.0.0-rc1`):

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

O build roda quando uma release é **publicada** (`.github/workflows/flutter-tag.yml`) e anexa os pacotes à própria release. Padrão: `<app em minúsculas>-<TAG>-<arquitetura>.<extensão>`.

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

`gh release create` cria a tag a partir de `master` e publica a release. Se o build não disparar sozinho, use o disparo manual: `gh workflow run flutter-tag.yml -f tag=v1.0.0-rc1 -f windows-only=false`.

## Android

- `applicationId` = `br.com.diomedes.magodesk` (permanente: trocar depois exige desinstalar o app nos aparelhos). O `namespace` Kotlin continua `com.carriez.flutter_hbb`; só o pacote `ffi` precisa manter o nome (ver `AGENTS.md`).
- O nome visível, o canal de notificação, o texto do `BootReceiver` e o esquema de link (`magodesk://`) vêm de `RD_APP_NAME`.
- O serviço pode subir no boot sem o Flutter. `Java_ffi_FFI_startServer` chama `captive::apply()` para que ele nunca registre no servidor público.
- O aviso de golpe antes de compartilhar a tela mantém os 12 s, mesmo com `isCustomClient` verdadeiro.
- Assinatura: o job usa os secrets `ANDROID_*`; o APK de teste e o final saem assinados com a mesma chave (alias `rustdesk`, titular `CN=RustDesk Diomedes`; o alias é só um rótulo interno, e trocá-lo mudaria a identidade de assinatura).
- Verificado em `v1.0.0-rc1`: pacote `br.com.diomedes.magodesk`, nome `MagoDesk`, serviço `MagoDesk Input`, esquema `magodesk://`, `versionName` 1.0.0. Nenhum teste de execução em aparelho ainda.

`flutter-nightly.yml` continua disponível só como disparo manual.

Os testes de `captive.rs` rodam com `cargo test` no crate (usam o `hbb_common` do submódulo).

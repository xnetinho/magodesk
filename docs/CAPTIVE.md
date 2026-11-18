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

## Nome do produto (rebranding)

`RD_APP_NAME` define o nome do executável (`MagoDesk.exe`), o pipe IPC, a pasta de configuração, o nome do serviço e os metadados do arquivo. Isso permite instalar o cliente ao lado de um RustDesk oficial sem colisão. O nome é gravado em `APP_NAME` dentro de `captive::apply()`, antes de qualquer uso de `Config`. Como o nome deixa de ser `RustDesk`, `is_custom_client()` passa a ser verdadeiro; ver `CONTEXT.md` para o efeito nos padrões.

## Release e nomes dos arquivos

O build roda quando uma release é **publicada** (`.github/workflows/flutter-tag.yml`) e anexa os pacotes à própria release:

| Arquivo | Exemplo |
|---|---|
| Portátil | `magodesk-v1.5.4-x86_64.exe`, `magodesk-v1.5.4-aarch64.exe` |
| MSI | `magodesk-v1.5.4-x86_64.msi`, `magodesk-v1.5.4-aarch64.msi` |

Padrão: `<app em minúsculas>-<TAG>-<arquitetura>.<exe|msi>`.

| Tag | Uso | Release |
|---|---|---|
| `vX.Y.Z-rcN` (ex.: `v1.5.4-rc1`) | teste | marcar como **pre-release** |
| `vX.Y.Z` (ex.: `v1.5.4`) | final | release normal |

O workflow marca a release como pre-release quando a tag contém `-rc` (e `nightly`); isso sobrescreve o que estiver na release, então a tag é que manda.

Passo a passo de um teste:

```
gh release create v1.5.4-rc1 --prerelease --target master --title "v1.5.4-rc1" --notes "teste"
```

`gh release create` cria a tag a partir de `master` e publica a release, o que dispara o build. Para refazer uma tag existente: `gh workflow run flutter-tag.yml -f tag=v1.5.4-rc1`.

`flutter-nightly.yml` continua disponível só como disparo manual.

Os testes de `captive.rs` rodam com `cargo test` no crate (usam o `hbb_common` do submódulo).

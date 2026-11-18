# Cliente cativo

Este fork compila um cliente que aponta sempre para um único servidor, sem troca pela interface.

## Como é configurado

Secrets do repositório (Settings → Secrets and variables → Actions), lidos na compilação por `option_env!` em `src/captive.rs`:

| Secret | Valor |
|---|---|
| `RD_HOST` | domínio do servidor, sem porta |
| `RD_KEY` | chave **pública** do servidor (`id_ed25519.pub`) |

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

## Build

```
gh workflow run flutter-nightly.yml --ref master -f windows-only=true
```

`windows-only=false` compila todas as plataformas. O `.exe` portátil sai na release `nightly`.

Os testes de `captive.rs` rodam com `cargo test` no crate (usam o `hbb_common` do submódulo).

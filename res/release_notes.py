#!/usr/bin/env python3
"""Build the checksum file and the install notes that go on a release.

    release_notes.py sums  <dir>                      -> writes <dir>/SHA256SUMS.txt
    release_notes.py body  <dir> <existing-body-file> -> prints the new release body

The body keeps whatever the owner wrote and only owns the block between the two markers,
so running it again replaces that block instead of piling up copies.
"""
import hashlib
import re
import sys
from pathlib import Path

BEGIN = "<!-- magodesk-install:begin -->"
END = "<!-- magodesk-install:end -->"
SUMS = "SHA256SUMS.txt"
# the SBOM and the checksum file are not something a user installs
SKIP_SUFFIX = (".json", ".txt")


MAC_STEPS = """
**macOS** (`.dmg`): o app tem só uma assinatura local ("ad hoc", sem custo), não a da Apple. Ela basta para o Apple Silicon executar o app, mas o Gatekeeper avisa na primeira vez:
1. Abra o `.dmg` e arraste o app para a pasta **Aplicativos**.
2. Abra o app. O macOS diz que não pôde verificar o desenvolvedor. Clique em **Concluído** (não em "Mover para o Lixo").
3. Vá em **Ajustes do Sistema > Privacidade e Segurança**, role até **Segurança** e clique em **Abrir Mesmo Assim**. Digite a senha de administrador. Isso é feito uma vez por versão.
4. No macOS 14 ou anterior, também funciona clicar com o botão direito no app e escolher **Abrir**. No macOS 15 em diante esse atalho não existe.
5. Se preferir o Terminal: `xattr -dr com.apple.quarantine /Applications/{app}.app` e depois abra o app.
6. Em **Privacidade e Segurança**, conceda **Acessibilidade** e **Gravação de Tela** para que o controle e o compartilhamento funcionem. Como a assinatura é local, o macOS pode pedir essas permissões de novo depois de uma atualização.
"""


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def app_name(folder):
    """Product name from the package file names (<app>-<tag>-<arch>.<ext>), as the build capitalises it."""
    import os
    name = os.environ.get("RD_APP_NAME", "").strip()
    if name:
        return name
    for p in packages(folder):
        if p.suffix == ".dmg":
            return p.name.split("-")[0].capitalize()
    return "MagoDesk"


def packages(folder):
    return sorted(
        p for p in Path(folder).iterdir()
        if p.is_file() and not p.name.endswith(SKIP_SUFFIX)
    )


def write_sums(folder):
    files = packages(folder)
    if not files:
        raise SystemExit(f"no packages found in {folder}")
    lines = [f"{sha256(p)}  {p.name}" for p in files]
    out = Path(folder) / SUMS
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


def install_block(folder):
    rows = []
    for p in packages(folder):
        rows.append(f"| `{p.name}` | `{sha256(p)}` |")
    table = "\n".join(rows)
    has_mac = any(p.suffix == ".dmg" for p in packages(folder))
    mac = MAC_STEPS.replace("{app}", app_name(folder)) if has_mac else ""
    return f"""{BEGIN}
## Como instalar

Estes arquivos **não têm assinatura de código** (o projeto é pessoal, sem fins comerciais e sem custo de certificado), então o Windows e o Android mostram um aviso na primeira vez. Isso é esperado.

**Windows** (`.exe` portátil ou `.msi`):
1. Baixe o arquivo. Se o navegador pedir, escolha **Manter**.
2. Ao abrir, aparece *"O Windows protegeu o computador"*. Clique em **Mais informações** e depois em **Executar assim mesmo**.
3. Se o Windows 11 (instalação nova) bloquear **sem** esse botão, é o *Smart App Control*. Abra *Segurança do Windows > Controle de aplicativos e navegador > Smart App Control* e desative-o, ou instale rodando o `.msi` por um terminal como administrador.

**Android** (`.apk`): permita instalar apps desta origem quando o aparelho pedir. Use sempre o mesmo tipo de APK no mesmo aparelho.
{mac}
**Confira o arquivo antes de executar.** O `SHA256SUMS.txt` desta release lista a impressão digital de cada pacote. No Windows (PowerShell):

```
Get-FileHash .\\magodesk-<versão>-x86_64.exe -Algorithm SHA256
```

O resultado deve ser idêntico ao da tabela abaixo. Se for diferente, **não execute o arquivo**.

| Arquivo | SHA-256 |
|---|---|
{table}
{END}"""


def merge(existing, block):
    existing = (existing or "").strip()
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if pattern.search(existing):
        return pattern.sub(lambda _m: block, existing).strip() + "\n"
    return (existing + "\n\n" if existing else "") + block + "\n"


def main(argv):
    if len(argv) >= 3 and argv[1] == "sums":
        for line in write_sums(argv[2]):
            print(line)
    elif len(argv) == 4 and argv[1] == "body":
        existing = Path(argv[3]).read_text(encoding="utf-8") if Path(argv[3]).exists() else ""
        sys.stdout.write(merge(existing, install_block(argv[2])))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv)

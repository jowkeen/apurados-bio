"""Mantém os achados da página apuradosdojow.com.br (docs/produtos.json) e publica no GitHub Pages.

Uso (pela raiz do projeto; `bio.bat` é atalho para `py ferramentas\\bio.py`):

  bio importar <pasta da execução ou manifest.json>   importa os produtos de uma campanha do apurados-dados
  bio adicionar --nome ... --preco 199,90 --link ... --foto ... [--loja ...] [--campanha id] [--campanha-titulo ...]
  bio listar [--todos]
  bio ocultar <id> | bio mostrar <id> | bio remover <id> | bio destacar <id> [--nao]
  bio limpar --dias 30                                 oculta achados apurados há mais de N dias
  bio previa [--porta 8000]                            abre a página local em http://localhost:8000
  bio publicar [-m "mensagem"]                         commit de docs/ e push (o site atualiza em ~1 min)

Só stdlib. Só campos públicos vão para produtos.json: ângulo, justificativa, comissão e
restrições do comitê ficam no apurados-dados e nunca entram no site.
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import http.server
import json
import re
import subprocess
import sys
import unicodedata
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
ARQUIVO = DOCS / "produtos.json"
DADOS_CAMPANHAS = Path(r"C:\Projetos\apurados-dados")
SHOPEE = Path(r"C:\Projetos\shopee-api\shopee.cmd")
# Links do site já gerados (itemid|campanha -> link). Fora do git: é só um atalho para não chamar a API de novo.
CACHE_LINKS = RAIZ / "ferramentas" / "cache-links.json"

CAMPOS_PUBLICOS = ("id", "nome", "preco", "link", "foto", "loja", "campanha", "campanha_titulo",
                   "apurado_em", "adicionado_em", "destaque", "ativo")


def agora() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def carregar() -> dict:
    if not ARQUIVO.exists():
        return {"atualizado_em": agora(), "produtos": []}
    return json.loads(ARQUIVO.read_text(encoding="utf-8"))


def salvar(dados: dict) -> None:
    dados["atualizado_em"] = agora()
    dados["produtos"] = [{k: p[k] for k in CAMPOS_PUBLICOS if k in p} for p in dados["produtos"]]
    ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "item"


def normalizar_preco(preco: str) -> str:
    """'199' / '199.9' / 'R$ 1.299,90' -> '199,00' / '199,90' / '1.299,90'."""
    p = str(preco).replace("R$", "").strip()
    if "," in p:
        inteiro, cent = p.rsplit(",", 1)
        inteiro = inteiro.replace(".", "")
    elif re.fullmatch(r"\d+\.\d{1,2}", p):
        inteiro, cent = p.split(".")
    else:
        inteiro, cent = p.replace(".", ""), "00"
    if not inteiro.isdigit() or not cent.isdigit():
        raise SystemExit(f"Preço inválido: {preco!r}")
    return f"{int(inteiro):,}".replace(",", ".") + "," + cent.ljust(2, "0")[:2]


def validar_url(url: str, campo: str) -> str:
    if not re.match(r"^https://", url or ""):
        raise SystemExit(f"{campo} precisa começar com https:// (veio {url!r})")
    return url


def upsert(dados: dict, novo: dict) -> str:
    for p in dados["produtos"]:
        if p["id"] == novo["id"]:
            adicionado = p.get("adicionado_em")
            destaque = p.get("destaque")
            p.update(novo)
            p["adicionado_em"] = adicionado or novo["adicionado_em"]
            if destaque is not None:
                p["destaque"] = destaque
            return "atualizado"
    dados["produtos"].append(novo)
    return "novo"


def achar(dados: dict, ident: str) -> dict:
    for p in dados["produtos"]:
        if p["id"] == ident:
            return p
    raise SystemExit(f"Não achei o id {ident!r}. Veja os ids com: bio listar --todos")


def link_do_site(link_produto: str, campanha: str, itemid: str, cache: dict) -> str | None:
    """Link de afiliado próprio do site, com sub_ids `bio <campanha> site a <itemid>`.

    Mesma convenção do n8n (canal, campanha, formato, variante, itemid), trocando o canal por "bio":
    assim `shopee conversoes --resumo` separa as vendas que vieram da página.
    """
    chave = f"{itemid}|{campanha}"
    if chave in cache:
        return cache[chave]
    limpar = lambda s: re.sub(r"[^A-Za-z0-9]", "", str(s))
    sub = [limpar(x) for x in ("bio", campanha, "site", "a", itemid) if limpar(x)]
    r = subprocess.run([str(SHOPEE), "link", link_produto, "--sub", *sub], text=True, capture_output=True,
                       encoding="utf-8", stdin=subprocess.DEVNULL)
    link = r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else ""
    if not link.startswith("https://"):
        print(f"  aviso: não gerei o link do site para {itemid} ({(r.stderr or r.stdout).strip()[:120]}); "
              "fica o link da campanha")
        return None
    cache[chave] = link
    return link


# ---------------------------------------------------------------- comandos

def cmd_importar(a) -> None:
    alvo = Path(a.pasta)
    if not alvo.is_absolute() and not alvo.exists():
        alvo = DADOS_CAMPANHAS / alvo
    manifesto = alvo if alvo.suffix == ".json" else alvo / "manifest.json"
    if not manifesto.exists():
        # aceita a pasta da campanha: pega a execução mais recente
        execs = sorted(alvo.glob("*/manifest.json")) if alvo.is_dir() else []
        if not execs:
            raise SystemExit(f"Não achei manifest.json em {alvo}")
        manifesto = execs[-1]
    m = json.loads(manifesto.read_text(encoding="utf-8"))
    pedido = m.get("pedido") or {}
    campanha = pedido.get("campanha") or m.get("campanha") or ""
    titulo = a.titulo or pedido.get("titulo") or campanha
    apurado = (m.get("gerado_em") or agora())[:10]

    dados = carregar()
    cache = {} if a.link_campanha or not CACHE_LINKS.exists() else json.loads(CACHE_LINKS.read_text(encoding="utf-8"))
    for item in pedido.get("produtos", []):
        if not item.get("link") or not item.get("preco"):
            print(f"  pulado (sem link ou preço): {item.get('nome') or item.get('titulo')}")
            continue
        ident = str(item.get("itemid") or slug(item.get("nome") or item["titulo"]))
        link = item["link"]
        if not a.link_campanha and item.get("link_produto") and item.get("itemid"):
            link = link_do_site(item["link_produto"], campanha, ident, cache) or link
        novo = {
            "id": ident,
            "nome": (item.get("nome") or f"{item.get('titulo', '')} {item.get('titulo2', '')}").strip(),
            "preco": normalizar_preco(item["preco"]),
            "link": validar_url(link, "link"),
            "foto": validar_url(item.get("foto", ""), "foto"),
            "loja": (item.get("loja") or "").strip(),
            "campanha": campanha,
            "campanha_titulo": titulo,
            "apurado_em": apurado,
            "adicionado_em": agora(),
            "ativo": True,
        }
        origem = "site" if link != item["link"] else "campanha"
        print(f"  {upsert(dados, novo):10} {novo['id']}  R$ {novo['preco']:>10}  link {origem:8}  {novo['nome'][:50]}")
    if cache:
        CACHE_LINKS.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    salvar(dados)
    print(f"Campanha {campanha!r} importada de {manifesto}")


def cmd_adicionar(a) -> None:
    dados = carregar()
    novo = {
        "id": a.id or slug(a.nome),
        "nome": a.nome.strip(),
        "preco": normalizar_preco(a.preco),
        "link": validar_url(a.link, "--link"),
        "foto": validar_url(a.foto, "--foto"),
        "loja": (a.loja or "").strip(),
        "campanha": a.campanha or "",
        "campanha_titulo": a.campanha_titulo or a.campanha or "",
        "apurado_em": a.apurado_em or dt.date.today().isoformat(),
        "adicionado_em": agora(),
        "ativo": True,
    }
    print(upsert(dados, novo), novo["id"])
    salvar(dados)


def cmd_listar(a) -> None:
    dados = carregar()
    for p in sorted(dados["produtos"], key=lambda p: p.get("adicionado_em", ""), reverse=True):
        if not a.todos and p.get("ativo") is False:
            continue
        marca = "*" if p.get("destaque") else (" " if p.get("ativo", True) else "-")
        print(f"{marca} {p['id']:<14} {p.get('apurado_em', ''):<10} R$ {p['preco']:>10}  "
              f"[{p.get('campanha', '')}] {p['nome'][:55]}")
    print("(* destaque, - oculto)")


def _marcar(ident: str, **campos) -> None:
    dados = carregar()
    achar(dados, ident).update(campos)
    salvar(dados)
    print("ok", ident, campos)


def cmd_remover(a) -> None:
    dados = carregar()
    achar(dados, a.id)
    dados["produtos"] = [p for p in dados["produtos"] if p["id"] != a.id]
    salvar(dados)
    print("removido", a.id)


def cmd_limpar(a) -> None:
    limite = (dt.date.today() - dt.timedelta(days=a.dias)).isoformat()
    dados = carregar()
    n = 0
    for p in dados["produtos"]:
        if p.get("ativo", True) and p.get("apurado_em", "9999") < limite:
            p["ativo"] = False
            n += 1
    salvar(dados)
    print(f"{n} achado(s) apurado(s) antes de {limite} ocultado(s)")


def cmd_previa(a) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DOCS))
    url = f"http://localhost:{a.porta}/"
    print(f"Prévia em {url} (Ctrl+C para parar)")
    webbrowser.open(url)
    http.server.ThreadingHTTPServer(("127.0.0.1", a.porta), handler).serve_forever()


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=RAIZ, text=True, capture_output=True, encoding="utf-8")


def cmd_publicar(a) -> None:
    json.loads(ARQUIVO.read_text(encoding="utf-8"))  # garante JSON válido antes de subir
    git("add", "docs")
    if git("diff", "--cached", "--quiet").returncode == 0:
        print("Nada mudou em docs/. Enviando commits pendentes, se houver.")
    else:
        msg = a.mensagem or f"Achados atualizados em {dt.datetime.now():%d/%m %H:%M}"
        r = git("commit", "-m", msg)
        if r.returncode:
            raise SystemExit(r.stderr or r.stdout)
        print(r.stdout.strip().splitlines()[0])
    r = git("push")
    if r.returncode:
        raise SystemExit(r.stderr)
    print("Publicado. https://apuradosdojow.com.br atualiza em cerca de 1 minuto.")


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="bio", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("importar", help="importa produtos de uma campanha do apurados-dados")
    s.add_argument("pasta", help="pasta da execução, da campanha (pega a mais recente) ou manifest.json")
    s.add_argument("--titulo", help="nome da campanha na página (padrão: título do pedido)")
    s.add_argument("--link-campanha", action="store_true",
                   help="usa o link de afiliado da campanha em vez de gerar um próprio do site (sub_id bio)")
    s.add_argument("--publicar", action="store_true", help="publica logo depois de importar")
    s.add_argument("-m", "--mensagem")
    s.set_defaults(f=cmd_importar)

    s = sub.add_parser("adicionar", help="adiciona ou atualiza um achado manualmente")
    s.add_argument("--nome", required=True)
    s.add_argument("--preco", required=True)
    s.add_argument("--link", required=True, help="link de afiliado (https://s.shopee.com.br/...)")
    s.add_argument("--foto", required=True, help="URL https da foto real do anúncio")
    s.add_argument("--loja")
    s.add_argument("--campanha")
    s.add_argument("--campanha-titulo")
    s.add_argument("--apurado-em", help="AAAA-MM-DD (padrão: hoje)")
    s.add_argument("--id", help="padrão: itemid ou slug do nome")
    s.add_argument("--publicar", action="store_true")
    s.add_argument("-m", "--mensagem")
    s.set_defaults(f=cmd_adicionar)

    s = sub.add_parser("listar")
    s.add_argument("--todos", action="store_true", help="inclui os ocultos")
    s.set_defaults(f=cmd_listar)

    for nome, campos in (("ocultar", {"ativo": False}), ("mostrar", {"ativo": True})):
        s = sub.add_parser(nome)
        s.add_argument("id")
        s.set_defaults(f=lambda a, c=campos: _marcar(a.id, **c))

    s = sub.add_parser("destacar", help="fixa o achado no topo")
    s.add_argument("id")
    s.add_argument("--nao", action="store_true", help="tira o destaque")
    s.set_defaults(f=lambda a: _marcar(a.id, destaque=not a.nao))

    s = sub.add_parser("remover")
    s.add_argument("id")
    s.set_defaults(f=cmd_remover)

    s = sub.add_parser("limpar", help="oculta achados com preço antigo")
    s.add_argument("--dias", type=int, default=30)
    s.set_defaults(f=cmd_limpar)

    s = sub.add_parser("previa")
    s.add_argument("--porta", type=int, default=8000)
    s.set_defaults(f=cmd_previa)

    s = sub.add_parser("publicar")
    s.add_argument("-m", "--mensagem")
    s.set_defaults(f=cmd_publicar)

    a = ap.parse_args()
    a.f(a)
    if getattr(a, "publicar", False):
        cmd_publicar(a)


if __name__ == "__main__":
    main()

# Projeto: apurados-bio

Página de links da bio (apuradosdojow.com.br) do **Apurados do Jow**. Site estático em `docs/` no GitHub Pages;
`ferramentas/bio.py` (Python stdlib, rodar com `py`) mantém `docs/produtos.json` e publica. Uso: `README.md`.

## Ligação com os outros projetos
- Lê `C:\Projetos\apurados-dados\<campanha>\<exec>\manifest.json` (gerado pelo `apurados-layouts`, campo
  `pedido.produtos`). Se o formato do manifest mudar lá, ajustar `cmd_importar`.
- Identidade visual vem de `apurados-layouts/layouts/Logo e capas` e `apurados-layouts/fontes`.

## Regras
- Tudo em pt-BR. Sem segredos nem dados pessoais no repositório (é público).
- Nunca publicar campos internos do comitê (ângulo, justificativa, comissão, restrições, sub_ids):
  `CAMPOS_PUBLICOS` em `bio.py` é a lista do que pode sair.
- Foto só a real do anúncio; preço sempre com a data de apuração; manter o aviso `#publi` no rodapé.
- Validar visualmente com `bio previa` em largura de celular (375 px) antes de publicar.
- Commits: separados por escopo. `bio publicar` faz commit só de `docs/` e push no `main`.

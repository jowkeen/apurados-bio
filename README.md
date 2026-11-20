# apurados-bio

Página de links da bio do **Apurados do Jow**: [apuradosdojow.com.br](https://apuradosdojow.com.br).
Mostra as redes (Instagram, TikTok, YouTube) e os achados da Shopee com preço e link de afiliado.
Site estático em `docs/`, publicado pelo GitHub Pages.

## Postar achados novos

Tudo pelo `bio.bat` na raiz (é `py ferramentas\bio.py`, só stdlib):

```
bio importar bfnatal26 --titulo "Black Friday e Natal"   # campanha do apurados-dados (pega a execução mais recente)
bio importar C:\Projetos\apurados-dados\bfnatal26\2026-11-20_1813_exec5   # ou uma execução específica
bio adicionar --nome "Fone X" --preco 89,90 --link https://s.shopee.com.br/... --foto https://cf.shopee.com.br/file/...
bio previa                      # confere em http://localhost:8000
bio publicar                    # commit de docs/ + push; o site atualiza em ~1 min
```

Outros: `bio listar [--todos]`, `bio destacar <id>` (fixa no topo), `bio ocultar|mostrar|remover <id>`,
`bio limpar --dias 30` (oculta achados com preço velho). `importar` e `adicionar` aceitam `--publicar`.

Reimportar a mesma campanha atualiza preço, link e data dos itens (o id é o `itemid` da Shopee).

## Regras

- Só campos públicos vão para `docs/produtos.json`: o ângulo, a justificativa, a comissão e as restrições do comitê
  ficam no `apurados-dados`.
- Foto é sempre a do anúncio (URL da Shopee). A página usa a miniatura `_tn`.
- Cada preço mostra "Preço apurado em DD/MM. Pode mudar." e o rodapé tem o aviso `#publi` de link de afiliado.

## Estrutura

```
docs/index.html            página
docs/assets/estilo.css     identidade (preto #0d0d0d, amarelo #fdb913, Barlow)
docs/assets/app.js         monta os cards, busca e filtro por campanha a partir de produtos.json
docs/assets/fontes/        Barlow (OFL, licença em OFL.txt), copiadas de apurados-layouts/fontes
docs/assets/img/           perfil, favicon e og.jpg, gerados de apurados-layouts/layouts/Logo e capas
docs/produtos.json         dados (gerado pelo bio.py; pode editar à mão, mantendo o JSON válido)
docs/CNAME                 domínio do GitHub Pages
ferramentas/bio.py         CLI
```

## Hospedagem

GitHub Pages: branch `main`, pasta `/docs`, domínio `apuradosdojow.com.br`, HTTPS obrigatório.
DNS no registro.br: registros A do domínio para `185.199.108.153`, `185.199.109.153`, `185.199.110.153`,
`185.199.111.153` e CNAME `www` para `jowkeen.github.io`.

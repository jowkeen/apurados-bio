// Monta a lista de achados a partir de produtos.json (mantido por ferramentas/bio.py).
(() => {
  const lista = document.getElementById("lista");
  const filtros = document.getElementById("filtros");
  const busca = document.getElementById("busca");
  const vazio = document.getElementById("vazio");
  document.getElementById("ano").textContent = new Date().getFullYear();

  let produtos = [];
  let campanhaAtiva = "";

  const semAcento = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  const dataCurta = (iso) => {
    const [, m, d] = (iso || "").split("-");
    return d && m ? `${d}/${m}` : "";
  };

  // Foto da Shopee: versão miniatura (_tn); se falhar, usa a original.
  const miniatura = (url) => /cf\.shopee\.com\.br\/file\/[^/?#]+$/.test(url) && !url.endsWith("_tn") ? url + "_tn" : url;

  const el = (tag, cls, texto) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (texto != null) e.textContent = texto;
    return e;
  };

  function card(p) {
    const li = el("li");
    const a = el("a", "card");
    a.href = p.link;
    a.target = "_blank";
    a.rel = "noopener sponsored";
    a.dataset.id = p.id;
    a.dataset.nome = p.nome;
    a.setAttribute("aria-label", `${p.nome}, R$ ${p.preco}. Comprar na Shopee`);

    const foto = el("div", "card__foto");
    const img = el("img");
    img.src = miniatura(p.foto);
    img.alt = "";
    img.loading = "lazy";
    img.decoding = "async";
    img.addEventListener("error", () => { if (img.src !== p.foto) img.src = p.foto; }, { once: true });
    foto.append(img);
    if (p.campanha_titulo) foto.append(el("span", "card__tag", p.campanha_titulo));

    const corpo = el("div", "card__corpo");
    corpo.append(el("h3", "card__nome", p.nome));
    if (p.loja) corpo.append(el("p", "card__loja", p.loja.trim()));

    const [int, cent = "00"] = String(p.preco).split(",");
    const preco = el("div", "preco");
    preco.append(el("span", "preco__rs", "R$"), el("span", "preco__int", int), el("span", "preco__cent", "," + cent));
    corpo.append(preco);
    const data = dataCurta(p.apurado_em);
    if (data) corpo.append(el("p", "card__nota", `Preço apurado em ${data}. Pode mudar.`));

    const botao = el("span", "card__botao", "Comprar");
    botao.insertAdjacentHTML("beforeend", '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></svg>');
    corpo.append(botao);

    a.append(foto, corpo);
    li.append(a);
    return li;
  }

  function desenhar() {
    const termo = semAcento(busca.value.trim());
    const visiveis = produtos.filter((p) =>
      (!campanhaAtiva || p.campanha === campanhaAtiva) &&
      (!termo || semAcento(`${p.nome} ${p.loja || ""} ${p.campanha_titulo || ""}`).includes(termo)));
    lista.replaceChildren(...visiveis.map(card));
    vazio.hidden = visiveis.length > 0;
  }

  function montarFiltros() {
    const campanhas = [];
    for (const p of produtos) {
      if (p.campanha && !campanhas.some((c) => c.id === p.campanha)) campanhas.push({ id: p.campanha, titulo: p.campanha_titulo || p.campanha });
    }
    if (campanhas.length < 2) return;
    const botao = (id, texto) => {
      const b = el("button", "filtro", texto);
      b.type = "button";
      b.setAttribute("aria-pressed", String(id === campanhaAtiva));
      b.addEventListener("click", () => {
        campanhaAtiva = id;
        filtros.querySelectorAll(".filtro").forEach((f) => f.setAttribute("aria-pressed", String(f === b)));
        desenhar();
      });
      return b;
    };
    filtros.replaceChildren(botao("", "Todos"), ...campanhas.map((c) => botao(c.id, c.titulo)));
  }

  busca.addEventListener("input", desenhar);

  // Cliques (GoatCounter): produtos viram /clique/<id>, redes viram /rede/<nome>. Sem o contador, não faz nada.
  function contar(caminho, titulo) {
    try {
      if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: caminho, title: titulo, event: true });
    } catch (_) { /* contagem nunca atrapalha o clique */ }
  }
  lista.addEventListener("click", (ev) => {
    const a = ev.target.closest("a.card");
    if (a) contar(`clique/${a.dataset.id}`, a.dataset.nome);
  });
  document.querySelectorAll(".rede").forEach((a) =>
    a.addEventListener("click", () => contar(`rede/${a.getAttribute("aria-label").toLowerCase()}`, a.getAttribute("aria-label"))));

  fetch("produtos.json", { cache: "no-cache" })
    .then((r) => r.json())
    .then((dados) => {
      produtos = (dados.produtos || [])
        .filter((p) => p.ativo !== false)
        .sort((a, b) => (b.destaque === true) - (a.destaque === true) || (b.adicionado_em || "").localeCompare(a.adicionado_em || ""));
      montarFiltros();
      desenhar();
    })
    .catch(() => { vazio.textContent = "Não deu para carregar os achados agora. Atualize a página."; vazio.hidden = false; });
})();

/* ============================================================
   ImobData — app.js
   Etapa 2: apenas os KPIs do hero (/api/stats).
   As próximas etapas adicionam, no mesmo arquivo:
     Etapa 3 — busca/filtros e tabela (/api/imoveis)
     Etapa 4 — mapa (/api/mapa)
     Etapa 5 — gráficos de estatísticas (/api/distribuicao, /api/bairros)
     Etapa 6 — modal de detalhe (/api/imoveis/<id>)
   ============================================================ */

(function () {
  "use strict";

  function formatarNumero(valor) {
    return new Intl.NumberFormat("pt-BR").format(valor);
  }

  async function carregarKpisHero() {
    const elementos = document.querySelectorAll("[data-stat]");
    if (!elementos.length) return;

    try {
      const resposta = await fetch("/api/stats");
      if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
      const dados = await resposta.json();

      elementos.forEach((el) => {
        const chave = el.getAttribute("data-stat");
        const valor = dados[chave];
        el.textContent = typeof valor === "number" ? formatarNumero(valor) : (valor ?? "—");
        el.removeAttribute("data-loading");
      });
    } catch (erro) {
      console.error("Não foi possível carregar /api/stats:", erro);
      elementos.forEach((el) => { el.textContent = "—"; });
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    inicializarNavMobile();
    carregarKpisHero();
    inicializarBusca();
    inicializarMapa();
    inicializarBairros();
    inicializarEstatisticas();
    inicializarModal();
  });

  /* ==========================================================
     Etapa 7 — Menu mobile
     ========================================================== */
  function inicializarNavMobile() {
    const botao = document.getElementById("nav-toggle");
    const links = document.getElementById("nav-links");
    if (!botao || !links) return;

    botao.addEventListener("click", () => {
      const aberto = links.classList.toggle("aberto");
      botao.setAttribute("aria-expanded", String(aberto));
    });

    links.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        links.classList.remove("aberto");
        botao.setAttribute("aria-expanded", "false");
      });
    });
  }

  /* ==========================================================
     Etapa 3 — Busca, filtros, tabela e paginação
     ========================================================== */

  const STATUS_BADGE = {
    "Acima do mercado":          { classe: "badge-acima",  texto: "Acima do mercado" },
    "Abaixo do mercado":         { classe: "badge-abaixo", texto: "Abaixo do mercado" },
    "Dentro da faixa esperada":  { classe: "badge-dentro", texto: "Dentro da faixa" },
  };

  const estadoBusca = {
    page: 1,
    per_page: 20,
    sort_by: "criado_em",
    sort_dir: "desc",
  };

  function formatarMoeda(valor) {
    if (valor === null || valor === undefined) return "—";
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(valor);
  }

  function lerFiltros() {
    const params = {};
    const q = document.getElementById("f-busca")?.value.trim();
    const bairro = document.getElementById("f-bairro")?.value;
    const status = document.getElementById("f-status")?.value;
    const precoMin = document.getElementById("f-preco-min")?.value;
    const precoMax = document.getElementById("f-preco-max")?.value;
    const quartos = document.getElementById("f-quartos")?.value;
    const vagas = document.getElementById("f-vagas")?.value;

    if (q) params.q = q;
    if (bairro) params.bairro = bairro;
    if (status) params.status = status;
    if (precoMin) params.preco_min = precoMin;
    if (precoMax) params.preco_max = precoMax;
    if (quartos) params.quartos_min = quartos;
    if (vagas) params.vagas_min = vagas;
    return params;
  }

  async function carregarDadosBairros() {
    try {
      const resposta = await fetch("/api/bairros");
      if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
      const bairros = await resposta.json();
      popularSelectBairros(bairros);
      renderizarBairros(bairros);
    } catch (erro) {
      console.error("Não foi possível carregar /api/bairros:", erro);
    }
  }

  function popularSelectBairros(bairros) {
    const select = document.getElementById("f-bairro");
    if (!select) return;
    bairros.forEach((b) => {
      const option = document.createElement("option");
      option.value = b.bairro;
      option.textContent = `${b.bairro} (${b.total})`;
      select.appendChild(option);
    });
  }

  function renderizarLinhaVazia(mensagem) {
    const corpo = document.getElementById("tabela-corpo");
    corpo.innerHTML = `<tr><td colspan="7" class="tabela-vazia">${mensagem}</td></tr>`;
  }

  function renderizarTabela(itens) {
    const corpo = document.getElementById("tabela-corpo");
    if (!itens.length) {
      renderizarLinhaVazia("Nenhum imóvel encontrado com esses filtros.");
      return;
    }

    corpo.innerHTML = itens.map((item) => {
      const badge = STATUS_BADGE[item.status] || { classe: "badge-dentro", texto: item.status || "—" };
      const diferencaClasse = (item.diferenca ?? 0) > 0 ? "diferenca-positiva" : "diferenca-negativa";
      return `
        <tr data-id="${item.id}">
          <td>
            <div class="tabela-titulo">
              <strong>${item.bairro || "Não informado"}</strong>
              <span>${item.titulo || ""}</span>
            </div>
          </td>
          <td class="data">${formatarMoeda(item.preco_real)}</td>
          <td class="data">${formatarMoeda(item.preco_previsto)}</td>
          <td class="data ${diferencaClasse}">${formatarMoeda(item.diferenca)}</td>
          <td><span class="badge ${badge.classe}">${badge.texto}</span></td>
          <td class="data">${item.metragem ?? "—"}</td>
          <td class="data">${item.quartos ?? "—"}</td>
        </tr>`;
    }).join("");
  }

  function renderizarPaginacao(pagina, totalPaginas) {
    const container = document.getElementById("paginacao");
    container.innerHTML = `
      <button id="pg-anterior" ${pagina <= 1 ? "disabled" : ""}>‹ Anterior</button>
      <span class="pagina-atual">Página ${pagina} de ${totalPaginas}</span>
      <button id="pg-proxima" ${pagina >= totalPaginas ? "disabled" : ""}>Próxima ›</button>
    `;
    document.getElementById("pg-anterior")?.addEventListener("click", () => {
      estadoBusca.page = Math.max(1, estadoBusca.page - 1);
      buscarImoveis();
    });
    document.getElementById("pg-proxima")?.addEventListener("click", () => {
      estadoBusca.page += 1;
      buscarImoveis();
    });
  }

  async function buscarImoveis() {
    const contagem = document.getElementById("tabela-contagem");
    contagem.textContent = "Carregando…";
    renderizarLinhaVazia("Carregando dados…");

    const params = new URLSearchParams({
      ...lerFiltros(),
      page: estadoBusca.page,
      per_page: estadoBusca.per_page,
      sort_by: estadoBusca.sort_by,
      sort_dir: estadoBusca.sort_dir,
    });

    try {
      const resposta = await fetch(`/api/imoveis?${params.toString()}`);
      if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
      const dados = await resposta.json();

      renderizarTabela(dados.items);
      renderizarPaginacao(dados.page, dados.total_pages);
      contagem.textContent = `${dados.total} imóvel(is) encontrado(s)`;
    } catch (erro) {
      console.error("Não foi possível carregar /api/imoveis:", erro);
      contagem.textContent = "Erro ao carregar dados.";
      renderizarLinhaVazia("Não foi possível carregar os imóveis agora.");
    }
  }

  function inicializarBusca() {
    if (!document.getElementById("tabela-imoveis")) return;

    carregarDadosBairros();
    buscarImoveis();

    document.getElementById("btn-buscar")?.addEventListener("click", () => {
      estadoBusca.page = 1;
      buscarImoveis();
    });

    document.getElementById("f-busca")?.addEventListener("keydown", (evento) => {
      if (evento.key === "Enter") {
        estadoBusca.page = 1;
        buscarImoveis();
      }
    });

    document.getElementById("btn-limpar")?.addEventListener("click", () => {
      document.querySelectorAll("#buscar .campo input").forEach((el) => (el.value = ""));
      document.querySelectorAll("#buscar .campo select").forEach((el) => (el.value = ""));
      estadoBusca.page = 1;
      buscarImoveis();
    });

    document.getElementById("f-per-page")?.addEventListener("change", (evento) => {
      estadoBusca.per_page = Number(evento.target.value);
      estadoBusca.page = 1;
      buscarImoveis();
    });

    document.querySelectorAll("#tabela-imoveis th[data-sort]").forEach((th) => {
      th.addEventListener("click", () => {
        const coluna = th.getAttribute("data-sort");
        if (estadoBusca.sort_by === coluna) {
          estadoBusca.sort_dir = estadoBusca.sort_dir === "asc" ? "desc" : "asc";
        } else {
          estadoBusca.sort_by = coluna;
          estadoBusca.sort_dir = "desc";
        }
        document.querySelectorAll("#tabela-imoveis th[data-sort]").forEach((el) => el.classList.remove("sort-asc", "sort-desc"));
        th.classList.add(estadoBusca.sort_dir === "asc" ? "sort-asc" : "sort-desc");
        estadoBusca.page = 1;
        buscarImoveis();
      });
    });
  }

  /* ==========================================================
     Etapa 4 — Mapa (Leaflet)
     ========================================================== */

  // Mesmas cores semânticas de css/base.css (--status-*), duplicadas aqui
  // porque o Leaflet não lê variáveis CSS diretamente nas opções de estilo.
  const COR_STATUS = {
    "Acima do mercado":         "#C4432E",
    "Abaixo do mercado":        "#2F8F5B",
    "Dentro da faixa esperada": "#8A9A94",
  };

  const CENTRO_CURITIBA = [-25.4284, -49.2733];

  function formatarMoedaMapa(valor) {
    if (valor === null || valor === undefined) return "—";
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(valor);
  }

  async function inicializarMapa() {
    const container = document.getElementById("leaflet-mapa");
    if (!container || typeof L === "undefined") return;

    const mapa = L.map(container, { scrollWheelZoom: false }).setView(CENTRO_CURITIBA, 12);
    container.querySelector(".carregando")?.remove();

    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      maxZoom: 19,
    }).addTo(mapa);

    try {
      const resposta = await fetch("/api/mapa");
      if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
      const dados = await resposta.json();

      const marcadores = [];
      dados.pontos.forEach((ponto) => {
        const cor = COR_STATUS[ponto.status] || "#8A9A94";
        const marcador = L.circleMarker([ponto.latitude, ponto.longitude], {
          radius: 7,
          color: "rgba(27,35,33,0.35)",
          weight: 1,
          fillColor: cor,
          fillOpacity: 0.85,
        }).bindPopup(`
          <div class="popup-imovel">
            <span class="popup-bairro">${ponto.bairro || "Não informado"}</span>
            <strong>${ponto.titulo || "Imóvel"}</strong>
            <div class="popup-precos">
              <span>Anunciado: ${formatarMoedaMapa(ponto.preco_real)}</span>
              <span>Mercado: ${formatarMoedaMapa(ponto.preco_previsto)}</span>
            </div>
            ${ponto.url ? `<a class="popup-link" href="${ponto.url}" target="_blank" rel="noopener">Ver anúncio original →</a>` : ""}
          </div>
        `);
        marcador.addTo(mapa);
        marcadores.push(marcador);
      });

      if (marcadores.length) {
        const grupo = L.featureGroup(marcadores);
        mapa.fitBounds(grupo.getBounds().pad(0.15));
      }

      const aviso = document.getElementById("mapa-aviso");
      if (aviso && dados.sem_coordenadas > 0) {
        aviso.textContent = `${dados.sem_coordenadas} imóvel(is) sem coordenadas cadastradas não aparecem no mapa.`;
      }
    } catch (erro) {
      console.error("Não foi possível carregar /api/mapa:", erro);
      container.innerHTML = '<p class="tabela-vazia" style="padding: var(--space-6);">Não foi possível carregar o mapa agora.</p>';
    }
  }

  /* ==========================================================
     Etapa 5 — Bairros e Estatísticas (Chart.js)
     ========================================================== */

  const CORES_GRAFICO = {
    pine:  "#2B5D45",
    amber: "#E8A23D",
    acima:  "#C4432E",
    abaixo: "#2F8F5B",
    dentro: "#8A9A94",
    slate:  "#4C5B57",
    linha:  "#C9CFC5",
  };

  const OPCOES_FONTE_GRAFICO = { family: "Inter", size: 12 };

  function formatarMoedaCompacta(valor) {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency", currency: "BRL", notation: "compact", maximumFractionDigits: 1,
    }).format(valor);
  }

  function removerCarregando(id) {
    document.querySelector(`[data-carregando-de="${id}"]`)?.remove();
  }

  async function inicializarBairros() {
    const canvas = document.getElementById("chart-bairros");
    const corpoTabela = document.querySelector("#tabela-bairros tbody");
    if (!canvas && !corpoTabela) return;

    try {
      const resposta = await fetch("/api/bairros");
      if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
      const bairros = await resposta.json();

      // Tabela: todos os bairros, já vêm ordenados por total (backend)
      if (corpoTabela) {
        corpoTabela.innerHTML = bairros.length
          ? bairros.map((b) => `
              <tr>
                <td>${b.bairro}</td>
                <td class="data">${b.total}</td>
                <td class="data">${formatarMoedaCompacta(b.preco_medio)}</td>
              </tr>`).join("")
          : `<tr><td colspan="3" class="tabela-vazia">Nenhum bairro encontrado.</td></tr>`;
      }

      // Gráfico: top 10 bairros com mais imóveis analisados
      if (canvas && typeof Chart !== "undefined") {
        const top10 = bairros.slice(0, 10);
        new Chart(canvas, {
          type: "bar",
          data: {
            labels: top10.map((b) => b.bairro),
            datasets: [{
              label: "Preço médio",
              data: top10.map((b) => b.preco_medio),
              backgroundColor: CORES_GRAFICO.pine,
              borderRadius: 3,
              maxBarThickness: 28,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (ctx) => ` ${formatarMoedaCompacta(ctx.parsed.x)}`,
                },
              },
            },
            scales: {
              x: {
                ticks: { font: OPCOES_FONTE_GRAFICO, callback: (v) => formatarMoedaCompacta(v) },
                grid: { color: CORES_GRAFICO.linha },
              },
              y: {
                ticks: { font: OPCOES_FONTE_GRAFICO },
                grid: { display: false },
              },
            },
          },
        });
      }
    } catch (erro) {
      console.error("Não foi possível carregar /api/bairros:", erro);
      if (corpoTabela) corpoTabela.innerHTML = `<tr><td colspan="3" class="tabela-vazia">Erro ao carregar bairros.</td></tr>`;
    } finally {
      removerCarregando("chart-bairros");
    }
  }

  function construirHistograma(valores, margemErro, numBins = 8) {
    if (!valores.length) return { labels: [], contagens: [], cores: [] };

    const min = Math.min(...valores);
    const max = Math.max(...valores);
    if (min === max) {
      return { labels: [formatarMoedaCompacta(min)], contagens: [valores.length], cores: [CORES_GRAFICO.dentro] };
    }

    const tamanhoBin = (max - min) / numBins;
    const contagens = new Array(numBins).fill(0);
    valores.forEach((v) => {
      const indice = Math.min(numBins - 1, Math.floor((v - min) / tamanhoBin));
      contagens[indice] += 1;
    });

    const labels = [];
    const cores = [];
    for (let i = 0; i < numBins; i++) {
      const inicio = min + i * tamanhoBin;
      const fim = inicio + tamanhoBin;
      const meio = (inicio + fim) / 2;
      labels.push(`${formatarMoedaCompacta(inicio)} a ${formatarMoedaCompacta(fim)}`);
      if (meio > margemErro) cores.push(CORES_GRAFICO.acima);
      else if (meio < -margemErro) cores.push(CORES_GRAFICO.abaixo);
      else cores.push(CORES_GRAFICO.dentro);
    }

    return { labels, contagens, cores };
  }

  async function inicializarEstatisticas() {
    const canvasHistograma = document.getElementById("chart-distribuicao");
    const canvasDonut = document.getElementById("chart-status");
    if (!canvasHistograma && !canvasDonut) return;

    try {
      const [respostaDist, respostaStats] = await Promise.all([
        fetch("/api/distribuicao"),
        fetch("/api/stats"),
      ]);
      if (!respostaDist.ok) throw new Error(`HTTP ${respostaDist.status}`);
      if (!respostaStats.ok) throw new Error(`HTTP ${respostaStats.status}`);

      const distribuicao = await respostaDist.json();
      const stats = await respostaStats.json();
      const margemErro = stats.margem_erro || 0;

      const textoMargem = document.getElementById("margem-erro-texto");
      if (textoMargem) {
        textoMargem.textContent = `Considerando a margem de erro do modelo (± ${formatarMoedaCompacta(margemErro)}), cada imóvel é classificado como acima, dentro ou abaixo do preço esperado.`;
      }

      if (canvasHistograma && typeof Chart !== "undefined") {
        const valores = distribuicao.map((d) => d.diferenca).filter((v) => v !== null && v !== undefined);
        const { labels, contagens, cores } = construirHistograma(valores, margemErro);

        new Chart(canvasHistograma, {
          type: "bar",
          data: {
            labels,
            datasets: [{
              label: "Imóveis",
              data: contagens,
              backgroundColor: cores,
              borderRadius: 3,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: { callbacks: { label: (ctx) => ` ${ctx.parsed.y} imóvel(is)` } },
            },
            scales: {
              x: { ticks: { font: { ...OPCOES_FONTE_GRAFICO, size: 10 }, maxRotation: 0, autoSkip: true }, grid: { display: false } },
              y: { beginAtZero: true, ticks: { font: OPCOES_FONTE_GRAFICO, precision: 0 }, grid: { color: CORES_GRAFICO.linha } },
            },
          },
        });
      }

      if (canvasDonut && typeof Chart !== "undefined") {
        new Chart(canvasDonut, {
          type: "doughnut",
          data: {
            labels: ["Acima do mercado", "Dentro da faixa", "Abaixo do mercado"],
            datasets: [{
              data: [stats.acima_do_mercado, stats.dentro_da_faixa, stats.abaixo_do_mercado],
              backgroundColor: [CORES_GRAFICO.acima, CORES_GRAFICO.dentro, CORES_GRAFICO.abaixo],
              borderWidth: 2,
              borderColor: "#FFFFFF",
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "62%",
            plugins: {
              legend: { position: "bottom", labels: { font: OPCOES_FONTE_GRAFICO, padding: 12, usePointStyle: true } },
            },
          },
        });
      }
    } catch (erro) {
      console.error("Não foi possível carregar dados de estatísticas:", erro);
    } finally {
      removerCarregando("chart-distribuicao");
      removerCarregando("chart-status");
    }
  }

  /* ==========================================================
     Etapa 6 — Modal de detalhe do imóvel
     ========================================================== */

  const STATUS_BADGE_MODAL = STATUS_BADGE; // reaproveita o mapeamento definido na Etapa 3

  function formatarMoedaModal(valor) {
    if (valor === null || valor === undefined) return "—";
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(valor);
  }

  function formatarDataModal(isoString) {
    if (!isoString) return "—";
    try {
      return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(isoString));
    } catch {
      return isoString;
    }
  }

  function montarConteudoModal(item) {
    const badge = STATUS_BADGE_MODAL[item.status] || { classe: "badge-dentro", texto: item.status || "—" };
    const diferencaClasse = (item.diferenca ?? 0) > 0 ? "diferenca-positiva" : "diferenca-negativa";

    const tags = [...(item.caracteristicas_imovel || []), ...(item.caracteristicas_condominio || [])];

    return `
      <div class="modal-header">
        <span class="eyebrow">${item.bairro || "Bairro não informado"}</span>
        <h3>${item.titulo || "Imóvel"}</h3>
        <div class="modal-local">${[item.bairro, item.cidade, item.estado].filter(Boolean).join(", ")}${item.cep ? ` · CEP ${item.cep}` : ""}</div>
      </div>

      <div class="modal-precos">
        <div><div class="stat-label">Anunciado</div><div class="stat-value">${formatarMoedaModal(item.preco_real)}</div></div>
        <div><div class="stat-label">Preço de mercado</div><div class="stat-value">${formatarMoedaModal(item.preco_previsto)}</div></div>
        <div><div class="stat-label">Diferença</div><div class="stat-value ${diferencaClasse}">${formatarMoedaModal(item.diferenca)}</div></div>
      </div>

      <p><span class="badge ${badge.classe}">${badge.texto}</span></p>

      <div class="modal-specs">
        <div class="spec"><span class="spec-label">Área</span><span class="spec-value">${item.metragem ?? "—"} m²</span></div>
        <div class="spec"><span class="spec-label">Quartos</span><span class="spec-value">${item.quartos ?? "—"}</span></div>
        <div class="spec"><span class="spec-label">Banheiros</span><span class="spec-value">${item.banheiros ?? "—"}</span></div>
        <div class="spec"><span class="spec-label">Vagas</span><span class="spec-value">${item.vagas ?? "—"}</span></div>
        <div class="spec"><span class="spec-label">Condomínio</span><span class="spec-value">${item.condominio ? formatarMoedaModal(item.condominio) : "—"}</span></div>
        <div class="spec"><span class="spec-label">IPTU</span><span class="spec-value">${item.iptu ? formatarMoedaModal(item.iptu) : "—"}</span></div>
      </div>

      ${tags.length ? `<div class="modal-tags">${tags.map((t) => `<span class="modal-tag">${t}</span>`).join("")}</div>` : ""}

      ${item.descricao ? `<p class="modal-descricao">${item.descricao}</p>` : ""}

      <div class="modal-footer">
        <span class="modal-data">Anúncio de ${formatarDataModal(item.criado_em)}</span>
        ${item.url ? `<a class="btn btn-primary" href="${item.url}" target="_blank" rel="noopener">Ver anúncio original →</a>` : ""}
      </div>
    `;
  }

  async function abrirModal(id) {
    const overlay = document.getElementById("modal-overlay");
    const conteudo = document.getElementById("modal-conteudo");
    if (!overlay || !conteudo) return;

    conteudo.innerHTML = '<p class="tabela-vazia">Carregando…</p>';
    overlay.classList.add("aberto");
    document.body.style.overflow = "hidden";

    try {
      const resposta = await fetch(`/api/imoveis/${id}`);
      if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
      const item = await resposta.json();
      conteudo.innerHTML = montarConteudoModal(item);
    } catch (erro) {
      console.error(`Não foi possível carregar /api/imoveis/${id}:`, erro);
      conteudo.innerHTML = '<p class="tabela-vazia">Não foi possível carregar os detalhes deste imóvel.</p>';
    }
  }

  function fecharModal() {
    const overlay = document.getElementById("modal-overlay");
    if (!overlay) return;
    overlay.classList.remove("aberto");
    document.body.style.overflow = "";
  }

  function inicializarModal() {
    const overlay = document.getElementById("modal-overlay");
    if (!overlay) return;

    // Delegação de evento: a tabela é redesenhada a cada busca, então o
    // listener fica no contêiner pai (#tabela-corpo), não nas linhas.
    document.getElementById("tabela-corpo")?.addEventListener("click", (evento) => {
      const linha = evento.target.closest("tr[data-id]");
      if (linha) abrirModal(linha.dataset.id);
    });

    document.getElementById("modal-fechar")?.addEventListener("click", fecharModal);
    overlay.addEventListener("click", (evento) => {
      if (evento.target === overlay) fecharModal();
    });
    document.addEventListener("keydown", (evento) => {
      if (evento.key === "Escape" && overlay.classList.contains("aberto")) fecharModal();
    });
  }
})();
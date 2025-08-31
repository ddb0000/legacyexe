// minimal compare-only client

const $ = (q) => document.querySelector(q);
const setText = (node, text) => (node.textContent = text ?? "");
const bullets = (node, items) => {
  node.innerHTML = "";
  (items || []).slice(0, 64).forEach((x) => {
    const li = document.createElement("li");
    li.textContent = String(x);
    node.appendChild(li);
  });
};
const copyText = (t) => navigator.clipboard?.writeText(t).catch(()=>{});
function download(name, text){
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([text],{type:"text/plain"}));
  a.download=name||"arquivo.txt"; a.click(); URL.revokeObjectURL(a.href);
}
function parseCSV(str) {
  return String(str || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

// Strong steering so the model avoids placeholders:
const PROMPT_BASE = `
- Responda SOMENTE JSON válido UTF-8, sem markdown.
- Não use placeholders como "conteúdo do ..." ou "resultado disponível em".
- Preencha "report" com 3–10 bullets técnicos e acionáveis (português).
- "summary": lista de 3–8 decisões, riscos ou próximos passos.
- "updated_files": crie apenas arquivos REAIS do projeto; evite duplicar arquivos existentes sem necessidade.
- Se for Python, os arquivos devem terminar com .py e conter código válido (ex.: imports, def, if __name__).
- Evite criar pastas artificiais (ex.: "resultados/v1/").
- Se não houver nada para mudar, mantenha "updated_files": [] e explique o porquê no "report".
`.trim();

let lastFiles = [];

function renderFiles(files) {
  lastFiles = files || [];
  const root = $("#files");
  root.innerHTML = "";
  (lastFiles).forEach((f) => {
    const details = document.createElement("details");
    const sum = document.createElement("summary");
    sum.textContent = f.path || "(sem nome)";

    const actions = document.createElement("div");
    actions.className = "file-actions";
    const bCopy = document.createElement("button");
    bCopy.className = "ghost";
    bCopy.textContent = "copiar";
    bCopy.addEventListener("click", (e)=>{ e.preventDefault(); copyText(f.content||""); });

    const bDl = document.createElement("button");
    bDl.className = "ghost";
    bDl.textContent = "baixar";
    bDl.addEventListener("click", (e)=>{ e.preventDefault(); download(f.path||"arquivo.txt", f.content||""); });

    actions.appendChild(bCopy);
    actions.appendChild(bDl);

    const pre = document.createElement("pre");
    const code = document.createElement("code");
    code.textContent = f.content || "";
    pre.appendChild(code);

    details.appendChild(sum);
    details.appendChild(actions);
    details.appendChild(pre);
    root.appendChild(details);
  });
}

function offlineBanner(show) {
  $("#api-offline").style.display = show ? "block" : "none";
}

async function runCompare() {
  const API_BASE = $("#api-base").value.trim() || "http://127.0.0.1:8000";

  // LLM (provider-agnostic)
  const llm_api_url = $("#llm-url").value.trim();       // Groq OpenAI endpoint OR Gemini v1beta base
  const llm_api_key = $("#llm-key").value.trim();
  const model       = $("#model").value.trim();

  const repo = $("#repo").value.trim();
  const branch = $("#branch").value.trim() || "main";
  const include_ext = parseCSV($("#exts").value);
  const raw_paths = parseCSV($("#paths").value);
  const include_paths = raw_paths.length ? raw_paths : ["/"]; // default: whole repo
  const requisitos = $("#reqs").value;
  const github_pat = $("#pat").value.trim() || null;

  const allow_placeholders = $("#allow-placeholders").checked;
  const debug_echo_raw = $("#debug-echo-raw").checked;

  const debug_no_llm = !(llm_api_key && model && llm_api_url);

  $("#status").textContent = "enviando...";
  offlineBanner(false);
  setText($("#report code"), "");
  $("#summary").innerHTML = "";
  $("#files").innerHTML = "";
  setText($("#raw code"), "");

  try {
    const r = await fetch(`${API_BASE}/compare`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        repo,
        branch,
        include_ext,
        include_paths,
        requisitos,
        github_pat,
        debug_no_llm,
        // generic LLM config
        llm_api_url,
        llm_api_key,
        model,
        // steering + toggles
        prompt_base: PROMPT_BASE,
        allow_placeholders,
        debug_echo_raw,
      }),
    });

    const text = await r.text();
    if (!r.ok) {
      let msg = text;
      try {
        const j = JSON.parse(text);
        msg = j.detail || text;
      } catch {}
      throw new Error(msg);
    }

    const j = JSON.parse(text);
    setText($("#report code"), j.report || "");
    bullets($("#summary"), j.summary || []);
    renderFiles(j.updated_files || []);
    if (j.raw) setText($("#raw code"), j.raw);
    $("#status").textContent = "ok";
  } catch (e) {
    $("#status").textContent = "erro";
    offlineBanner(true);
    setText($("#report code"), "");
    bullets($("#summary"), [`falha: ${String(e).slice(0, 400)}`]);
    $("#files").innerHTML = "";
    setText($("#raw code"), "");
    lastFiles = [];
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("#run").addEventListener("click", runCompare);
  $("#download-all").addEventListener("click", ()=>{
    for (const f of lastFiles) download(f.path||"arquivo.txt", f.content||"");
  });

  // quick deep-linking
  const q = new URLSearchParams(location.search);
  if (q.get("api")) $("#api-base").value = q.get("api");
  if (q.get("llm")) $("#llm-url").value = q.get("llm");
  if (q.get("llm_key")) $("#llm-key").value = q.get("llm_key");
  if (q.get("model")) $("#model").value = q.get("model");
  if (q.get("repo")) $("#repo").value = q.get("repo");
  if (q.get("branch")) $("#branch").value = q.get("branch");
  if (q.get("exts")) $("#exts").value = q.get("exts");
  if (q.get("paths")) $("#paths").value = q.get("paths");
  if (q.get("allow")) $("#allow-placeholders").checked = q.get("allow") === "1";
  if (q.get("raw")) $("#debug-echo-raw").checked = q.get("raw") === "1";
  if (q.get("autorun") === "1") runCompare();
});

import { el, setText, bulletsToList, download } from "./util.js"
import { unifiedDiff } from "./diff.js"

// ---- remember key ----
let remember = false
export function bindRemember(){
  const btn = el("#remember")
  btn.addEventListener("click",()=>{
    remember = !remember
    btn.classList.toggle("active", remember)
    btn.textContent = remember ? "remember key ✓" : "remember key"
  })
}
export function shouldRemember(){ return remember }
export function setRemember(v){
  remember = !!v
  const btn = el("#remember")
  btn.classList.toggle("active", remember)
  btn.textContent = remember ? "remember key ✓" : "remember key"
}

// ---- expand/collapse editor: clamp ~20 linhas e auto-grow sem scrollbar ----
function setClampHeight(container, lines=20){
  const ta = container.querySelector("textarea")
  const cs = getComputedStyle(ta)
  const lh = parseFloat(cs.lineHeight || "18")
  const py = parseFloat(cs.paddingTop||"12")+parseFloat(cs.paddingBottom||"12")
  const max = Math.round(lh*lines + py)
  container.style.setProperty("--ta-max", `${max}px`)
}
function autosize(ta){
  ta.style.height = "auto"
  ta.style.height = ta.scrollHeight + "px"
}
export function bindExpand(){
  const wrap = el(".code-wrap")
  const ta   = el("#legacy")
  const btn  = el("#btn-expand")

  const sync = () => {
    const collapsed = wrap.classList.contains("collapsed")
    btn.textContent = collapsed ? "mostrar mais" : "mostrar menos"
    btn.setAttribute("aria-expanded", String(!collapsed))
    if (collapsed){
      // volta a usar o clamp controlado por CSS
      setClampHeight(wrap, 20)
      ta.style.height = ""
    } else {
      // cresce até caber todo conteúdo
      autosize(ta)
    }
  }

  btn.addEventListener("click", ()=>{
    wrap.classList.toggle("collapsed")
    sync()
  })

  // enquanto digita, só autosize quando expandido
  ta.addEventListener("input", ()=>{ if(!wrap.classList.contains("collapsed")) autosize(ta) })

  window.addEventListener("resize", sync)

  // init
  wrap.classList.add("collapsed")
  setClampHeight(wrap, 20)
  sync()
}

// ---- misc UI helpers ----
export function bindSample(setLegacy){
  el("#btn-sample").addEventListener("click",()=>{ 
    setLegacy(`public class Exemplo {
  public static void main(String[] args){
    System.out.println("Olá mundo");
  }
}`) })
}
export function bindRefactor(onRun){ el("#btn-refactor").addEventListener("click", onRun) }
export function readInputs(){
  return {
    language: el("#language").value,
    provider: el("#provider").value,
    model: el("#model").value.trim() || undefined,
    apiKey: el("#apikey").value.trim(),
    code: el("#legacy").value,
    save: shouldRemember()
  }
}
export function setInputs({provider,model,apiKey,save}){
  if(provider) el("#provider").value = provider
  if(model) el("#model").value = model
  if(apiKey) el("#apikey").value = apiKey
  setRemember(!!save || !!apiKey)
}
export function showBefore(code){ setText(el("#before code"), code||"") }
export function showAfter(code){ setText(el("#after code"), code||"") }
export function showMeta({before, after, notes, summary}){
  setText(el("#diff code"), unifiedDiff(before, after))
  bulletsToList(el("#notes"), notes)
  bulletsToList(el("#summary"), summary)
}
export function showError(msg){
  setText(el("#after code"), "")
  bulletsToList(el("#notes"), [`erro: ${msg}`])
}
export function bindDownload(getAfter){
  el("#btn-download").addEventListener("click",()=>{
    const out = getAfter()
    if(!out) return
    download("legacy_refatorado.txt", out)
  })
}
export function overlay(v){ el("#overlay").style.display = v ? "flex" : "none" }
export function status(t){ el("#status").textContent = t||"" }
export function mountState(){ let after=""; return { setAfter:v=>after=v, getAfter:()=>after } }

import { refactorBYO } from "./api_byo.js"
import { saveConfig, loadConfig } from "./config.js"
import { el } from "./util.js"
import {
  bindSample, bindRefactor, bindRemember, readInputs, setInputs,
  showBefore, showAfter, showMeta, bindDownload, overlay,
  mountState, showError, status, bindExpand
} from "./ui.js"

const state = mountState()
function setLegacy(v){ el("#legacy").value = v }

const cfg = loadConfig()
setInputs(cfg||{})

bindSample(setLegacy)
bindRemember()
bindExpand()

bindRefactor(async ()=>{
  const input = readInputs()
  if(!input.code.trim()) return
  if(!input.apiKey) { showError("api key ausente"); return }
  if(input.save) saveConfig({provider:input.provider,model:input.model,apiKey:input.apiKey,save:true})

  showBefore(input.code)
  overlay(true); status("rodando...")
  const t0 = performance.now()

  try{
    const r = await refactorBYO({
      provider: input.provider,
      model: input.model,
      apiKey: input.apiKey,
      code: input.code,
      language: input.language
    })
    if(!(r.code && r.code.trim())){
      showError(r.notes || "falha na refatoração")
    }else{
      showAfter(r.code||"")
      state.setAfter(r.code||"")
      showMeta({ before: input.code, after: r.code||"", notes: r.notes||[], summary: r.summary||[] })
    }
  }catch(e){
    showError(String(e))
  }finally{
    const ms = Math.round(performance.now()-t0)
    overlay(false); status(`${input.provider} · ${input.model||"auto"} · ${ms}ms`)
  }
})

bindDownload(()=>state.getAfter())

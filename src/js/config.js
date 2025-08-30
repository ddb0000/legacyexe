const K="legacyexe.v1"
export function saveConfig({provider,model,apiKey,save}){
  try{ localStorage.setItem(K, JSON.stringify({provider,model,apiKey,save:!!save})) }catch{}
}
export function loadConfig(){
  try{ return JSON.parse(localStorage.getItem(K)||"{}") }catch{ return {} }
}
export function hasSaved(){ try{ return !!(JSON.parse(localStorage.getItem(K)||"{}").apiKey) }catch{ return false } }

export function el(q){return document.querySelector(q)}
export function setText(node, text){node.textContent = text}
export function download(filename, text){
  const a = document.createElement("a")
  a.href = URL.createObjectURL(new Blob([text],{type:"text/plain"}))
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}
export function bulletsToList(node, s){
  node.innerHTML = ""
  if(!s) return
  const arr = Array.isArray(s) ? s : String(s).split(/[\r\n;•-]+/).map(x=>x.trim()).filter(Boolean)
  for(const p of arr.slice(0,12)){
    const li = document.createElement("li")
    li.textContent = p
    node.appendChild(li)
  }
}

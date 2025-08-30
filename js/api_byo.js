// -------- prompts --------
function sysRefactor(lang){
  return `Você é um agente de modernização de código.
Responda SOMENTE JSON válido:
{"code":"<código COMPLETO>", "summary":"<lista ou string>", "notes":"<lista ou string>"}.
NADA fora do JSON. Linguagem alvo: ${lang}.`;
}
function sysReview(lang){
  return `Você é revisor. Dado {original, refactored}, devolva SOMENTE:
{"code":"<código FINAL>", "notes":"<lista ou string>"}.
NADA fora do JSON. Linguagem: ${lang}.`;
}

// -------- util --------
function asArray(x){
  if (Array.isArray(x)) return x;
  if (x == null) return [];
  return String(x).split(/\r?\n|[;•]+/).map(s=>s.trim()).filter(Boolean);
}
function looksLikeCode(s, lang){
  if (!s) return false;
  const t = String(s).trim();
  if (t.length < 10) return false;              // evita "200", "ok"
  if (!/[;\n{}()=]/.test(t)) return false;      // precisa ter “cara” de código
  const L = (lang||"").toLowerCase();
  const KW = {
    java: /\b(class|public|static|void|import|try|catch|package)\b/,
    python: /\b(def|import|class|return|with|try|except)\b/,
    javascript: /\b(function|const|let|import|export|class|=>)\b/,
    csharp: /\b(namespace|class|using|public|static|void)\b/
  };
  const rx = KW[L] || /./;
  return rx.test(t);
}
function normalize(obj){
  if (obj == null || typeof obj !== "object")
    return { code:"", summary:[], notes: obj==null ? [] : [String(obj)] };
  const code = obj.code != null ? String(obj.code) : "";
  const summary = asArray(obj.summary);
  const notes = asArray(obj.notes);
  return { code, summary, notes };
}
function safeJSON(s){
  // tenta direto
  try{ return normalize(JSON.parse(s)) }catch{}
  // tenta bloco ```json
  const m = String(s).match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (m){ try{ return normalize(JSON.parse(m[1])) }catch{} }
  // tudo falhou → devolve em notes
  return { code:"", summary:[], notes:String(s||"") };
}

// -------- providers --------
async function callOpenAI({apiKey,model,messages}){
  const r = await fetch("https://api.openai.com/v1/chat/completions",{
    method:"POST",
    headers:{authorization:`Bearer ${apiKey}`,"content-type":"application/json"},
    body:JSON.stringify({model:model||"gpt-4o-mini",temperature:0.2,messages})
  });
  const t = await r.text();
  if(!r.ok) throw new Error(t);
  const j = JSON.parse(t);
  return j.choices?.[0]?.message?.content ?? "";
}
function toGemini(messages){
  // Gemini 1.5 aceita responseMimeType = "application/json"
  return messages.map(m=>({role:m.role==="system"?"user":m.role,parts:[{text:String(m.content)}]}));
}
async function callGemini({apiKey,model,messages}){
  const r = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model||"gemini-1.5-flash"}:generateContent?key=${apiKey}`,
    {
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({
        contents: toGemini(messages),
        generationConfig: {
          temperature: 0.2,
          responseMimeType: "application/json"   // força JSON puro
        }
      })
    }
  );
  const t = await r.text();
  if(!r.ok) throw new Error(t);
  const j = JSON.parse(t);
  // quando responseMimeType=JSON, vem em parts[0].text como string JSON
  return j.candidates?.[0]?.content?.parts?.map(p=>p.text||"").join("") ?? "";
}

// -------- main --------
export async function refactorBYO({provider,model,apiKey,code,language}){
  const m1 = [
    { role:"system", content: sysRefactor(language) },
    { role:"user",   content: `original:\n\`\`\`${language}\n${code}\n\`\`\`` }
  ];
  const raw1 = provider==="openai"
    ? await callOpenAI({apiKey,model,messages:m1})
    : await callGemini({apiKey,model,messages:m1});
  const j1 = safeJSON(raw1);             // {code, summary[], notes[]}

  const m2 = [
    { role:"system", content: sysReview(language) },
    { role:"user",   content: JSON.stringify({original:code,refactored:j1.code||""}) }
  ];
  const raw2 = provider==="openai"
    ? await callOpenAI({apiKey,model,messages:m2})
    : await callGemini({apiKey,model,messages:m2});
  const j2 = safeJSON(raw2);             // {code, notes[]}

  // valida “cara de código”
  const code2ok = looksLikeCode(j2.code, language);
  const code1ok = looksLikeCode(j1.code, language);

  const finalCode = code2ok ? j2.code : (code1ok ? j1.code : "");
  const finalNotes = [
    ...(j2.notes||[]),
    ...(code2ok ? [] : ["review sem código válido"]),
    ...(code1ok ? [] : ["refactor sem código válido"])
  ].filter(Boolean);

  return { code: finalCode, summary: j1.summary||[], notes: finalNotes };
}

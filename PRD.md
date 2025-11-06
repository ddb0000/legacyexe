# 🧠 **PRD — LEGACY.exe (Ford Challenge 2025)**

## 🏁 **Contexto**

A Ford enfrenta o desafio de modernizar sistemas legados que ainda rodam em tecnologias antigas (Java 6–11, Struts 1.3, JSF, JAX-RS e AngularJS).
Essas aplicações críticas atrasam o ciclo de desenvolvimento, elevam custos e dificultam a integração com novas plataformas em Java 21, Spring Boot e front-ends modernos.

O **LEGACY.exe** foi criado como uma interface de IA Generativa para:

* automatizar a refatoração de código legado,
* sugerir migrações de frameworks,
* gerar código atualizado e validado,
* e produzir relatórios explicativos sobre as mudanças aplicadas.

---

## 🚀 **Objetivo**

Reduzir o esforço manual e a dependência de especialistas em código legado, entregando um **ponto de partida funcional** para migrações tecnológicas com **apoio de IA Generativa** (OpenAI / Gemini / Groq / outros).

---

## 💡 **Proposta de Valor**

* **Refatoração automática** de trechos legados (Java, JS, C#).
* **Comparador de código** antes/depois com análise de impacto.
* **Explicação textual e resumo executivo** em linguagem natural.
* **Arquitetura BYO-KEY serverless-ready** (funciona client-side).

---

## ⚙️ **MVP Atual**

* **Frontend:** HTML+JS puro (modularizado em `/js`)
* **Modo BYO-KEY:** usuário insere a própria API key (OpenAI ou Gemini)
* **Output:** novo código, diff e resumo em JSON
* **Deploy:** pode rodar estático (GitHub Pages / S3)
* **Backend opcional:** FastAPI/Express server para log e auditoria

---

## 🧩 **Próximas Iterações (Fase 7)**

### 🎯 Sprint 2 — Integração com Ford Frameworks

> incorporar exemplos reais dos frameworks legados que a Ford listou.

**Objetivo:** usar os repositórios reais para gerar contexto, samples e prompt engineering mais preciso.

**Frameworks alvo:**

| Framework     | Link                                                                                                          | Migração recomendada      |
| ------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------- |
| Struts 1.3    | [ShradhaPandey/Struts-1.3-demo-project](https://github.com/ShradhaPandey/Struts-1.3-demo-project)             | Spring Boot / MVC         |
| Jakarta Faces | [hantsy/jakartaee-faces-sample](https://github.com/hantsy/jakartaee-faces-sample)                             | Thymeleaf / Quarkus       |
| JAX-RS        | [roshangade/jax-rs-example](https://github.com/roshangade/jax-rs-example)                                     | Spring WebFlux / RESTEasy |
| AngularJS     | [gothinkster/angularjs-realworld-example-app](https://github.com/gothinkster/angularjs-realworld-example-app) | Angular 17 / React / Vue  |

---

## 🧱 **Arquitetura Técnica**

**Frontend:**

* `index.html` + módulos JS (api_byo.js, ui.js, diff.js, etc.)
* roda 100% client-side, com storage local opcional
* envia prompts estruturados via API LLM (OpenAI ou Gemini)

**Backend (opcional):**

* Node ou Python (Express / FastAPI)
* endpoints `/api/refactor`, `/api/analyze`
* logging e histórico em S3/DynamoDB

**Fluxo de Execução:**

```
Input Code → Prompt Generator (language + provider)
→ LLM (Gemini/OpenAI)
→ JSON Output { code, notes, summary }
→ Diff Engine → UI Render
```

---

## 🧩 **Roadmap Técnico / Tasks para o Agent**

### 🧠 1. Prompt Engineering — Migração Ford

* [ ] Adicionar **preset de refatoração por framework**
  ex: `refatorar código Struts 1.3 para Spring Boot MVC`
* [ ] Detectar automaticamente o framework (regex/heurística simples)
* [ ] Adicionar lista de **melhores práticas por framework** no prompt system message.

### 🧰 2. Integração no Front-End

* [ ] Adicionar dropdown “Framework alvo” (Struts, JSF, AngularJS etc.)
* [ ] Gerar prompt automático com base na escolha do usuário
* [ ] Salvar último framework usado no localStorage

### 🧾 3. UX/UI Ajustes

* [ ] Melhorar layout da área de código (tela central, botões abaixo)
* [ ] Adicionar botão “Sample Ford” com exemplo real de código Struts
* [ ] Atualizar copy em PT-BR (labels, tooltips)
* [ ] Adicionar indicador visual de “modo gemini / modo openai”

### 📊 4. Logging e Métricas (opcional)

* [ ] Enviar logs (input + provider + tempo de execução) para console ou endpoint `/logs`
* [ ] Mostrar tempo de resposta e provider usado na UI

### 🧩 5. MVP Demo Mode

* [ ] Criar `demoMode=true` no config.js que retorna respostas fixas (sem API key)
  → útil pra demo no vídeo e banca

---

## 🎬 **Entrega (Sprint 2 - Ford Challenge)**

**Pacote Final (ZIP):**

```
/legacy-exe/
 ├── index.html
 ├── js/
 │   ├── api_byo.js
 │   ├── app.js
 │   ├── ui.js
 │   ├── diff.js
 │   └── util.js
 ├── assets/ (imgs do vídeo)
 ├── README.md
 ├── repomix-output.md
 ├── PRD.md
 └── PDF_com_link_video.pdf
```

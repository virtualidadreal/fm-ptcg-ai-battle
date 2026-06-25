# Las dos competiciones — cómo se relacionan

El reto es UNA cosa repartida en **dos competiciones Kaggle conectadas**. Hay que entrar en las dos
para optar a premio.

## 1. Simulation — `pokemon-tcg-ai-battle`

- **Qué es:** la competición técnica. Construyes el **agente Python** (`main.py` + `deck.csv`), se sube al
  **ladder** y juega episodios contra otros agentes. Rating gaussiano μ₀=600.
- **Entregable:** `.tar.gz` con el agente. 5 envíos/día, 2 finales.
- **Premio:** **NINGUNO** (n/a). Solo medallas/puntos Kaggle + tu posición en el leaderboard.
- **Fechas:** start 16 jun · final submission **16 ago** · convergencia hasta 31 ago.
- **Rol:** es el **motor de puntuación**. Tu rendimiento aquí ALIMENTA la Strategy.

## 2. Strategy / Hackathon — `pokemon-tcg-ai-battle-challenge-strategy`

- **Qué es:** la competición de premios. Entregas un **REPORT escrito (máx 2.000 palabras)** explicando
  lógica estratégica, concepto de mazo y decisiones de diseño.
- **Evaluación (pesos) — el dato clave:**
  - **70% — enfoque del modelo** (cómo está pensado/construido el agente). NO es win rate puro.
  - **20% — concepto del mazo**.
  - **10% — calidad del report**.
  El rendimiento en la Simulation alimenta la valoración, pero el grueso (70%) es la **metodología**.
  → Aquí el **Dev Aumentado + disciplina anti-falso-positivo** es una historia diferenciadora real ante
    un jurado tipo Matsuo Institute / HEROZ.
- **Premios (>$290K total) — DINERO REAL (cash), no créditos:**
  - **Ronda 1 (Strategy):** Top 8 equipos → **$30.000 en metálico cada uno** + pase a la final.
  - **Ronda 2 (Final Stage, presencial en Tokio):** los agentes de los 8 equipos compiten en un **torneo
    en vivo retransmitido por el YouTube oficial de Pokémon**. 1º **+$50.000 cash**, 2º **+$30.000 cash**.
    Formato exacto del torneo (bracket/liga, bo-N, fecha) **por confirmar**. En la final NO se itera:
    compite el agente ya clasificado.
  - **Extra:** todos los finalistas reciben además **$3.000/persona en créditos Google Cloud**
    (esto es lo único que es crédito; es un añadido encima del cash).
  - El cash imponible es a cargo del ganador. Premio de equipo se reparte a partes iguales salvo pacto.
  - ⚠️ Confirmar montos/condiciones en la **pestaña Prizes oficial de la Strategy** al verificar la cuenta.
- **Fechas:** corre jun → ~sept 2026. Final Stage en septiembre, presencial en Tokio (fecha por confirmar).

## Lectura estratégica

- **El leaderboard de la Simulation es condición necesaria pero NO suficiente.** Un agente top sin buen
  report no maximiza premio; un report brillante con agente mediocre tampoco.
- **Objetivo real = Top 8 de la Strategy** → ahí está el primer $30K. Eso exige:
  1. Agente fuerte y **estable** en el ladder (Simulation).
  2. **Mazo con concepto** defendible (no solo netdeck del meta).
  3. **Report** que cuente bien la metodología (aquí nuestro Dev Aumentado + disciplina anti-falso-positivo
     es una HISTORIA diferenciadora que el jurado puede premiar).
- El Final Stage es **presencial en Japón** (sept) → si llegamos, hay viaje. Tenerlo en cuenta vs el bloque HA.

## Fuentes
- Reglas Simulation: web oficial de la comp (guardadas en RULES.md).
- Estructura/premios: PokéBeach, Dexerto, Shane the Gamer (jun 2026).

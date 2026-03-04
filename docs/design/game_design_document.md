# Documento de Diseño de Juego (Producción)

## 1. Propósito
CHAKANA es un roguelike de cartas con identidad andina, sesiones cortas (20–35 min) y decisiones tácticas claras por turno.

## 2. Pilar de diseño
- **Legibilidad:** el jugador entiende estado, intención enemiga y resultado esperado.
- **Decisión significativa:** cada carta, ruta y recompensa implica costo de oportunidad.
- **Cadencia rápida:** turnos ágiles, poca fricción de navegación.

## 3. Loop base
1. Elegir ruta en mapa.
2. Resolver nodo (combate / evento / tienda / reliquia / boss).
3. Obtener recompensa (carta/oro/xp).
4. Ajustar mazo/sideboard.
5. Repetir hasta boss o derrota.

## 4. Reglas de producción
- Cambios de gameplay deben incluir impacto en: combate, mapa, economía y UX.
- Cada feature nueva requiere criterio de aceptación medible.
- No mezclar refactor grande con feature en el mismo PR.

## 5. Criterios de “hecho”
- UI funcional + textos localizados ES.
- Validación mínima ejecutada (compilación o smoke).
- Sin regresiones críticas en navegación (menu/map/combat/reward).

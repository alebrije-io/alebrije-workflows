# Technical Debt — alebrije-workflows

> Updated: 2026-05-07. Per ADR-001 tracking.

## Census — 2026-08-21 (censo por cuerpo, no por titulo)

Se releyeron los 25 encabezados con cadena `DEBT` que existen hoy en este archivo (`grep -niE
'^#.*debt' TECHNICAL-DEBT.md`, excluyendo la linea 1 que es el titulo del documento) — **no el
titulo, el `Status:`/`FIXED`/`CLOSED` real dentro del cuerpo**. Resultado:

| Categoria | Cuenta | Detalle |
|---|---|---|
| **CERRADO** | 6 | DEBT-W14 (property-tests mask, dos veces con el mismo ID — **renumerado a DEBT-W17 el 2026-08-22, ver esa entrada**), DEBT-W13 (envelope AQ-112), DEBT-§43-SUPPLY-CHAIN-6, DEBT-§43-SUPPLY-CHAIN-7, DEBT-§44-CONTRACT-GAP-RECONCILE |
| **ABIERTO** | 18 | DEBT-001 (REABIERTO esta sesion — ver abajo, no es el mismo P1 original), DEBT-002, DEBT-003, DEBT-004, DEBT-005, DEBT-W01, DEBT-W02, DEBT-W03, DEBT-W04, DEBT-W05, DEBT-W06, DEBT-W07, DEBT-W08 (alcance corregido), DEBT-W09, DEBT-W10, DEBT-W11, DEBT-W12, DEBT-W15 |
| **AMBIGUO** | 1 | La linea `## §44 — DEBT-FN-ADR-79-EVENT-BUS-SCHEMA-REGISTRY (infra-CI portion) reconciliation` (encabezado de SECCION, no de item) contiene la cadena `DEBT-` y por eso el regex la cuenta como un 25º encabezado, pero no tiene su propio bloque `Status:` — es el envoltorio del unico item real que cuelga debajo, `DEBT-§44-CONTRACT-GAP-RECONCILE` (linea inmediatamente siguiente). Contarla como ticket independiente duplica el mismo ticket dos veces. |

**Suman 25** (6+18+1). Dos hallazgos de la propia auditoria, no del contenido:

1. **El numero de "abiertos" que traia el encargo (19) no es el real (18).** El heuristico de
   encabezado-con-palabra-clave (ya corregido para reconocer `DONE` ademas de
   `FIXED|RESUELTO|CLOSED|CERRADO|RESOLVED`) cuenta 6 headers con esa palabra en el TITULO — los
   mismos 6 que el censo por cuerpo confirma CERRADOS, asi que en eso acertó — pero cuenta la
   linea `## §44 — DEBT-...` de arriba como un item "abierto" mas cuando en realidad es el
   envoltorio de un item que YA esta contado. 25 titulos − 6 cerrados = 19 "abiertos" por
   heuristico; 25 titulos − 6 cerrados − 1 envoltorio-sin-status = **18 abiertos reales**.
2. **`DEBT-001` estaba marcado `Status: CLOSED` en el cuerpo y la cifra `19` YA lo daba por
   abierto** (el titulo `## DEBT-001 — Missing scripts/gen-api-collection.sh` no trae ninguna
   palabra de cierre, así que el heuristico lo contaba abierto pese al cuerpo decir CLOSED) — es
   decir el heuristico acertó por la razón equivocada: no leyó el cuerpo, y el cuerpo mentia.
   Ver el REABIERTO abajo: el cierre original era falso por "existe" ≠ "funciona", así que el
   heuristico y el censo real coinciden en ABIERTO para este item, pero por motivos opuestos.

**Metodo de correlacion en las dos direcciones** (para no repetir la trampa de "0 hits = limpio"):
para cada uno de los 6 marcados CERRADO en el cuerpo hice al menos una verificacion externa al
propio texto del archivo (grep contra el workflow/action real que el item dice haber tocado) antes
de aceptar la marca. Confirmado con evidencia in-situ: DEBT-W14 (linea 222, `check-no-deprecated-set-output`
existe en `validate-self.yml:536` y esta en la lista `needs:` del summary), DEBT-§43-SUPPLY-CHAIN-6
(`Gate — validate Dockerfile base images against whitelist` existe en `reusable-build-push.yml:132`),
DEBT-§44-CONTRACT-GAP-RECONCILE (`alebrije-mod-campaigns-ex` y `alebrije-svc-notifications-ex`
aparecen en `event-schemas/consumers.yaml`). No se re-verificaron §43-7, W13 y W14(linea173) linea
por linea contra codigo externo — su cuerpo trae su propia evidencia citada (comandos + salidas) y
no hubo señal de alarma al leerlos completos.

---

## Census — 2026-08-22 (re-medido sobre el arbol de hoy, mismo metodo por cuerpo)

PASO 0 del encargo de hoy: se repitio EXACTO el metodo del censo 2026-08-21 (`grep -niE
'^#.*debt' TECHNICAL-DEBT.md`, excluyendo linea 1, leyendo el `Status:` del CUERPO, no el
titulo) sobre el arbol tal como estaba ANTES de tocar nada en esta sesion.

**Resultado antes de esta sesion: 25 headers, 6 CERRADO, 18 ABIERTO, 1 envoltorio — IDENTICO al
censo 2026-08-21.** El arbol no habia cambiado (mismo HEAD, `ae00b11`), asi que el censo se
reproduce exacto — no hay drift que reportar entre las dos fechas. **El encargo decia 18 y
midio 18 real: no hubo discrepancia que corregir esta vez** (a diferencia de la ronda anterior,
donde el heuristico daba 19 y el real era 18).

Ordenados por PEOR RAZON (lo que hoy deja pasar algo malo primero, no lo mas barato), con
evidencia REAL citada — no supuesta — para cada uno:

1. **DEBT-001** — un generador que sale con exit 0 e imprime "Generated API collection" mientras
   es ciego al 100% de las rutas reales del gateway de la flota. Peor patron de los 18: exito
   FALSO-POSITIVO, no una ausencia declarada. Ya habia sido cerrado en falso una vez.
2. **DEBT-W07** — `validate-self.yml` (el propio gate de CALIDAD de este repo, ADR-001 Bloque R)
   valida la estructura de `event-schemas/*.json` pero tenia CERO validacion de
   `approved-base-images.json` — el archivo que gatea los builds Docker de ~33 repos de la flota
   (DEBT-§43-SUPPLY-CHAIN-6/7). Un edit malformado podia fusionarse a `main` sin que NINGUN gate
   de este repo lo notara, y detonar en el siguiente build de cualquiera de los 33 consumidores.
   Mayor radio de explosion de los 18 (toda la flota, no solo este repo).
3. **DEBT-W12** — la pregunta de si el masking del vault token depende de la accion upstream
   quedo CONTESTADA con evidencia (no supuesta): se leyo el fuente real de
   `hashicorp/vault-action@4c06c5ccf5c0761b6029f56cfb1dcf5565918a3b` (el SHA pineado que usa
   `setup-vault-token/action.yml`) — `src/action.js:91` hace `core.setSecret(vaultToken)`
   INCONDICIONAL, ANTES del `if (outputToken === true)` de la linea 95. El masking NO depende de
   nada configurable: corre siempre. Pero verificar esto destapo un defecto REAL adyacente:
   `setup-vault-token/action.yml` nunca pasa `outputToken: true` a la accion pineada, y
   `outputToken` por default es `'false'` (`action.yml` upstream linea ~66) — asi que el output
   propio `vault-token` que la accion de este repo declara (`outputs.vault-token` →
   `steps.vault.outputs.vault_token`) JAMAS se puebla, es string vacio siempre. Mismo patron
   "existe pero no funciona" que DEBT-001. Radio HOY: cero — `grep -rln "setup-vault-token"
   alebrije-*/.github` en los 33 repos del cowork no encontro NINGUN caller — pero un futuro
   consumidor que confie en ese output se encuentra con nada. Queda ABIERTO porque no ejecute la
   accion compuesta contra un Vault+K8s-auth real (no hay uno disponible aqui) — leer el fuente
   no es lo mismo que correrlo, y la regla de esta unidad es explicita: lo que no se ejecuta no
   se cierra.
4. **DEBT-W02** — la estructura del CRD de Flagger puede estar mal. Verificado que el mecanismo
   de aplicacion (`apply-weight.sh --method istio` Y el paso inline equivalente en
   `trigger-canary/action.yml`) falla RUIDOSO si el `kubectl patch` no aplica
   (`::warning::Failed to patch Canary CRD` + `exit 1`), no en silencio — si el campo del CRD
   esta mal, el deploy de canary FALLA, no finge exito con 0% de trafico canario. Riesgo real de
   correccion sigue abierto (nadie lo probo contra un Flagger real), pero el modo de fallo es
   fail-closed, no silencioso — por eso rankea debajo de W12. Sin cluster con Flagger disponible
   aqui para probarlo.
5. **DEBT-002** — 27 tipos de evento publicados sin schema registrado. Verificado en
   `reusable-event-schema-check.yml` (lineas 41-45 y 175-176): `fail-on-missing` es `true` por
   default y es FATAL para cualquier tipo de evento NUEVO que un repo empiece a publicar de hoy
   en adelante — el gate NO deja pasar drift nuevo en silencio. Lo que falta es back-fill
   retroactivo de los 27 tipos anteriores al gate. Acotado y ya declarado correctamente.
6. **DEBT-W10** — `validate-test-pool.sh` alcance solo-Python. Verificado que NO es codigo
   vestigial: esta copiado y en uso real en `alebrije-svc-auth/scripts/validate-test-pool.sh` y
   `alebrije-mod-control-medico/scripts/validate-test-pool.sh`, invocado desde el `run_prepush.sh`
   de cada uno — cumple su promesa para esos dos. El hueco real es que la mayoria Go/Elixir de la
   flota (~30 de ~33 repos) no tiene ningun detector de tests huerfanos, ni existe una version
   Go/Elixir en este repo-fuente para que la copien.
7. **DEBT-W06** — `reusable-notify.yml` no tiene canal PagerDuty. Verificado que el switch de
   canal (`case ... in slack|email|github|all|*) ... exit 1`) falla RUIDOSO ante un valor no
   reconocido — no es un no-op silencioso, es una ausencia de feature declarada y acotada.
8. **DEBT-W04** — `cross-repo-trigger.yml` no abre PRs en repos consumidores.
9. **DEBT-004** — mismo hueco de raiz que W04 desde el otro lado (bump automatico cross-fleet):
   sin bot de PRs, el fallback manual sigue funcionando, solo mas lento.
10. **DEBT-W01** — `reusable-release-extended.yml` sin goreleaser/docker/cosign — incompleto
    desde que se escribio, no una promesa rota.
11. **DEBT-W15** — agregacion de run-ids en matrix se colapsa al ultimo leg — reduce
    observabilidad de correlacion, no causa un deploy incorrecto.
12. **DEBT-005** — `ci-cost-aggregator.yml` necesita GH App token que no existe todavia.
13. **DEBT-W05** — mismo `ci-cost-aggregator.yml`, falta reporte a Slack — bloqueado por lo mismo
    que 005 (sin webhook configurado).
14. **DEBT-003** — self-hosted runners diferido por decision explicita de volumen — cero riesgo
    funcional hoy.
15. **DEBT-W11** — 21 campos requeridos en schemas de eventos sin `description` — completitud de
    documentacion DENTRO del schema, no afecta la logica de validacion (ya enforced aparte).
16. **DEBT-W03** — template de `generate-postmortem` incompleto — plantilla, sin dependencia
    externa.
17. **DEBT-W09** — README sin ejemplos de uso Go/Elixir/TS — documentacion pura.

**Cerrados DE VERDAD en esta sesion (mecanismo corrido, control en las dos direcciones — ver
cada entrada abajo para el comando+salida): DEBT-001, DEBT-W07, DEBT-W08.** Post-cierre: 25
headers (sin cambio — cerrar no agrega ni quita encabezados), 9 CERRADO (6+3), **15 ABIERTO**
(18−3), 1 envoltorio. 9+15+1=25.

**Hallazgo colateral, fuera del alcance de los 18** (ver seccion "Hallazgo colateral" al final
del archivo): al re-verificar con Regla 13 el patron de `tests/test_approved_base_images.py`
(paso previo obligatorio antes de escribir el test nuevo de W07), su prueba preexistente
`test_catalog_covers_every_real_fleet_base_image` **fallaba YA en HEAD, antes de que esta sesion
tocara nada** — confirmado corriendo la copia de `git show HEAD:tests/test_approved_base_images.py`
sin ningun cambio mio. No es uno de los 18 y no se toca en esta sesion (el fix cambia el
mismisimo matcher de produccion que gatea 33 repos — requiere su propio diseno, no un parche de
pasada); queda documentado para que no se pierda.

---

## Continuacion 2026-08-22 — ronda 2 (los 15 restantes + auditoria de `scripts/`)

**Re-medicion PASO 0, mismo metodo, sobre el arbol heredado de la ronda 1** (HEAD `101c0fc`,
ya en `origin/main`): `grep -niE '^#.*debt' TECHNICAL-DEBT.md | tail -n +2 | wc -l` → **25**
(identico), 9 CERRADO (identico), **15 ABIERTO** (identico), 1 envoltorio. El arbol no habia
cambiado desde el cierre de la ronda 1 — la cifra hereda sin discrepancia. Confirma la foto del
encargo: `DEBT-002, 003, 004, 005, W01..W06, W09..W12, W15`.

**Auditoria de `scripts/` (punto 2 del encargo — buscar mas mecanismos ciegos como DEBT-001)**:
el directorio tiene exactamente 4 scripts (fuera de `__pycache__`):
`gen_api_collection.py`+`gen-api-collection.sh` (YA arreglados en la ronda 1, DEBT-001) y
`fe_be_audit.py`+`audit-fe-be-contracts.sh` (el otro par que produce un conteo). Corrido contra
la flota real:
```
$ python3 scripts/fe_be_audit.py --json   # invocado SIN el staging que hace reusable-contract-check.yml
{'fe_endpoints': 0, 'be_endpoints': 0, 'matched': 0, 'fe_only': 0, 'be_only': 0}
```
**Primera impresion: parece el mismo bug que DEBT-001 (0 total).** Verificado que NO lo es —
`fe_be_audit.py` resuelve `WORKSPACE = Path(__file__).resolve().parent.parent`, que solo apunta
al workspace real (el folder que CONTIENE `alebrije-frontend/`, `alebrije-mod-*/`, etc. como
hermanos) cuando el script vive en `<workspace>/scripts/fe_be_audit.py` — exactamente como
`reusable-contract-check.yml:109-115` lo deja (`cp workflows/scripts/fe_be_audit.py scripts/`,
ejecutado desde la raiz del workspace). Corrido con ese staging real replicado a mano
(`cp` a la raiz del cowork, que SI contiene los 14 repos hermanos como submodulos de directorio):
```
$ python3 scripts/fe_be_audit.py --json   # staged como CI lo hace, WORKSPACE = raiz real
{'fe_endpoints': 931, 'be_endpoints': 1580, 'matched': 571, 'fe_only': 360, 'be_only': 1009}
```
No vaciamente cero — **veredicto: LIMPIO, no ciego**, cuando se invoca como CI lo invoca.
Y la invocacion "incorrecta" (desde dentro de `alebrije-workflows/`, sin staging) **tampoco miente**:
cada modulo sale marcado `backend_missing=True` explicitamente (consola Y markdown dicen
`(backend missing)` / `| missing |`), y `--strict` (el default real de
`reusable-contract-check.yml`, `inputs.strict: default: true`) devuelve **exit 1** en ese estado
— confirmado corriendo `python3 scripts/fe_be_audit.py --strict` sin staging → `STRICT_EXIT=1`.
Fail-closed por diseño, lo opuesto al patron DEBT-001. No se encontro un segundo mecanismo ciego
en `scripts/`; los 4 scripts existentes quedan auditados.

**El hallazgo principal de esta ronda no salio de `scripts/` — salio de re-verificar DEBT-W02
contra el schema real de Flagger** (fetched, no adivinado): la ranking original de la ronda 1
puso a DEBT-W02 en el puesto #4 por "el modo de fallo es fail-closed"; esa conclusion solo era
cierta para el CLI standalone `apply-weight.sh` en el metodo istio revisado superficialmente —
al aplicar el schema real contra un `Canary` CR real en el cluster docker-desktop, el campo que
patchea (`spec.analysis.canary.maxWeight`) **no existe** en el CRD real y el API server lo
**PRUNEA en silencio** (structural schema, `apiextensions.k8s.io/v1`) — exit 0, "patched (no
change)", el peso real nunca cambia. Y `apply-weight.sh --method istio` tiene 2 llamadores reales
en `reusable-canary-deploy.yml` (no es codigo muerto). Esto es el patron DEBT-001 sobre un
camino de deploy EN VIVO, no sobre un script sin llamadores — **peor razon que cualquiera de los
15 originales**. Re-rankeado a #1, por delante de DEBT-W12. Ver la entrada `DEBT-W02` completa
mas abajo para el comando+salida real de la prueba en las dos direcciones.

**Cerrados DE VERDAD en esta ronda: DEBT-W02, DEBT-W03, DEBT-W09, DEBT-W11** (4 de 15, mecanismo
corrido + control en las dos direcciones cada uno — ver su propia entrada mas abajo). Post-cierre:
25 headers (sin cambio), **13 CERRADO** (9+4), **11 ABIERTO** (15−4), 1 envoltorio. 13+11+1=25.

**Orden final por PEOR RAZON de los 15 que entraron a esta ronda** (1=peor, cerrado marcado):
1. **DEBT-W02** — CERRADO. Camino de deploy EN VIVO, silenciosamente no-op (ver arriba).
2. **DEBT-W12** — abierto, ver su entrada: fix enviado (agregar `outputToken: 'true'`), pero el
   auth kubernetes E2E real sigue sin ejecutarse (razon medida, no supuesta — ver abajo).
3. **DEBT-002** — abierto, sin cambio de razon (backfill de 27 schemas es trabajo real de
   varios repos, no una sesion).
4. **DEBT-W10** — abierto, sin cambio de razon.
5. **DEBT-W06** — abierto, sin cambio de razon.
6. **DEBT-W04** — abierto, sin cambio de razon.
7. **DEBT-004** — abierto, sin cambio de razon.
8. **DEBT-W01** — abierto, sin cambio de razon.
9. **DEBT-W15** — abierto, sin cambio de razon.
10. **DEBT-005** — abierto, sin cambio de razon.
11. **DEBT-W05** — abierto, sin cambio de razon.
12. **DEBT-003** — abierto, decision explicita del user, sin cambio.
13. **DEBT-W11** — CERRADO.
14. **DEBT-W03** — CERRADO.
15. **DEBT-W09** — CERRADO.

(W11/W03/W09 quedan bajos en la lista de PEOR RAZON — documentacion/metadata pura, sin riesgo de
produccion — pero se cerraron igual porque el efecto/costo de cerrarlos era bajo y real, dejando
mas presupuesto de sesion para medir W02 a fondo, que si importaba.)

**Hallazgo adicional, fuera de los 15 pero directamente encima de DEBT-002** (ver la entrada
`DEBT-002` completa arriba en el documento): al re-medir su cifra "~27" con el instrumento real
(`reusable-event-schema-check.yml`, extraido y corrido contra los 19 repos hermanos reales), el
instrumento devolvio **0 candidatos de tipo evento en cada uno de los repos Go/Elixir muestreados**
— no porque esos repos no publiquen eventos (rewards-go publica al menos 9 tipos reales por su
propio `events_publisher.go`), sino porque el regex del check (`"event_type"\s*:\s*"..."`, estilo
JSON/dict) no reconoce ni la asignacion de campo de struct de Go (`e.EventType = "..."`) ni el
keyword/map de Elixir (`event_type: "..."`, sin comillas en la clave) — y el patron de archivos
(`PUBLISHER_GLOBS`) tampoco cubre el nombrado real `outbox_*_publisher.go` que este proyecto usa
para el patron outbox. Encontrado en vivo: `cadences.reply.received` se emite hoy en
`alebrije-mod-cadences-ex/lib/alebrije_cadences/reply_detection.ex:72` y **no tiene schema
registrado** — drift real, no hipotetico, invisible para el gate que 10 repos consumidores ya
tienen cableado en su CI (`DEBT-§44-CONTRACT-GAP-RECONCILE`). No se arregla en esta sesion — el
radio (10 repos consumidores reales) exige primero correr el detector arreglado en modo
report-only y triar el backfill antes de subir el gate a fatal; ver el spec dejado en la entrada
`DEBT-002` para la proxima ronda. Esto es mas grande que cualquiera de los 15 originales: no es un
item mal cerrado, es el CENSO del que salio la cifra del ticket el que estaba ciego.

---

## Continuacion 2026-08-22 — confirmacion de ronda 2 (censo re-derivado + auditoria de supresiones en `scripts/`)

**PASO 0, re-derivado de forma independiente (no releyendo el texto de arriba, parseando el
CUERPO de cada header programaticamente)** sobre el arbol de hoy, HEAD `975cb5a` (el mismo que
dejo la ronda anterior — nada lo toco entre medias):

```
$ grep -niE '^#.*debt' TECHNICAL-DEBT.md | tail -n +2 | wc -l
25
```

Y para cada uno de los 25, se extrajo su campo `Status` real del cuerpo (no del titulo) con un
parser propio. **Primer intento del parser: MINTIO** — un regex que solo reconocia `**Status**:`
en negritas paso por alto `DEBT-W05`/`DEBT-W06` (que escriben `- **Effort**: S — Status: OPEN`,
sin negrita en la palabra `Status`) y `DEBT-W13` (`Effort: XS — Status: **CLOSED**`), y los conto
como "envoltorio sin status" en vez de ABIERTO/CERRADO — dio **12 CERRADO / 9 ABIERTO / 4
envoltorio** (suma 25, pero la distribucion es falsa). Corregido el regex para buscar `Status`
en cualquier parte de la linea (con o sin negrita), se re-corrio:

```
$ python3 /private/tmp/claude-501/-Users-ileonelperea-Documents-cowork-personal-alebrije/5a322fb4-3159-4520-a95f-268e09f73069/scratchpad/census-body-parser-workflowsronda2.py TECHNICAL-DEBT.md | tail -2
total headers: 25
CERRADO: 13 ABIERTO: 11 envoltorio: 1 sum: 25
```

**13 CERRADO, 11 ABIERTO, 1 envoltorio (el header `## §44 — ...` que envuelve a
`DEBT-§44-CONTRACT-GAP-RECONCILE`, sin `Status` propio) — IDENTICO a lo que esta seccion ya
afirmaba.** No hay drift que corregir: el censo de la ronda anterior era correcto; lo que fallo
fue mi PRIMER intento de reproducirlo con un parser demasiado estricto — exactamente el tipo de
instrumento que miente hacia un lado (aqui, hacia MAS envoltorio/menos cerrado) que esta unidad
tiene la obligacion de detectar antes de creerle. Confirmados por parseo de cuerpo, los **11
ABIERTO** son: `DEBT-002, DEBT-003, DEBT-004, DEBT-005, DEBT-W01, DEBT-W04, DEBT-W05, DEBT-W06,
DEBT-W10, DEBT-W12, DEBT-W15` — misma lista que la ronda anterior dejo escrita, sin cambios.

**Punto 2 del encargo (cerrar los 15, o los que tengan mecanismo)**: de los 15 que entraron a la
ronda anterior, 4 ya se cerraron con mecanismo corrido (`DEBT-W02`, `DEBT-W03`, `DEBT-W09`,
`DEBT-W11`, ver sus entradas mas abajo) y el premise de 2 mas se corrigio con medicion real sin
que eso habilite un cierre (`DEBT-002`, `DEBT-W10`, ver sus entradas). Para los 11 que siguen
ABIERTO no aparecio en esta ronda un mecanismo nuevo que no existiera ya documentado — cada uno
tiene su razon de bloqueo citada con evidencia (vault RBAC real para W12, coordinacion de 10 repos
consumidores para 002, decision explicita del user para 003, ausencia de infra de pago/Slack para
005/W05, backlog de esfuerzo real sin atajo para W01/W04/004/W15/W06). No se fuerza ningun cierre
sin mecanismo — cerrar sin haber corrido nada seria la misma clase de "existe pero no funciona"
que `DEBT-001` origino.

**Punto 3 del encargo — auditoria de `scripts/` por supresiones de error REALES (`|| true`,
exit codes ignorados, `set +e` defensivo), distinguiendo USO de MENCION**:

`scripts/` tiene exactamente 4 archivos fuente (fuera de `__pycache__`, confirmado con
`find scripts -type f`): `gen-api-collection.sh`, `gen_api_collection.py`,
`audit-fe-be-contracts.sh`, `fe_be_audit.py`. Comando de poblacion (excluye contenido de
comentarios ANTES de buscar el patron, para no contar una mencion en prosa como si fuera el
patron ejecutandose — el incidente que este mismo proyecto ya sufrio):

```bash
find scripts -type f \( -name '*.sh' -o -name '*.py' \) -not -path '*__pycache__*' -print0 |
while IFS= read -r -d '' f; do
  sed -E 's/(^|[[:space:]])#.*$//' "$f" \
    | grep -nE '\|\|[[:space:]]*true\b|\bset[[:space:]]+\+e\b|except[[:space:]]*[A-Za-z_.]*[[:space:]]*:[[:space:]]*pass\b'
done
```

```
(sin salida)
$ echo $?
1
```

**Poblacion = 0.** Tambien se revisaron a mano los 4 archivos por otras formas de supresion no
cubiertas por ese regex (`subprocess`/`os.system` con `check=False` o retorno descartado,
`$?` capturado y nunca comparado): `grep -nE 'subprocess\.|os\.system|check=False|returncode|\$\?'
scripts/*.py scripts/*.sh` → sin salida — ninguno de los 4 scripts invoca un subproceso ni
inspecciona un exit code ajeno, asi que no hay superficie para esa clase de supresion. Los dos
`except` reales que SI existen (`gen_api_collection.py:95` `except Exception as e: print(...)`,
per-archivo, continua el batch pero **imprime el warning a stderr, no lo traga**; y
`fe_be_audit.py:275` `except OSError: return []`, un archivo TS ilegible devuelve lista vacia sin
aviso) no son la forma `|| true`/`set +e`/`except: pass` que el encargo nombra, y ninguno de los
dos hace que un CHECK/GATE reporte exito falso — el segundo es la unica supresion silenciosa real
de los 4 archivos y queda anotado abajo como hallazgo menor, no como poblacion del patron pedido.

**Control de inyeccion, EN LAS DOS DIRECCIONES, con `Edit` (nunca `git`)** — para demostrar que el
detector de arriba SI sabe encontrar un `|| true` real y SI sabe ignorar una mencion dentro de un
comentario:

1. Baseline (arbol tal cual, sin tocar nada):
   ```
   $ bash /private/tmp/claude-501/-Users-ileonelperea-Documents-cowork-personal-alebrije/5a322fb4-3159-4520-a95f-268e09f73069/scratchpad/suppress-audit-workflowsronda2.sh
   POBLACION=0 (ninguna supresion de error USADA en scripts/, distinguido de mencion)
   EXIT=0
   ```
2. Inyectado con `Edit` en `scripts/gen-api-collection.sh`: se reemplazo el `if ! python3 ...;
   then log_error ...; exit 1; fi` real por `python3 ... || true` (una supresion de verdad, en
   linea ejecutable). Al MISMO TIEMPO, inyectado con `Edit` en
   `scripts/audit-fe-be-contracts.sh` un comentario puro: `# NOTA CONTROL M-RONDA2: nunca escribas
   || true aqui para tapar un fallo real.` (la cadena `|| true` aparece en el archivo, pero SOLO
   dentro de un comentario — la MISMA trampa que ya costo cara en este proyecto). Re-corrido el
   detector:
   ```
   $ bash /private/tmp/claude-501/-Users-ileonelperea-Documents-cowork-personal-alebrije/5a322fb4-3159-4520-a95f-268e09f73069/scratchpad/suppress-audit-workflowsronda2.sh
   scripts/gen-api-collection.sh:54:python3 "$SCRIPT_DIR/gen_api_collection.py" --repo "$API_REPO_PATH" --output "$OUTPUT_FILE" || true
   POBLACION>0 -- ver lineas arriba
   EXIT=1
   ```
   **RED** — y la unica linea acusada es la de `gen-api-collection.sh` (el USO real). La mencion
   dentro del comentario de `audit-fe-be-contracts.sh` **no aparece en la salida** — el detector
   la ignoro correctamente porque el `sed` le quito todo lo que sigue a `#` antes de buscar el
   patron. Esto es la prueba de USO-vs-MENCION que pide el encargo, no solo la prueba de que el
   detector puede encender una luz roja.
3. Restaurado con `Edit` (los dos archivos, al contenido exacto de antes de este control):
   ```
   $ bash /private/tmp/claude-501/-Users-ileonelperea-Documents-cowork-personal-alebrije/5a322fb4-3159-4520-a95f-268e09f73069/scratchpad/suppress-audit-workflowsronda2.sh
   POBLACION=0 (ninguna supresion de error USADA en scripts/, distinguido de mencion)
   EXIT=0
   $ git status --porcelain
   (vacio)
   $ git diff -- scripts/
   (vacio)
   $ bash -n scripts/gen-api-collection.sh; echo $?
   0
   $ bash -n scripts/audit-fe-be-contracts.sh; echo $?
   0
   ```
   **GREEN**, arbol identico a como estaba, sin residuo.

**Veredicto de la auditoria de `scripts/` (punto 3): poblacion real = 0 supresiones de error
`|| true`/`set +e`/`except: pass` USADAS en los 4 scripts existentes**, con el detector probado en
las dos direcciones sobre el arbol real de este repo (no un harness aislado) y con el caso de
MENCION-en-comentario probado explicitamente para no repetir el incidente ya documentado en este
proyecto. Hallazgo menor fuera del patron pedido: `fe_be_audit.py:275` (`except OSError: return
[]`) traga silenciosamente un fallo de lectura de archivo TS sin log — no afecta ningun gate
fatal (el peor efecto es sub-contar rutas frontend en el reporte, no un exito falso de CI) y no es
uno de los 15 tickets ni parte de la poblacion pedida por el encargo; se deja anotado aqui, sin
ticket nuevo, porque el efecto es cosmetico y el archivo ya tiene otra ruta de `except` (linea 95
del otro script) que SI loggea — asimetria menor, no bloqueante.

**Punto 4 del encargo — cifra exacta de lo que queda abierto**: **11 de 25** tickets con cadena
`DEBT` en este archivo siguen ABIERTO tras esta ronda y la anterior combinadas (13 CERRADO + 1
envoltorio + 11 ABIERTO = 25): `DEBT-002` (instrumento del propio censo ciego a Go/Elixir, backfill
de poblacion aun no medida), `DEBT-003` (decision explicita del user, deferred), `DEBT-004`
(bump-PR cross-fleet, sin bot), `DEBT-005` (ci-cost-aggregator necesita GH App token),
`DEBT-W01` (release-extended sin goreleaser/docker/cosign), `DEBT-W04` (cross-repo-trigger sin
apertura de PRs), `DEBT-W05` (ci-cost-aggregator sin Slack, mismo bloqueo que 005), `DEBT-W06`
(reusable-notify sin canal PagerDuty, falta Vault path), `DEBT-W10` (premisa "Python-only" ya
refutada con medicion real — Go/Elixir no tienen el failure-mode que el ticket asumia — pero se
mantiene la decision ya tomada de dejarlo ABIERTO como placeholder, no se fuerza un cierre nuevo
en esta ronda), `DEBT-W12` (fix de `outputToken` ya enviado, pero el login E2E real contra Vault
kubernetes-auth sigue sin ejecutarse porque requiere acceso root/admin que las guardrails de este
proyecto restringen a la terminal local del user), `DEBT-W15` (agregacion de run-ids en matrix,
mejora de observabilidad, no de correctitud).

---

## Continuacion 2026-08-22 — ronda 3 ("los 29 encabezados del repo que orquesta")

**PASO 0, con el comando literal que trae este encargo** (distinto del metodo de las rondas
anteriores — ver la reconciliacion abajo):

```
$ git rev-parse HEAD
beae6334cb0072ff6a96f9e23ec9d25a48f58416
$ grep -cE '^#{2,3} +(DEBT|GAP|AQ|Census|DEBT ITEMS)' TECHNICAL-DEBT.md
29
```

**29 confirmado**, sobre el arbol tal como lo dejo la ronda anterior (`beae633`, ya empujado —
ver el encargo, que cita ese mismo commit). **0 casillas** confirmado
(`grep -c '^\s*- \[[ x]\]' TECHNICAL-DEBT.md` → 0, sin cambio).

**Dos headers citados con `archivo:linea`, PASO 0 explicito del encargo — lineas re-derivadas por
contenido con `grep -n` DESPUES de escribir todo lo demas en esta ronda, no calculadas a mano,
justo para no caer en la propia trampa que este archivo ya documenta ("un `archivo:linea` migra
solo")**:
1. `grep -n "^### DEBT-W12" TECHNICAL-DEBT.md` → **linea 1239** —
   `### DEBT-W12: setup-vault-token — ... stays OPEN 2026-08-22`. Releido el cuerpo completo:
   sigue ABIERTO de verdad — el fix de `outputToken` esta commiteado, pero la propia entrada dice
   explicitamente "lo que no se ejecuta no se cierra" y el login Kubernetes-auth real contra
   Vault nunca corrio en esta sesion ni en las anteriores. El comando que la entrada ya cita
   (`kubectl exec -n vault vault-0 -- sh -c 'vault read auth/kubernetes/role/ci-runner-role'` →
   403) no se re-corrio para no repetir el mismo intento contra RBAC que las rondas previas ya
   agotaron, pero `git log -1 --format=%H -- .github/actions/setup-vault-token/action.yml` da el
   mismo commit que cerro el fix — el codigo no cambio desde que se midio, asi que el estado
   sigue siendo el medido.
2. `grep -n "^### DEBT-W17" TECHNICAL-DEBT.md` → **linea 1313** —
   `### DEBT-W17: reusable-property-tests.yml — ... FIXED 2026-05-31` (este ticket vivia en la
   linea 1131 con el ID `DEBT-W14` cuando el encargo se redacto; esa cifra y ese ID ya no
   aplican, ver el rename abajo). Este SI estaba mal, pero no en su status (CERRADO de verdad,
   mecanismo corrido y documentado con control en las dos direcciones) sino en su ID:
   **duplicado** con otra entrada que tambien se llamaba `DEBT-W14` (`cross-repo-trigger.yml`'s
   `::set-output`, ticket distinto). El censo del 2026-08-21 ya habia notado el duplicado en
   prosa ("dos veces con el mismo ID") pero nunca lo resolvio. Verificado antes de renombrar que
   ningun codigo fuera de este archivo referencia el de property-tests por ID
   (`grep -rn "DEBT-W14" --include='*.md' --include='*.yml' --include='*.py' --include='*.sh' .`
   fuera de `TECHNICAL-DEBT.md` solo pega en `tests/test_event_schemas.py`, y ambos hits son del
   OTRO ticket, el de `cross-repo-trigger.yml`) — renombrado a `DEBT-W17` en esta ronda, dejando
   el de `cross-repo-trigger.yml` con el ID `DEBT-W14` intacto para no romper esa referencia real.

**Reconciliacion 25 (metodo de las rondas 1-2) vs 29 (metodo de este encargo)**: no es drift, son
regex distintos apuntando al mismo arbol. El metodo anterior
(`grep -niE '^#.*debt' TECHNICAL-DEBT.md | tail -n +2`, 25) solo cuenta headers que contienen la
subcadena "debt" en cualquier parte del titulo (case-insensitive) — eso incluye los 24 tickets
`DEBT-*` reales mas el envoltorio de seccion `## §44 — DEBT-FN-ADR-79-...` (1), pero **excluye**
los 3 `AQ-00N` y los 2 `## Census — ...` porque ninguno de esos 5 titulos contiene la palabra
"debt". El metodo de este encargo (`^#{2,3} +(DEBT|GAP|AQ|Census|DEBT ITEMS)`, 29) exige que el
header EMPIECE con una de esas palabras — por eso SI cuenta los 3 `AQ` y los 2 `Census`, pero
**no** cuenta el envoltorio `## §44 — ...` (empieza con "§44", no con "DEBT"). Cuadra
exactamente: 24 tickets `DEBT-*` reales + 3 `AQ-*` + 2 `Census` = **29**; el otro metodo da
24 + 1 envoltorio = **25**. Ninguno de los dos numeros es el "verdadero" — miden universos
distintos (uno incluye preguntas de producto y secciones de censo, el otro incluye el envoltorio
de seccion); lo que hoy se usa es el 29 porque es el que trae el encargo.

**Separacion abiertos / cerrados / duplicados de los 29** (censo por CUERPO, no por titulo,
mismo metodo que las rondas 1-2):
- **2 no son tickets**: los dos headers `## Census — ...` son secciones de metodo, no items con
  `Status:` propio — se cuentan en el 29 pero no entran en el conteo ABIERTO/CERRADO.
- **24 tickets `DEBT-*`** — de estos, **13 CERRADO** (`DEBT-001`, `W02`, `W03`, `W07`, `W08`,
  `W09`, `W11`, `W13`, `W14`[cross-repo-trigger], `W17`[property-tests, ex-`W14` duplicado],
  `§43-SUPPLY-CHAIN-6`, `§43-SUPPLY-CHAIN-7`, `§44-CONTRACT-GAP-RECONCILE`) y **11 ABIERTO**
  (`DEBT-002`, `003`, `004`, `005`, `W01`, `W04`, `W05`, `W06`, `W10`, `W12`, `W15`) — identico a
  la cifra que dejaron las rondas 1-2, mas el ticket nuevo de esta ronda:
  **`DEBT-W16` se agrega y se CIERRA en la misma ronda** (ver su entrada completa mas abajo),
  asi que el tallo de tickets `DEBT-*` sube de 24 a 25 y el CERRADO de 13 a 14.
- **1 duplicado de ID resuelto**: las dos entradas `DEBT-W14` de las rondas anteriores eran dos
  tickets DISTINTOS con el MISMO ID — no un ticket contado dos veces por error de censo, sino un
  defecto real de numeracion en el propio tracker. Resuelto renombrando la del property-tests
  masking a `DEBT-W17` (mecanica y justificacion completas en esa entrada).
- **3 `AQ-*`**: `AQ-001` (NOT DECIDED — pregunta de producto, no ticket con mecanismo: sigue
  abierta, no se fuerza una decision de arquitectura que no me corresponde), `AQ-002` (FRAMEWORK
  EXISTS, no completamente validado para Python/Elixir/TS — sigue abierta, validar
  `reusable-release-extended.yml` en produccion para esos 3 lenguajes es trabajo de varias
  sesiones, no una remedicion de esta ronda), `AQ-003` (**CERRADA esta ronda** — ver su entrada).

**Tabla final de esta ronda**: PASO 0 midio **29** headers ANTES de tocar nada; esta ronda AGREGA
un ticket nuevo (`DEBT-W16`, ver mas abajo), asi que el arbol que se commitea queda en **30**
(verificado de nuevo tras escribir todo: `grep -cE '^#{2,3} +(DEBT|GAP|AQ|Census|DEBT ITEMS)'
TECHNICAL-DEBT.md` → 30). De esos 30: 2 son secciones-Census (no tickets), 25 son tickets
`DEBT-*` (14 CERRADO + 11 ABIERTO, tras sumar `DEBT-W16` y renombrar el duplicado sin cambiar su
status), y 3 son `AQ-*` (1 CERRADA esta ronda, 2 siguen como preguntas de producto sin decision).
2+25+3=30. **0 casillas** en todo el documento (`grep -cE '^\s*- \[[ x]\]' TECHNICAL-DEBT.md` →
0), sin cambio.

**Punto 2 del encargo — USO vs MENCION, demostrado para cada hallazgo nuevo de esta ronda**: los
dos detectores construidos hoy (el de `printf` con guion inicial sin protector, para `AQ-003`; y
el de `|| true`/`--no-verify`, para `DEBT-W16`) tuvieron el MISMO defecto al primer intento —
ninguno de los dos despojaba comentarios en la rama que revisa los bloques `run:` extraidos de
YAML — y el mismo control lo encontro las dos veces: una MENCION real (una nota de comentario
citando la cadena vigilada para explicar por que no debe escribirse) se contaba como USO hasta
que se corrigio. Ver el detalle completo, con las salidas ROJA y VERDE reales, en las entradas
`DEBT-W16` y `AQ-003` mas abajo.

**Punto 3 del encargo — cerrar por PEOR RAZON**: de los 3 hallazgos nuevos de esta ronda,
`DEBT-W16` (el self-audit del propio repo, ADR-001 Bloque R, ciego a `.github/actions` Y
ahogado en 129:1 ruido falso) se cerro primero — es la misma clase "parece proteger, no protege"
que `DEBT-001`/`DEBT-W07`/`DEBT-W02` de las rondas anteriores, y su radio es el peor de los tres
porque es el MECANISMO QUE AUDITA A LOS DEMAS. `AQ-003` se cerro segundo (documentacion +
verificacion de portabilidad, sin riesgo de esconder un fallo). El renombrado de `DEBT-W14`
duplicado se hizo ultimo porque es higiene de datos del tracker, no un mecanismo de CI — bajo
riesgo, pero real (cualquier herramienta que resuelva por ID, como el propio
`docs-avance.sh ver <ID>` de este proyecto, quedaria a merced de cual entrada matchea primero).

---

## DEBT-001 — CERRADO 2026-08-22 (regex ampliado a chi + test dirigido contra el repo real; el "REABIERTO 2026-08-21" de abajo era la ultima medicion falsa)

**Status**: **CLOSED 2026-08-22** (el `Status: CLOSED` de 2026-05-07 fue FALSO, luego REABIERTO
2026-08-21 con la evidencia de abajo; este cierre es el tercero y trae mecanismo corrido +
control en las dos direcciones, no solo lectura)
**Priority**: P2
**Impact real (medido, no el original)**: ambos ficheros existen (`scripts/gen-api-collection.sh`,
`scripts/gen_api_collection.py`) y el wrapper corre limpio, exit 0:

```
$ bash scripts/gen-api-collection.sh -r ../alebrije-api-gateway-go -o /tmp/api-collection-debt001.json
[INFO] API Repository: ../alebrije-api-gateway-go
[INFO] Output File: /tmp/api-collection-debt001.json
Generated API collection: /tmp/api-collection-debt001.json
Total endpoints: 0
[INFO] Successfully generated API collection: /tmp/api-collection-debt001.json
```

**El "Total endpoints: 0" no es limpio, es ciego.** `alebrije-api-gateway-go` es el gateway real de
la flota y expone decenas de rutas — el regex de `scripts/gen_api_collection.py:64`
(`r'(?:router|r)\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*"([^"]+)"\s*,\s*(\w+)\)'`) solo matchea
verbos en **MAYUSCULAS**. El gateway real usa `go-chi/chi` (`internal/handler/router.go:1-17`
importa `github.com/go-chi/chi/v5`), cuyo idioma es `r.Get(...)`/`r.Post(...)` — primera letra
mayúscula, resto minúscula. Verificado: `grep -rnE '\br\.(Get|Post|Put|Delete|Patch)\(' 
internal/handler/router.go` devuelve 7+ rutas reales (`r.Get("/api/v1/dashboard/hero", ...)`,
`r.Post("/artifacts/{id}/token", ...)`, etc.), y `grep -rlE '\.(Get|Post|Put|Delete|Patch)\(\s*"'
--include='*.go' .` cuenta **40 archivos** con ese patrón en todo el repo del gateway. El script
nunca podrá encontrarlas: su regex está escrito para un router estilo gin/mux en mayúsculas que
este gateway no usa desde que existe.
**Fix real pendiente**: agregar el patrón chi (`\.(Get|Post|Put|Delete|Patch)\(` case-sensitive tal
cual, sin forzar mayúsculas) a `gen_api_collection.py:64`, y agregar un caso de prueba que falle si
el conteo de endpoints es 0 contra un repo con rutas reales — ahora mismo nada distingue "no hay
rutas" de "la regex no las vio".
**Effort**: S — un segundo patrón de regex + un test dirigido.

### Cierre real 2026-08-22

**Fix aplicado**: `scripts/gen_api_collection.py:63-76` — el patrón ahora corre con `re.IGNORECASE`
(cubre `GET`/`Get` sin duplicar la alternancia) y el grupo del handler pasó de `(\w+)` a
`([\w.]+(?:\([^)]*\))?)` — el bloqueo real no era solo la mayúscula del verbo: los handlers reales
de chi son selectores con punto (`artifactsHandler.ProxyData`) o llamadas (`health.LiveHandler()`,
`startupHandler(cfg.WebhookEnabled, deps.db)`), ninguno de los cuales matchea `\w+`. Confirmado con
la mitad "case-only" del fix por separado: subía de 0 a solo 2 matches en `router.go`; el fix
completo (verbo + handler) sube a 7 en ese archivo y a **18 en todo el repo real**
(`../alebrije-api-gateway-go`, `APICollectionGenerator.generate()` recorre `rglob("*.go")`).

**Mecanismo corrido, comando exacto**:
```
$ bash scripts/gen-api-collection.sh -r ../alebrije-api-gateway-go -o /tmp/api-collection-debt001-after.json
[INFO] API Repository: ../alebrije-api-gateway-go
[INFO] Output File: /tmp/api-collection-debt001-after.json
Generated API collection: /tmp/api-collection-debt001-after.json
Total endpoints: 18
[INFO] Successfully generated API collection: /tmp/api-collection-debt001-after.json
```
(antes del fix, el mismo comando exacto daba `Total endpoints: 0`, exit 0 igual — el problema
nunca fue el exit code, fue el conteo silencioso.)

**Control en las dos direcciones** (Edit, no git): se revirtió `gen_api_collection.py` al regex
viejo exacto (`(?:router|r)\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*"([^"]+)"\s*,\s*(\w+)\)`, sin
`re.IGNORECASE`) y se corrió `python3 tests/test_gen_api_collection.py`:
```
FAIL test_chi_call_expression_handler_is_detected: call-expression handler (pkg.Func()) must be detected
FAIL test_chi_dotted_selector_handler_is_detected: chi handler as a dotted selector (artifactsHandler.ProxyData) must be detected
FAIL test_chi_titlecase_verb_with_bare_handler_is_detected: chi-style Title-case verb (r.Get) with a bare handler must be detected — this alone was already a gap in the pre-fix regex
PASS test_gin_mux_uppercase_style_still_detected_no_regression
FAIL test_real_gateway_repo_yields_nonzero_endpoints: Total endpoints: 0 against the REAL gateway is not clean, it's blind (DEBT-001) — the regex stopped matching this gateway's real router idiom again
PASS test_zero_endpoints_against_a_file_with_no_routes_is_still_zero

4 failure(s)
EXIT=1
```
Reproduce EXACTO el bug original (0 contra el gateway real). Se restauró el fix con Edit y se
corrió de nuevo:
```
PASS test_chi_call_expression_handler_is_detected
PASS test_chi_dotted_selector_handler_is_detected
PASS test_chi_titlecase_verb_with_bare_handler_is_detected
PASS test_gin_mux_uppercase_style_still_detected_no_regression
real gateway endpoint count: 18
PASS test_real_gateway_repo_yields_nonzero_endpoints
PASS test_zero_endpoints_against_a_file_with_no_routes_is_still_zero

0 failure(s)
EXIT=0
```
`git diff scripts/gen_api_collection.py` contra HEAD tras restaurar coincide con el fix que se
está commiteando (el árbol quedó en el estado que se commitea, no en un intermedio).

**Test nuevo**: `tests/test_gen_api_collection.py` — importa el módulo real (no lo reimplementa),
prueba las 4 formas reales de handler de chi (bare, dotted, call sin args, call con args), un caso
de no-regresión gin/mux UPPERCASE, un caso de cero-rutas-reales-sigue-siendo-cero (para que el fix
no sobre-matchee), y el caso contra el repo real con skip explícito (no un PASS falso) si el
checkout hermano no existe.

**Fuera de alcance de este cierre (nuevo hallazgo, no se toca)**: `api-collection-gen.yml` (el
workflow que invoca este script a diario via `cron` con `contents: write` + `git push`) hace
`actions/checkout` de **sí mismo** (no especifica `repository:`), y por default
`API_REPO_PATH=../api-gateway-go` — ese directorio JAMÁS existe en un checkout de un solo repo en
un runner de GitHub Actions. El job fallaría en el `if [[ ! -d "$API_REPO_PATH" ]]` de
`gen-api-collection.sh:46` antes incluso de llegar al regex, todos los días, sea cual sea el
regex. Esto es fail-closed (el job falla, no genera basura), así que no es "peor razón" que la
ceguera del regex — pero sí significa que el mecanismo diario **nunca ha podido producir nada
útil en CI real**, con o sin este fix, hasta que alguien decida cómo se espera que este workflow
obtenga el checkout del gateway (sparse-checkout cross-repo como hace `reusable-build-push.yml`,
o un input explícito de repo). No es parte del scope declarado de DEBT-001 (que es sobre el
regex) y cambiar el diseño de checkout del workflow requiere una decisión, no un parche de
pasada — se deja escrito aquí para que no se pierda.

---

---

## DEBT-002 — Event schema registry incomplete — PREMISE CORRECTED 2026-08-22, priority RAISED (not closed)

**Status**: OPEN — **the "~27" figure is unmeasurable with the current instrument, real number unknown**
**Priority**: was P3 — **raised, see below** — the instrument this ticket's number came from is
structurally blind to Go and Elixir, the two languages that publish the majority of this fleet's
events.

**Original claim**: ~27 event types published by the fleet lack registered schemas.

**What was actually measured 2026-08-22 (the real check, run for real, not assumed)**: extracted
the literal Python heredoc from `reusable-event-schema-check.yml`'s `check` job via
`yaml.safe_load` (not retyped) and ran it against all 19 real sibling repos in the cowork:
```
alebrije-mod-rewards-go:      scanned 1 publisher file(s), 0 candidate event type(s) referenced
alebrije-mod-crm-go:          scanned 2 publisher file(s), 0 candidate event type(s) referenced
alebrije-mod-campaigns-ex:    scanned 2 publisher file(s), 0 candidate event type(s) referenced
alebrije-svc-notifications-ex: scanned 1 publisher file(s), 0 candidate event type(s) referenced
```
**0 candidate event types found in every Go/Elixir repo sampled**, despite these being the
fleet's highest-volume real publishers (rewards-go alone emits at least 9 distinct types per its
own `events_publisher.go`). Aggregate across all 19 repos: only **2** missing-schema hits total
(`toronja.order.created`, `toronja.sync.completed`, both from `alebrije-adapt-toronja`, a Python
repo). **Neither 27 nor 2 is a trustworthy fleet-wide number** — 2 is real for the one repo whose
idiom the regex happens to match; for every Go/Elixir repo the check returns "OK" not because
schemas are complete but because **it cannot see the publishers at all**.

**Root cause, verified against real source (not guessed)**: `EVENT_TYPE_RE` in the check is
`r'"event_type"\s*:\s*"([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)"'` — it only matches
literal JSON/dict-style text: a quoted key `"event_type"`, a colon, a quoted string value. Real
Go and Elixir source does not write events that way:
```go
// alebrije-mod-rewards-go/internal/service/events_publisher.go:234 (the ONE file the check
// actually scans for this repo — matches the "events_publisher.*" glob):
e.EventType = "rewards.earned"          // struct-field assignment, no quotes around EventType
```
```go
// alebrije-mod-rewards-go/internal/service/outbox_event_publisher.go — the REAL outbox-pattern
// publisher (per this project's own "producer emits via outbox.Poller" architecture) — does NOT
// match ANY of the 9 PUBLISHER_GLOBS (none of them match "outbox_event_publisher.go"), so it is
// never even opened:
p.emit(ctx, tx, "rewards.earned", outboxIdemKey("rewards.earned", e), e, ...)   // positional arg
```
```elixir
# alebrije-mod-cadences-ex/lib/alebrije_cadences/reply_detection.ex:72 — DOES match the
# "events.ex"-adjacent naming loosely but the file itself isn't named events.ex/event_publisher.ex
# so it is ALSO never scanned; even if it were, the syntax wouldn't match:
event_type: "cadences.reply.received",   # Elixir keyword/map shorthand, key has no quotes at all
```
Two independent, compounding blind spots: (1) the 9 `PUBLISHER_GLOBS` filenames don't cover the
`outbox_*_publisher.go` naming this project's own outbox pattern actually uses, and files with
ad-hoc names like `reply_detection.ex` that happen to emit events; (2) even for files that ARE
scanned, the regex only recognizes JSON-literal-key syntax, which is not how Go struct fields or
Elixir keyword lists are written.

**Concrete, currently-real drift this blindness is hiding** (not hypothetical): `cadences.reply.received`
is emitted by real code (`alebrije-mod-cadences-ex/lib/alebrije_cadences/reply_detection.ex:72`)
and has **no registered schema** — `event-schemas/` only has `cadences.converted.v1.json` and
`cadences.enrolled.v1.json` for the cadences domain. `reusable-event-contract.yml` is wired into
this repo's `ci.yml` (per `DEBT-§44-CONTRACT-GAP-RECONCILE`, already CLOSED, which lists
cadences-ex among the 10 wired consumers) and has been reporting "OK" on every PR since this
event type was added, without ever having been able to see it.

**Why this is NOT fixed in this session**: `reusable-event-schema-check.yml` is `workflow_call`d
by ~10 consumer repos' real CI (`reusable-event-contract.yml`, `DEBT-§44-CONTRACT-GAP-RECONCILE`).
Loosening the regex to catch Go struct-assignment and Elixir keyword syntax can only turn
existing silent "OK"s into new FAILURES for whatever real drift has already accumulated in those
10 repos while the gate was blind — exactly the population DEBT-002 itself says needs backfilling
first. Shipping a stricter detector in the same session as discovering it, without coordinating
the backfill in each of the 10 affected repos, would turn every one of their next PRs red for
pre-existing drift nobody has triaged yet. This is squarely the class of change the domain
guardrail for this repo warns about ("un gate que se afloje/cambie aqui se afloja/cambia en los
20 repos que lo llaman") — here inverted (tightening, not loosening) but the same blast-radius
argument applies to an uncoordinated rollout.
**Spec for the fix, left for a dedicated session** (do NOT do this inline with unrelated changes):
(1) widen `PUBLISHER_GLOBS` to include `outbox_*publisher*.go`/`.ex` and any file containing a
call matched by a new regex, not just specific filenames; (2) add a Go-idiom pattern
(`EventType\s*=\s*"(...)"`  struct-field assignment) and an Elixir-idiom pattern
(`event_type:\s*"(...)"` keyword/map shorthand, no quotes around the key) alongside the existing
JSON-literal pattern; (3) before flipping `fail-on-missing` semantics fleet-wide, run the fixed
check in **report-only** mode (`fail-on-missing: false`, already a supported input) against all
10 wired repos first and triage the real backfill list it surfaces — THEN raise the gate.
**Fix (original, still valid)**: once the detector can see them, add schemas for all missing
event types — this remains real backfill work, now against an unmeasured population, not ~27.

---

## DEBT-003 — Bloque Q (Self-hosted runners) deferred

**Status**: DEFERRED — out of scope until fleet volume justifies infra ops
**Priority**: P4
**Impact**: Using GH-hosted runners (more expensive at scale)
**Trigger to revisit**: Fleet CI exceeds 5,000 min/month

---

## DEBT-004 — No automated cross-fleet version bump PRs

**Status**: OPEN
**Priority**: P3
**Impact**: When common-go/common-ex/common-python release, consumer repos don't get automatic update PRs with `go get -u`, `mix deps.update`, etc.
**Fix**: Implement worker in cross-repo-trigger.yml that opens PRs with updated dependencies

---

## DEBT-005 — ci-cost-aggregator requires GH App token

**Status**: OPEN
**Priority**: P3
**Impact**: Weekly CI cost report (ci-cost-aggregator.yml) needs a GH App token with Actions read permission across all repos
**Fix**: Create GH App in GitHub + configure secret in alebrije-infra

---

## AQ-001 — Event schema auto-publish to registry not implemented

**Question**: Should event schemas auto-publish to Confluent Schema Registry or a custom registry?
**Status**: NOT DECIDED
**Context**: reusable-event-schema-check.yml has breaking change detection but no auto-publish step

---

## AQ-002 — Multi-language release workflow not battle-tested in production

**Question**: Has reusable-release-extended.yml been validated in production for all language targets?
**Status**: FRAMEWORK EXISTS — not fully validated for Python/Elixir/TS (Go only proven)
**Risk**: May have untested edge cases for non-Go languages in semver bumping, changelog parsing, or publish targets

---

## AQ-003 — Custom actions completeness verification — CLOSED 2026-08-22

**Question**: Are all 9 custom actions (.github/actions/*) fully implemented and documented?
**Status**: **CLOSED** — the three specifically-named blockers are gone (measured, not assumed),
and the broader "documented" half of the question — not scoped to any of the three, and not
previously measured — turned out to be the real gap: **0 of the 9 actions were named anywhere
in README.md** before this session.

**Original 3 named blockers, re-verified against today's tree**:
1. `bump-version/bump.sh` — **no longer exists**. `ls .github/actions/bump-version/` → only
   `action.yml`; both `bump.sh` and `parse-semver.sh` were `git rm`'d closing `DEBT-W08` earlier
   this session (0 callers verified before removal). Nothing left to review.
2. `wait-for-metrics/check-metrics.sh` — reviewed: `bash -n` exit 0; re-ran the exact printf
   leading-dash-portability detector that found the real macOS `/bin/bash` bug in
   `generate-postmortem` (`DEBT-W03`) against this file specifically — 0 hits (no unguarded
   `printf "-...`). Its `_float_compare()` bc/awk fallback (line 62-69) is the fix already shipped
   2026-05-07 per this file's own "Fixed in session 2026-05-07" list ("wait-for-metrics: script
   consolidated to bundled check-metrics.sh, bc fallback") — unchanged, still present.
3. `generate-postmortem` template completeness — **CLOSED** by `DEBT-W03` earlier this session
   (4 new fields + the same printf-portability bug class fixed there).

**Real gap found (not one of the 3 named, sharper than any of them)**: README.md documents
reusable workflows (`## Reusable Workflows`), language examples (`DEBT-W09`), the security scan
workflow, `scripts/`, and policies — but had **no section at all** for `.github/actions/*`
(`grep -n "bump-version\|check-tenant-id-leak\|generate-postmortem\|post-benchmark-comment\|
post-coverage-comment\|setup-vault-token\|sign-with-cosign\|trigger-canary\|wait-for-metrics"
README.md` → 0 hits, verified before writing anything).

**Fix**: new `## Custom Actions (AQ-003)` section in README.md — a table naming all 9 actions with
their real `inputs:`/`outputs:`, each re-derived via `yaml.safe_load` against the committed
`action.yml` (Regla 12 — not retyped from memory or guessed), same pattern as `DEBT-W09`'s
per-language examples (cited: `tests/test_readme_examples.py`'s `_real_inputs()` helper, same
ground-truth-from-YAML idiom reused here for actions instead of workflows). Also ran the printf
leading-dash detector (built and proven both-directions for `DEBT-W16`/`AQ-003`, see below)
against **all 9** actions' inline `run:` blocks and standalone `.sh` files, not just the 3 named
ones — 0 remaining hits.
**Mechanism, new test `test_all_nine_custom_actions_documented_in_readme` in
`tests/test_readme_examples.py`** (appended, same file DEBT-W09 created, same stand-alone-runner
pattern): asserts the action-directory count is 9 (fails loud if it silently drifts), that every
action directory name appears in the README table, and that at least one of each action's REAL
input keys (from `yaml.safe_load`, not the table's prose) is named — so it goes red if a new
action ships undocumented or an existing one's real inputs drift from the table.
**Mechanism run + control in both directions**:
```
$ python3 tests/test_readme_examples.py
PASS test_all_nine_custom_actions_documented_in_readme
PASS test_elixir_example_names_real_reusable_test_elixir_inputs
PASS test_go_example_names_real_reusable_test_go_inputs
PASS test_ts_example_does_not_claim_a_secrets_block_that_does_not_exist
PASS test_ts_example_names_real_reusable_test_ts_inputs
0 failure(s)
```
Removed (with Edit) the `trigger-canary` row from the README table, re-ran:
```
FAIL test_all_nine_custom_actions_documented_in_readme: AQ-003 gap(s) found:
trigger-canary: name missing from README table
1 failure(s)
```
Restored the row with Edit (alphabetical position, matching the other 8), re-ran → back to
`0 failure(s)`, all 5 PASS. `git diff --stat README.md` shows a clean 17-line net addition (the
whole section), no residual hole from the break/restore cycle.
**Printf-portability detector, built for this ticket, proven both directions (Regla — no texto
plano donde se pueda estructural)**: scans (a) every standalone `.sh` under `.github/actions/`
and `scripts/` with shell comments stripped first (`sed -E 's/(^|[[:space:]])#.*$//'`), and (b)
every `action.yml`'s real `run:` blocks extracted via `yaml.safe_load` (also comment-stripped
per-line before matching — first version of this detector did NOT strip comments in branch (b)
and wrongly flagged a comment in `sign-with-cosign/action.yml` that only *mentioned* the bug
class; fixed before trusting the 0-hits result, see `DEBT-W16` for the identical defect found
in the OTHER detector built this session). Injected via `Edit` a real unguarded
`printf "- ...` into `wait-for-metrics/check-metrics.sh` (USE) and, simultaneously, a
comment-only mention of the same string into a `run:` block of `sign-with-cosign/action.yml`
(MENTION) — detector caught only the real USE, ignored the MENTION; restored both with Edit,
re-ran, back to 0 hits; `git status --porcelain` empty on both files afterward.
**Risk retired**: the two concrete, verifiable risks the ticket named (`bump-version/bump.sh`,
`generate-postmortem`) are gone; the general "shell script portability" risk was checked with a
real, both-directions-tested detector across all 9 actions, not sampled. Residual, out of this
ticket's scope: `setup-vault-token`'s Kubernetes-auth E2E remains unexecuted (tracked under its
own ticket, `DEBT-W12`) — AQ-003 does not re-open that, it is already open under its own ID.

---

## Workflows Audit — 2026-05-07

A comprehensive audit of all 28 workflows, 9 custom actions, and meta-files was conducted. P1 items fixed in this session are listed below. Remaining items require future work.

### Fixed in session 2026-05-07
- approved-base-images.json: schema key mismatch (base_images→images)
- reusable-notify.yml: deprecated ::set-output replaced with $GITHUB_OUTPUT
- reusable-security-scan.yml: gitleaks step added, OSV exit code configurable
- reusable-benchmark.yml: Python exit code propagation from heredoc fixed
- reusable-openapi-check.yml: [allow-breaking-change] override implemented
- reusable-event-schema-check.yml: JSON parse errors exit 1 (not breaking change), regex narrowed
- validate-self.yml: actionlint job, timeout audit, inputs injection checks added
- reusable-test-go.yml + reusable-test-elixir.yml: inputs.* injection via run blocks fixed
- reusable-mutation-test.yml: Elixir muzak || true removed, hard fail
- reusable-property-tests.yml: artifact uploads added for all 4 languages
- reusable-test-go-matrix.yml: Go 1.25 added
- reusable-test-elixir-matrix.yml: Elixir 1.17+OTP26 added
- ci-cost-aggregator.yml: pagination added, hardcoded git author removed
- cross-repo-trigger.yml: concurrency added, JSON injection fixed
- CODEOWNERS: typo @ileonelperia→@ileonelperea fixed, missing entries added
- README.md: 18 undocumented workflows added to table
- node-version.json: ci_matrix added
- PULL_REQUEST_TEMPLATE.md: documentation checkbox added
- reusable-canary-deploy.yml: sed pipe vulnerability fixed
- bump-version/bump.sh: set -euo pipefail, portable sed
- check-tenant-id-leak: comprehensive UUID regex, case-insensitive matching
- wait-for-metrics: script consolidated to bundled check-metrics.sh, bc fallback
- post-coverage-comment: istanbul-json parsing expanded to branches/functions/statements
- event-schemas: control-medico→control_medico naming fixed (P1)
- event-schemas: auth-enhanced/payments-enhanced/rewards-enhanced hyphen→underscore

### DEBT-W01: reusable-release-extended.yml — No goreleaser/docker/cosign jobs
- **What**: Release workflow missing artifact publishing, Docker image build+push, cosign signing
- **Effort**: L
- **Status**: OPEN

### DEBT-W02: trigger-canary action — Flagger CRD structure was WRONG, live path was a silent no-op — CLOSED 2026-08-22

- **What (was broken, worse than suspected)**: fetched the real upstream Flagger CRD
  (`https://raw.githubusercontent.com/fluxcd/flagger/main/artifacts/flagger/crd.yaml`,
  `canaries.flagger.app` v1beta1) and parsed its OpenAPI v3 schema. Real `spec` properties:
  `analysis, autoscalerRef, ingressRef, metricsServer, progressDeadlineSeconds, provider,
  revertOnDeletion, routeRef, service, skipAnalysis, suspend, targetRef, upstreamRef` — **no
  `canaryMetrics`**. Real `spec.analysis` properties: `alerts, canaryReadyThreshold, interval,
  iterations, match, maxWeight, metrics, mirror, mirrorWeight, primaryReadyThreshold,
  sessionAffinity, stepWeight, stepWeightPromotion, stepWeights, threshold, webhooks` — **no
  `canary` sub-object**. Both `apply-weight.sh --method istio` (`spec.analysis.canary.maxWeight`)
  and `trigger-canary/action.yml`'s inline istio branch (`spec.canaryMetrics`) patched fields
  that do not exist on the real CRD.
  `apply-weight.sh` is **not** dead code — `reusable-canary-deploy.yml:305,312` calls it for
  every weight-promotion step in the loop when `use-istio-flagger: true`, i.e. this is a LIVE
  production path.
- **Why this is worse than "may be incorrect"**: `apiextensions.k8s.io/v1` CRDs are structural
  schemas, so the Kubernetes API server silently **PRUNES unknown fields** on a merge patch
  instead of rejecting them. Proved live, not inferred: applied the real fetched CRD to the
  local docker-desktop cluster, created a real `Canary` CR, and ran the exact broken payload:
  ```
  $ kubectl patch canary probe-svc -n w2-flagger-probe --type merge -p '{"spec":{"analysis":{"canary":{"maxWeight":50}}}}'
  Warning: unknown field "spec.analysis.canary"
  canary.flagger.app/probe-svc patched (no change)
  $ kubectl get canary probe-svc -n w2-flagger-probe -o jsonpath='{.spec.analysis.maxWeight}'
  10   # unchanged — the intended weight (50) was silently dropped, exit 0
  ```
  `apply-weight.sh`'s own `2>/dev/null` even suppressed the one visible hint (the `unknown
  field` warning) — the old `|| { exit 1; }` never fires because pruning is not a kubectl error.
  This is the **exact DEBT-001 failure class** (exit 0, looks like success, silently does
  nothing) but on a currently-live deploy path, not an unused script.
- **Second, independent bug found in the same file**: `trigger-canary/action.yml`'s inline
  `manual` branch had `kubectl patch deployment/${SERVICE}-canary ... 2>/dev/null || true`,
  then **unconditionally** printed `::notice::...applied` and `exit 0` regardless of whether the
  patch succeeded — a textbook fail-open silent-success (Inquebrantable 11). `apply-weight.sh`'s
  own manual branch does NOT have this bug (it already used the `|| { warning; exit 1; }` guard
  correctly) — only the composite action's inline copy did.
- **Fix**: `apply-weight.sh` istio patch → `{"spec":{"analysis":{"maxWeight":${WEIGHT}}}}` (no
  `.canary` nesting), `2>/dev/null` removed so future schema-prune warnings are visible instead
  of hidden. `trigger-canary/action.yml`: `canaryMetrics` folded into `spec.analysis.metrics`
  (alongside the existing `request-success-rate` entry); manual branch's `|| true` replaced with
  a real `if kubectl patch ...; then ...; fi` guard matching the istio branch's shape (no false
  success on a real failure).
- **Mechanism run + control in both directions (real Flagger CRD, real docker-desktop cluster,
  not simulated)**:
  ```
  # BEFORE fix (bug reproduced against a real Canary CR, maxWeight=10):
  $ kubectl patch canary probe-svc -n w2-flagger-probe --type merge -p '{"spec":{"analysis":{"canary":{"maxWeight":50}}}}'
  Warning: unknown field "spec.analysis.canary"
  canary.flagger.app/probe-svc patched (no change)     # exit 0
  $ kubectl get canary probe-svc -n w2-flagger-probe -o jsonpath='{.spec.analysis.maxWeight}'
  10                                                     # unchanged — RED

  # AFTER fix, run via the REAL apply-weight.sh (not a re-implementation):
  $ bash .github/actions/trigger-canary/apply-weight.sh --service probe-svc --namespace w2-flagger-probe --weight 77 --method istio
  canary.flagger.app/probe-svc patched
  ✓ Applied 77% weight to probe-svc
  $ kubectl get canary probe-svc -n w2-flagger-probe -o jsonpath='{.spec.analysis.maxWeight}'
  77                                                     # GREEN — real change

  # Control: reverted apply-weight.sh to the OLD payload with Edit (not git), re-ran:
  $ bash .github/actions/trigger-canary/apply-weight.sh --service probe-svc --namespace w2-flagger-probe --weight 30 --method istio
  canary.flagger.app/probe-svc patched (no change)
  ✓ Applied 30% weight to probe-svc                     # LIES — exit 0, prints success
  $ kubectl get canary probe-svc -n w2-flagger-probe -o jsonpath='{.spec.analysis.maxWeight}'
  77                                                     # RED — still 77, not 30, silent no-op reproduced

  # Restored fix with Edit, re-ran:
  $ bash .github/actions/trigger-canary/apply-weight.sh --service probe-svc --namespace w2-flagger-probe --weight 30 --method istio
  canary.flagger.app/probe-svc patched
  ✓ Applied 30% weight to probe-svc
  $ kubectl get canary probe-svc -n w2-flagger-probe -o jsonpath='{.spec.analysis.maxWeight}'
  30                                                     # GREEN restored
  ```
  Also verified `trigger-canary/action.yml`'s fixed inline istio branch directly (YAML-extracted
  literal `run:` block via `yaml.safe_load`, GH Actions `${{ }}` expressions substituted with
  literal test values, executed against the same live Canary CR): `maxWeight` moved 30→61 and
  `spec.analysis.metrics[*].name` came back `request-success-rate error-rate latency` (all 3, the
  `canaryMetrics` fold-in confirmed working). Manual-branch fix verified by running the exact
  guarded `if kubectl patch deployment/${SERVICE}-canary ...; then ... fi` structure against a
  real nonexistent deployment (`nonexistent-svc-xyz-canary`, confirmed absent via `kubectl get`)
  — the real "NotFound" error correctly skips the false-success notice/outputs, falling through
  to the retry/fail path instead of the old unconditional `exit 0`.
  Cleanup: `kubectl delete canary probe-svc -n w2-flagger-probe` and
  `kubectl delete crd canaries.flagger.app` both run (confirmed gone). The empty test namespace
  `w2-flagger-probe` could not be deleted — `.claude/hooks/M212-destructive.sh` blocks
  `kubectl delete namespace` with no kill switch by design; left for the user to remove manually
  if desired, it holds no resources.
- **git diff scope**: `.github/actions/trigger-canary/apply-weight.sh`,
  `.github/actions/trigger-canary/action.yml` only. `reusable-canary-deploy.yml` (the caller) was
  not touched — its call signature to `apply-weight.sh` is unchanged.
- **Effort**: M (turned out S once the real CRD schema was in hand) — **Priority**: P1 (was P2 by
  cost-based ranking; **re-ranked #1 by PEOR RAZON** ahead of DEBT-W12 — this is a currently-live
  deploy mechanism silently doing nothing, not an unused output) — **Status**: **CLOSED**

### DEBT-W03: generate-postmortem action — template incomplete — CLOSED 2026-08-22

- **What (was missing)**: template had no incident commander, related services, deployment
  context, or escalation path fields — exactly the 4 gaps the ticket named.
- **Fix**: 4 new composite-action inputs (`incident-commander`, `related-services`,
  `deployment-context`, `escalation-path`, all optional with `TBD`/empty defaults so existing
  callers keep working unchanged) surfaced into: the header metadata line (Incident Commander),
  a new `## Deployment Context` section (between Root Cause and Impact), the `## Impact` section
  (Related services, conditionally rendered), and a new `## Escalation Path` section (between
  Detection/Alerting and Lessons Learned).
- **Second defect found by actually RUNNING the mechanism (not in the original ticket scope, but
  the same failure class this session is hunting)**: the script has 15 `printf` calls whose
  format string starts with a bare `-` bullet (e.g. `printf "- **Duration**: ...`). GNU bash 5.x
  (GitHub Actions `ubuntu-latest` runners, and this machine's Homebrew `bash`) tolerates this, but
  macOS's stock `/bin/bash` (3.2) does not — it parses the leading `-` as an option flag:
  ```
  $ /bin/bash -c 'printf "- **Duration**: test\n"'
  /bin/bash: line 0: printf: - : invalid option
  printf: usage: printf [-v var] format [arguments]
  ```
  The generated postmortem silently drops that bullet line (the enclosing `{ ... } > "$OUT"`
  block has no `set -e`, so the script still exits 0 and prints "Generated..."). Guarded all 15
  with `printf -- "..."` (matches the pattern already used correctly on every `printf -- "---"`
  separator line elsewhere in the same file). Zero behavior change under GNU bash (already
  worked); fixes the same class of macOS-bash portability bug already documented for `M38`
  (Docker daemon health check) in this project's CLAUDE.md.
- **Mechanism run + control in both directions**: extracted the real `run:` block via
  `yaml.safe_load` (not retyped), substituted GH Actions `${{ }}` expressions with literal test
  values, executed under `/bin/bash` (the strict interpreter that reproduces the bug):
  ```
  # BEFORE (unguarded, macOS /bin/bash) — RED:
  /bin/bash: line 43: printf: - : invalid option
  printf: usage: printf [-v var] format [arguments]
  Generated postmortem template: postmortem-888888.md   # still "succeeds", bullet silently missing

  # AFTER (guarded with `--`) — GREEN:
  Generated postmortem template: postmortem-999999.md   # no errors
  $ grep -c "Duration" postmortem-999999.md
  1
  ```
  Reverted one guard (`- **Duration**` line) with Edit, re-ran under `/bin/bash`, reproduced the
  exact RED error above; restored with Edit, re-ran, GREEN again with no errors. Also confirmed
  the 4 new sections render with real substituted values end-to-end (Incident Commander, Related
  services also impacted, Deployment Context body, Escalation Path body all present in the
  generated file).
  `python3 -c "import yaml; yaml.safe_load(open('.github/actions/generate-postmortem/action.yml'))"`
  → OK throughout.
- **git diff scope**: `.github/actions/generate-postmortem/action.yml` only.
- **Effort**: S — **Status**: **CLOSED**

### DEBT-W04: cross-repo-trigger.yml — PR creation not implemented
- **What**: Does not open PRs in consumer repos with updated workflow version pins
- **Effort**: M
- **Status**: OPEN

### DEBT-W05: ci-cost-aggregator.yml — No Slack reporting or growth alerts
- **Effort**: S — Status: OPEN

### DEBT-W06: reusable-notify.yml — PagerDuty not implemented
- **Vault path needed**: alebrije/data/pagerduty/routing-key
- **Effort**: S — Status: OPEN

### DEBT-W07: validate-self.yml — No approved-base-images.json schema validation job — CLOSED 2026-08-22
- **What (was broken)**: AUDIT 11 (`check-event-schemas-valid`) in `validate-self.yml` globs
  `event-schemas/*.json` only. `approved-base-images.json` — the whitelist that gates Docker
  builds for the whole fleet inline in `reusable-build-push.yml` (DEBT-§43-SUPPLY-CHAIN-6/7) —
  had ZERO structural validation of its own in this repo's CI. A malformed or semantically-broken
  edit could merge to `main` untouched by any check here, then break every one of the ~33
  fleet consumers' builds simultaneously the next time each one built.
- **Fix**: new job `check-approved-images-schema` (AUDIT 18) in `validate-self.yml`, wired into
  `security-audit-summary.needs:` and into the final `Fail if any audit failed` condition (so a
  schema violation actually fails the workflow, not just the advisory summary table). Validates:
  `images` is a non-empty array; each entry has a non-empty `name`; each entry declares
  `approved_tags` (non-empty array of non-empty strings) or `tag` (non-empty string); and
  `scanning_policy.block_on_critical` is present.
- **Mechanism run, exact literal script (extracted from the committed YAML via
  `yaml.safe_load`, not retyped, so there is zero drift risk between what was tested and what CI
  runs)**:
  ```
  $ python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/validate-self.yml')); \
      print(d['jobs']['check-approved-images-schema']['steps'][-1]['run'])" > /tmp/extracted.py
  $ python3 /tmp/extracted.py
  PASS: approved-base-images.json structurally valid (11 image entries)
  ```
- **Control in two directions (Edit on the real `approved-base-images.json`, not git)**: emptied
  the `golang` entry's `approved_tags` to `[]` —
  ```
  $ python3 /tmp/extracted.py
  ::error::images[2] (golang): 'approved_tags' must be a non-empty array
  ```
  exit 1 — RED, names the exact broken entry. Restored the file to its original content with
  Edit —
  ```
  $ python3 /tmp/extracted.py
  PASS: approved-base-images.json structurally valid (11 image entries)
  ```
  exit 0 — GREEN. `git diff approved-base-images.json` against HEAD shows no residual diff (the
  break/restore cycle left the file byte-identical to before).
- **YAML re-validated**: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/validate-self.yml'))"`
  → OK; `yamllint -d "{extends: default, rules: {line-length: {max: 180}, comments: {min-spaces-from-content: 2}}}" .github/workflows/validate-self.yml`
  → only the two pre-existing `document-start`/`truthy` warnings shared by every workflow in this
  repo, no new warnings, no errors; no tabs.
- **Tests**: appended to `tests/test_approved_base_images.py` (same file, same pattern as the
  DEBT-§43 tests already there) — `_validate_schema()` re-implements the exact algorithm,
  `test_schema_validator_extracted_from_workflow_matches_reimplementation` guards against the
  re-implementation drifting from the real YAML text, plus 5 targeted cases (missing `images`,
  entry without `name`, entry without tags, emptied `approved_tags` — the exact live-control
  mutation — and missing `scanning_policy`). `python3 tests/test_approved_base_images.py` → all
  new tests PASS (one PRE-EXISTING unrelated failure in this same file, `test_catalog_covers_...`,
  predates this session — see "Hallazgo colateral" at the end of this document; not touched here).
- **Effort**: XS — **Priority**: P2 — **Status**: **CLOSED**

### DEBT-W08: Dead shell scripts in custom actions — ALCANCE CORREGIDO 2026-08-21 (era 3 de 3, son 2 de 3)
- **What (original, 2 de 3 partes correctas)**: `bump-version/bump.sh` + `parse-semver.sh` siguen
  muertos, y hoy están MÁS muertos que cuando se escribió el item: `.github/actions/bump-version/action.yml`
  ya no invoca `bump.sh` en absoluto — el step `Parse commits and bump version` hace el cálculo de
  semver **inline en Python** dentro del propio `action.yml` (`run: | python3 << 'PY' ... PY`).
  `grep -rn "bump-version/bump\.sh" . --include='*.yml' --include='*.sh'` → 0 resultados en todo el
  repo. Y `bump.sh` a su vez hace `source "$SCRIPT_DIR/parse-semver.sh"` (`bump.sh:26`) — así que
  `parse-semver.sh` solo se ejecutaría SI algo llamara a `bump.sh`, y nada lo hace.
- **What (corrección, 1 de 3 era falso)**: `trigger-canary/apply-weight.sh` **NO está muerto** —
  `grep -n "apply-weight.sh" .github/workflows/reusable-canary-deploy.yml` → 2 sitios de llamada
  reales (líneas 305 y 312, dentro del job `Wait & Monitor Canary`). El item original lo incluía en
  la lista de "unused" sin haberlo comprobado; es el mismo defecto que el brief advierte con
  DEBT-001 pero en dirección contraria (aquí sobra alcance, en DEBT-001 faltaba).
- **Fix pendiente**: `git rm .github/actions/bump-version/bump.sh .github/actions/bump-version/parse-semver.sh`
  (o, si se prefiere conservar el cálculo fuera del YAML por legibilidad, invertir el orden: hacer
  que `action.yml` vuelva a llamar a `bump.sh` en vez de duplicar la lógica inline — pero eso es un
  cambio de diseño, no limpieza). No tocar `apply-weight.sh`.
- **Effort**: XS (son 2 `rm` + una línea de README si `Scripts` los llegó a listar — no los lista,
  verificado)

### Cierre real 2026-08-22

**Re-verificado sobre el árbol de hoy antes de tocar nada** (no confiar en el hallazgo de ayer sin
remedir): `grep -rn "bump-version/bump\.sh\|bump\.sh" . --include='*.yml' --include='*.sh'
--include='*.md'` → 0 llamadas reales (solo el propio `bump.sh` citándose en su docstring y las
entradas de este archivo). `grep -rn "parse-semver"` → mismo resultado, solo `bump.sh:26` lo
`source`ea, y nada llama a `bump.sh`. `action.yml` no menciona ninguno de los dos ficheros.
README.md / README.orphan no los listan.

**Mecanismo (no hay "correr" un script muerto — el control aquí es de AUSENCIA, no de
comportamiento)**:
```
$ ls .github/actions/bump-version/*.sh
.github/actions/bump-version/bump.sh
.github/actions/bump-version/parse-semver.sh
$ python3 -c "import yaml; d=yaml.safe_load(open('.github/actions/bump-version/action.yml')); print('action.yml valid, steps:', len(d['runs']['steps']))"
action.yml valid, steps: 1
$ git rm .github/actions/bump-version/bump.sh .github/actions/bump-version/parse-semver.sh
rm '.github/actions/bump-version/bump.sh'
rm '.github/actions/bump-version/parse-semver.sh'
$ python3 -c "import yaml; d=yaml.safe_load(open('.github/actions/bump-version/action.yml')); print('action.yml valid, steps:', len(d['runs']['steps']))"
action.yml valid, steps: 1
$ grep -rn "bump-version/bump\.sh\|bump-version/parse-semver\.sh" .github/ 2>/dev/null
(sin salida — exit 1, cero referencias colgantes)
```
**Control en las dos direcciones para este caso concreto** (no hay comportamiento que romper con
Edit porque el archivo no ejecuta nada — la prueba de "peor caso" aquí es la ausencia de caller
ANTES de borrar y la ausencia de referencia colgante DESPUÉS): confirmado antes (0 callers →
borrar es seguro) y confirmado después (0 referencias → borrar no rompió nada). `apply-weight.sh`
no se tocó (verificado que sigue llamado 2 veces en `reusable-canary-deploy.yml`).
**Effort**: XS — **Status**: **CLOSED**

### DEBT-W09: README.md — No usage examples for Go, Elixir, TypeScript — CLOSED 2026-08-22
- **Fix**: 3 new `### <Language> service (DEBT-W09)` sections added to README.md after the
  existing generic Python example, each grounded in the REAL `on.workflow_call.inputs` of the
  corresponding reusable workflow (`reusable-test-go.yml`, `reusable-test-elixir.yml`,
  `reusable-test-ts.yml`, read via `yaml.safe_load` before writing, not guessed — Regla 12/13),
  plus pointers to the matrix variants (`reusable-test-go-matrix.yml`,
  `reusable-test-elixir-matrix.yml`) and to `reusable-test-node.yml` for plain-Node services.
  Deliberately did NOT invent a `secrets:` block for the TS example — `reusable-test-ts.yml` (and
  `-node.yml`) declare no `secrets:` under `workflow_call`, unlike Go/Elixir which require
  `GH_TOKEN`; documenting a contract that doesn't exist would be the DEBT-001 failure class
  applied to prose instead of code.
- **Mechanism**: new `tests/test_readme_examples.py` (pattern copied from
  `tests/test_approved_base_images.py`'s `REPO_ROOT` constant + stand-alone-runner tail —
  cited: `REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` and the
  `if __name__ == "__main__": ... sys.exit(1 if failures else 0)` block, same shape here).
  For each language it re-derives the workflow's real `workflow_call.inputs` via
  `yaml.safe_load` (ground truth) and asserts the README's example section for that language
  actually names ≥3 of those real input keys and points at the matrix/plain-Node variant — so
  the check goes red if a workflow's inputs drift without the README being updated, not just if
  the word "Go" disappears. A dedicated test additionally asserts the TS section does NOT claim a
  `secrets:` requirement that the real workflow doesn't have.
- **Mechanism run + control in both directions**:
  ```
  $ python3 tests/test_readme_examples.py
  PASS test_elixir_example_names_real_reusable_test_elixir_inputs
  PASS test_go_example_names_real_reusable_test_go_inputs
  PASS test_ts_example_does_not_claim_a_secrets_block_that_does_not_exist
  PASS test_ts_example_names_real_reusable_test_ts_inputs
  0 failure(s)
  ```
  Removed (with Edit) the Go section's pointer to `reusable-test-go-matrix.yml`, re-ran:
  ```
  FAIL test_go_example_names_real_reusable_test_go_inputs: Go section must point to the matrix variant for multi-version testing
  1 failure(s)
  ```
  Restored with Edit, re-ran → back to `0 failure(s)`, all 4 PASS.
- **git diff scope**: `README.md` (new sections only, existing content untouched) +
  `tests/test_readme_examples.py` (new file).
- **Effort**: S — **Status**: **CLOSED**

### DEBT-W10: validate-test-pool.sh — Python-only scope — premise re-measured 2026-08-22, stays OPEN with a sharper reason

- **What the ticket assumed**: "Does not validate Go or Elixir test files" — implying a Go/Elixir
  clone of the Python orphan-detector is missing work.
- **What was actually measured (real CI invocation, not assumed)**: `validate-test-pool.sh`
  exists because THIS fleet's Python CI (`reusable-test.yml:204`) runs pytest **per-file, off an
  explicit curated list** (`for test_file in ...: pytest ... "$test_file"`) — so a new
  `tests/test_foo.py` that nobody adds to that list silently never runs. That's the real failure
  mode the script guards against.
  Go and Elixir do **not** have that failure mode, verified against this repo's own real
  workflows:
  ```
  $ grep -n "go test" .github/workflows/reusable-test-go.yml
  150:          go test $RACE_FLAG $TAGS_FLAG -coverprofile=coverage.out -covermode=atomic ./...
  $ grep -n "mix coveralls\|mix test" .github/workflows/reusable-test-elixir.yml
  169:        run: mix coveralls.json
  206:          mix coveralls 2>/dev/null | grep ...
  ```
  `go test ./...` and `mix coveralls` (which wraps `mix test`) both **auto-discover every test
  file** in the module/project unconditionally — there is no curated list for a new test file to
  fall out of sync with. Cross-checked against 2 real repos' actual `run_prepush.sh` (not just
  the reusable workflow): `alebrije-mod-crm-go/run_prepush.sh:149` runs
  `go test ... ./... -count=1 ...` (full auto-discovery); `alebrije-mod-agenda-ex/run_prepush.sh:99`
  runs `mix coveralls --max-failures 20` (full auto-discovery, no `Code.require_file` curated
  list — that pattern only appears in this session's own ad-hoc dev-machine workaround for a
  local Postgres auth limitation, documented separately in this project's memory, and is **not**
  the repo's committed prepush/CI mechanism).
- **Conclusion**: writing a Go/Elixir clone of this script would be solving a problem that does
  not exist in either ecosystem's real invocation in this fleet — dead code with nothing to catch,
  and worse, it would read as "orphan-test coverage now handled for Go/Elixir" when the real risk
  was never there to begin with (same shape of harm as `gen_api_collection.py`'s false "0 is
  clean" — a mechanism that LOOKS like protection but protects against nothing).
  The one edge that IS real for Go — a `//go:build <tag>` test file silently excluded from
  `./...` unless `-tags` matches — is already a first-class, deliberate input on this repo's own
  `reusable-test-go.yml` (`test-tags`), not an accidental omission; out of scope for this ticket.
- **Effort**: (re-scoped to zero — the described gap does not exist) — **Status**: **OPEN**, but
  the "Python-only scope" framing is retired; re-open only if a Go/Elixir repo is found that
  genuinely curates an explicit test-file list the way Python's `reusable-test.yml` does.

### DEBT-W11: Event schemas — required fields missing descriptions — CLOSED 2026-08-22

- **Recount before fixing (Regla: verify the number, don't trust it)**: the ticket said 21. A
  fresh walk of every `event-schemas/*.json` (required-array membership + own `description` key,
  recursing through `allOf`) found **22**, one more — `envelope.v1.json`'s top-level `producer`
  field (required by the envelope itself, object had `type`/`required`/`properties` but no
  `description` of its own, even though its nested `service`/`version` sub-fields did). The
  ticket's "21" undercounted by missing this envelope-level field; using the measured 22, not the
  ticket's stale count.
- **Fix**: added `description` to all 22: `cadences.converted.v1.json` (cadence_instance_id,
  cadence_id, contact_id, converted_at), `cadences.enrolled.v1.json` (same 4 field names,
  enrollment context), `crm.contact.stage_changed.v1.json` (contact_id), `envelope.v1.json`
  (producer, object-level), `field_ops.order.completed.v1.json` (order_id, completed_at),
  `notifications.email.delivered.v1.json` (recipient, delivered_at),
  `notifications.email.opened.v1.json` (notification_id, recipient, opened_at),
  `payments.invoice.overdue.v1.json` (invoice_id, due_date, days_overdue),
  `payments.payment.completed.v1.json` (payment_id, currency). Purely additive metadata — no
  `type`/`required`/`pattern`/`enum` touched, zero validation-behavior change.
- **Mechanism**: new permanent regression test `test_required_fields_have_descriptions` in
  `tests/test_event_schemas.py` (same file as the existing `test_all_event_schemas_still_structurally_valid`,
  copied its glob-and-walk shape) — walks every schema's `required` arrays (including nested
  `allOf` and `properties`) and fails naming the exact `file: path.to.field` for any required
  field still missing a `description`.
- **Mechanism run + control in both directions**:
  ```
  $ python3 tests/test_event_schemas.py
  ... (16 tests)
  16 passed, 0 failed, 16 total
  ```
  Reverted `payments.payment.completed.v1.json`'s `currency` description with Edit, re-ran:
  ```
  FAIL test_required_fields_have_descriptions: 1 required field(s) missing description: ['payments.payment.completed.v1.json: data.currency']
  15 passed, 1 failed, 16 total
  ```
  Restored with Edit, re-ran → `16 passed, 0 failed, 16 total` again; `git diff --stat` on that
  file showed exactly the intended 2-field addition (payment_id + currency), no residual
  break/restore artifact. All 15 pre-existing tests in the file (DEBT-W13/W14 regressions,
  AQ-112, rewards outbox shape, etc.) still pass unchanged.
- **git diff scope**: the 9 schema files listed above + `tests/test_event_schemas.py` (one new
  test function appended, nothing else in the file touched).
- **Effort**: S — **Status**: **CLOSED**

### DEBT-W12: setup-vault-token — `vault-token` output never populated — fix shipped, E2E still not run, stays OPEN 2026-08-22

- **Fix applied**: added `outputToken: "true"` to the `hashicorp/vault-action@4c06c5ccf5c0761b6029f56cfb1dcf5565918a3b`
  step inside `setup-vault-token/action.yml`. Without it, the pinned action's own
  `outputToken` local (src/action.js:19) defaults to `false`, and its
  `core.setOutput('vault_token', ...)` call (src/action.js:90-91) is gated behind
  `if (outputToken === true)` — so the composite action's declared
  `outputs.vault-token` (→ `steps.vault.outputs.vault_token`) was unconditionally
  an empty string. Zero blast radius today: `grep -rln "setup-vault-token"
  alebrije-*/.github` across the 33-repo cowork still finds no caller.
- **Verification actually run (real vendored source + real @actions/core, not
  reimplemented, not guessed)**: fetched the pinned commit's real
  `src/action.js` (`https://raw.githubusercontent.com/hashicorp/vault-action/4c06c5ccf5c0761b6029f56cfb1dcf5565918a3b/src/action.js`),
  extracted the literal `const outputToken = ...` line by regex (not retyped), and
  installed the real `@actions/core` npm package (declared in a throwaway
  harness `package.json`, not vendored/assumed) to evaluate it under both real
  input-passing scenarios:
  ```
  Extracted REAL line from vault-action src/action.js:
    const outputToken = (core.getInput('outputToken', { required: false }) || 'false').toLowerCase() != 'false';

  BEFORE: INPUT_OUTPUTTOKEN=undefined -> outputToken=false -> core.setOutput('vault_token', ...) would run: false
  core.getInput("outputToken") with INPUT_OUTPUTTOKEN=true -> "true"
  AFTER: INPUT_OUTPUTTOKEN="true" -> outputToken=true -> core.setOutput('vault_token', ...) would run: true

  RESULT: PASS (fix flips the real guard as intended)
  ```
  This proves the fix flips the exact real guard that was broken, using GH
  Actions' real `INPUT_<NAME>` env-var convention and the real
  `@actions/core.getInput` implementation — not a re-implementation.
- **Why this stays OPEN instead of CLOSED (measured, not assumed)**: the ticket's
  own bar, restated in this session's brief, is "lo que no se ejecuta no se
  cierra" — and the part NOT executed is `retrieveToken()`/`getSecrets()`, i.e.
  the actual Vault kubernetes-auth login, which runs BEFORE the line verified
  above reaches `core.setOutput`. **Correcting the previous census note**: a
  real Vault IS available locally (`kubectl get pods -n vault` → `vault-0
  1/1 Running`, unsealed, `Version 1.17.2`) — "no vault available" was wrong.
  The real, narrower blocker: reading `auth/kubernetes/role/ci-runner-role` (to
  know which ServiceAccount to mint a token for) requires an authenticated
  Vault client:
  ```
  $ kubectl exec -n vault vault-0 -- sh -c 'vault read auth/kubernetes/role/ci-runner-role'
  Error reading auth/kubernetes/role/ci-runner-role: ... Code: 403 ... permission denied
  ```
  Obtaining that access (root token, or an admin policy) is exactly the class
  of operation Alebrije's own guardrails (`memory/feedback_m212_m213_m214_m215_categoria_destructivos_20260519.md`
  Regla K / M213) restrict to the user's local terminal, not a session
  auditing an unused, zero-caller composite action. This session declines to
  escalate for that reason, not because the infra doesn't exist.
- **git diff scope**: `.github/actions/setup-vault-token/action.yml` only (one
  line + comment added, nothing removed).
- **Effort**: XS — **Priority**: unchanged (#2 by peor razon, see ronda-2 ranking
  above) — **Status**: **OPEN** (fix shipped, full E2E not executed — see above)

### Fixed in session 2026-05-31

- **reusable-property-tests.yml ts-property step (line 219): `|| true` no-op on `npx vitest run` removed — property gate is now FATAL.**
  - **Problem**: The fast-check step appended `|| true` to `npx vitest run ... --coverage=false`, making the
    property-testing job a no-op across the entire TS fan-out — a failing invariant / shrunk counterexample
    exited 0 and never failed CI. This is the exact anti-pattern that `validate-self.yml:183-189` audits for
    ("`|| true` in test/coverage steps — FATAL anti-pattern", Rule #11).
  - **Root-cause fix**: Dropped `|| true` inside the existing `if find ... | grep -q .` branch. When property
    test files EXIST → `npx vitest run` runs FATALLY (a failing property fails the job). When NO `*.property.test.{ts,js}`
    files exist → the pre-existing `else` branch emits `::notice::No *.property.test.ts files found (optional)` and
    exits 0 — an explicit conditional skip, NOT a no-op. Pattern mirrors `reusable-test-ts.yml:124-158`
    (fatal coverage gate, `# Fail if below threshold (fatal, no || true)`) and the python step of this same
    workflow (lines 86-92, advisory skip on missing `tests/property/`).
  - **Verification** (throwaway vitest@2.1.9 + fast-check@3.23.1 harness in /tmp, `bash -euo pipefail` = GH Actions default shell):
    - Failing property present → NEW step exit **1** (FATAL, vitest "Property failed after 1 tests"); OLD `|| true` line exit **0** (the masked bug).
    - All properties pass → NEW step exit **0** (no false-fail; vitest "Tests 1 passed").
    - No property files → NEW step exit **0** with `::notice::No *.property.test.ts files found (optional)` (explicit skip).
    - YAML re-validated: `yamllint` (CI invocation) exit 0 (only pre-existing document-start/truthy warnings, identical in sibling workflows); `python3 yaml.safe_load` OK, all 4 jobs intact.
  - **Effort**: S — **Status**: CLOSED

### DEBT-W17: reusable-property-tests.yml — Go & Elixir steps mask test failures via `|| { echo ...; }` (SAME no-op class as the just-fixed TS bug) — FIXED 2026-05-31

**Renumbered from DEBT-W14 to DEBT-W17 on 2026-08-22** — this ticket and the *different* ticket
below (`cross-repo-trigger.yml`'s `::set-output` gap) were both filed under the ID `DEBT-W14`,
a duplicate the 2026-08-21 census already noticed and named ("DEBT-W14, dos veces con el mismo
ID") but never resolved. Verified before renaming that no code outside this file references
this ticket by ID (`grep -rn "DEBT-W14" --include='*.md' --include='*.yml' --include='*.py'
--include='*.sh' .` outside `TECHNICAL-DEBT.md` only hits `tests/test_event_schemas.py`, and
both hits there are about the *other* ticket — the `cross-repo-trigger.yml` one, which keeps the
`DEBT-W14` ID unchanged so that reference stays correct). A duplicate ticket ID is a real defect
in this tracker, not cosmetic: any tool that resolves debt items by ID (e.g. this project's own
`docs-avance.sh ver <ID>` pattern) would silently return whichever of the two entries `grep`
happens to hit first.

- **What**: The Go step (`go test ... || { echo "::notice"; }`) and Elixir step (`mix test ... || { echo "::notice"; }`)
  used the brace-block idiom to handle the "no property tests yet" case. Confirmed under `bash -euo pipefail`
  (GitHub Actions default shell) that `<failing-cmd> || { echo ...; }` exits **0** whether the command fails,
  passes, or finds nothing — so a genuinely failing Go/Elixir property silently passed CI. Same no-op class as
  the bare `|| true` removed from the TS step, only less obvious.
- **Root-cause fix**: Re-gated both steps with explicit existence detection → run-fatally / else explicit skip,
  mirroring the ts-property step of this same workflow + `reusable-test-ts.yml:124-158` (fatal coverage gate,
  `# Fail if below threshold (fatal, no || true)`) + `reusable-mutation-test.yml:140-161` (`if [ ! -f ... ]; then ... exit 1`):
  - **Go**: `if grep -rlqE '(func TestProperty)|(//go:build property)|(+build property)' --include='*_test.go' .; then go test -tags=property -run=TestProperty ./... -count=N -v; else echo "::notice::No property tests found ... — optional"; fi`.
    Existence detection is REQUIRED: `go test -run=TestProperty` itself exits 0 with "no tests to run" when nothing
    matches, which is indistinguishable from a real pass without the grep guard.
  - **Elixir**: `if grep -rlq '@tag :property' --include='*.exs' --include='*.ex' .; then mix test --include property --max-cases N; else echo "::notice::No property tests tagged with @tag :property found (optional)"; fi`.
  - Detection uses the EXISTENCE signals named in DEBT spec: Go = `TestProperty`/`+build property`/`//go:build property`;
    Elixir = `@tag :property`. When tests EXIST → fatal. When ABSENT → explicit `::notice::` skip (exit 0), NOT a no-op.
- **Verification** (throwaway exit-code harness in `/tmp`, `bash -e` = GH Actions default shell; output cited):
  - OLD masking idiom, failing cmd → exit **0** (the masked bug reproduced).
  - NEW Go gate: exist+passing → **0**; exist+FAILING → **1** (FATAL); absent → **0** (explicit skip). 3/3 PASS.
  - NEW Elixir gate: exist+passing → **0**; exist+FAILING → **1** (FATAL); absent → **0** (explicit skip). 3/3 PASS.
  - Detection greps (exact YAML commands): `go_has`→MATCH, `go_none`→NO MATCH, `ex_has`→MATCH, `ex_none`→NO MATCH (no false positives on empty dirs / non-`_test.go` files). Harness total: 10 passed, 0 failed; full step sim: 6 passed, 0 failed.
  - YAML re-validated with the EXACT `validate-self.yml` validate-yaml config:
    `yamllint -d "{extends: default, rules: {line-length: {max: 180}, comments: {min-spaces-from-content: 2}}}"`
    → exit **0** (only the two pre-existing `document-start` + `truthy` warnings, identical across sibling workflows, unchanged by this edit). `python3 yaml.safe_load` OK, all 4 jobs intact, `workflow_call` trigger + inputs preserved, no tabs.
  - Anti-pattern audit: zero `|| {` / `|| true` remain on any executable (non-comment) line; remaining matches are documentary comment references to the canonical pattern (consistent with the already-shipped TS step). `validate-self.yml check-anti-patterns` is WARN-only (never `exit 1`).
- **Effort**: M — **Priority**: P2 — **Status**: CLOSED

### DEBT-W13: envelope.v1 — AQ-112 sender_type/branch_id added (DONE) + per-event doc surfacing (OPEN)
- **What (DONE 2026-05-30, lane AQ112-ENVELOPE-PRODUCERS)**: `event-schemas/envelope.v1.json` gained
  two optional+nullable top-level fields — `sender_type` (enum `client|employee|tenant_admin|null`)
  and `branch_id` (string|null, maxLength 36). Neither is in `required`, so all existing events stay
  valid (backward-compat verified with jsonschema: validates with the fields, without them, and with
  explicit nulls; rejects out-of-enum sender_type + over-length branch_id). All `.base.`/event schemas
  inherit these via `allOf $ref envelope.v1.json` — no per-event schema edits were needed.
- **What (DONE 2026-05-31)**: `omnichannel.message.received.v1.json` now surfaces `sender_type` and
  `branch_id` per-event in its own `allOf[-1].properties` (siblings of `event_type`/`data`), each with
  AQ-112 consumer documentation describing the producer source (omnichannel conversation
  `sender_type` column / `context_id`). Constraints mirror the envelope (`sender_type` enum
  `client|employee|tenant_admin|null`, `branch_id` maxLength 36) so the merged `allOf` cannot
  contradict. Behavior verified with the documented jsonschema/draft-07 validator (registry resolves
  the envelope `$ref` by `$id`): events validate with the fields, without them (backward-compat), and
  with explicit nulls; out-of-enum `sender_type` and over-length `branch_id` are rejected. Tests:
  `tests/test_event_schemas.py` (test_aq112_fields_surfaced_in_event_schema,
  test_event_with_aq112_fields_validates, test_invalid_sender_type_rejected,
  test_over_length_branch_id_rejected, + backward-compat cases).
- **Effort**: XS — Status: **CLOSED** (schema DONE; per-event doc surfacing DONE)

---

### DEBT-W14: cross-repo-trigger.yml emitted disabled `::set-output` — orchestration outputs silently empty (FIXED)
- **What (was broken)**: `cross-repo-trigger.yml` (ADR-001 Bloque L) captured its three orchestration
  outputs (`count`, `has-timeout` in prepare-dispatch; `run-ids` in dispatch-workflows) via the
  `print("::set-output name=...")` worker command. GitHub disabled that command on hosted runners in
  2023, so each was a no-op: `prepare-dispatch.outputs.dispatch-count` was empty (report-status job
  printed a blank `Total targets`), and `steps.dispatch.outputs.run-ids` was never set (wait-completion
  run-id correlation degraded). Source: audit `AUDIT_FUNCTIONAL_GAPS_BY_MODULE_20260531.md` workflows
  gap #1 (P1/S), file:linea 94-95 + 210.
- **What (DONE 2026-05-31)**: replaced all three emissions with writes to
  `os.environ["GITHUB_OUTPUT"]` (the canonical pattern already used in
  `reusable-release-extended.yml:142-145`); the `has-timeout` value keeps its
  `${{ inputs.timeout-seconds > 0 }}` Actions expression (template-substituted before the heredoc runs).
  Added regression guard `validate-self.yml` AUDIT 17 `check-no-deprecated-set-output` (FATAL, exit 1,
  wired into `security-audit-summary` needs + fail-gate) — built so the guard never matches its own
  detection literal. Tests: `tests/test_event_schemas.py` (test_no_deprecated_set_output_remains,
  test_outputs_written_to_github_output, test_workflow_yaml_parses_and_keeps_declared_outputs,
  test_has_timeout_expression_still_template_substituted).
- **Side fix**: while editing the `validate-self.yml` `security-audit-summary` `needs:` line (already
  364 chars, over the repo's yamllint 180-char limit before this session — a pre-existing
  `validate-yaml` job failure), converted the flow sequence to a YAML block sequence. yamllint now
  exits 0 (only the two pre-existing `document-start` + `truthy` warnings remain).
- **Known remaining limitation (not in scope of this gap)**: `dispatch-workflows` is a matrix job, so
  `steps.dispatch.outputs.run-ids` still collapses to the last matrix instance's value (a standard
  GitHub Actions matrix-output constraint, independent of the `::set-output` bug). Aggregating run-ids
  across all matrix legs would need a separate fan-in job. See gaps_blocked / DEBT below.
- **Effort**: S — **Priority**: P1 — **Status**: **FIXED** (audit gap closed; matrix fan-in tracked separately)

### DEBT-W15: cross-repo-trigger matrix run-id aggregation (OPEN, follow-up to W14)
- **What (OPEN)**: `dispatch-workflows.outputs.run-ids` maps to `steps.dispatch.outputs.run-ids`, but
  because the job uses `strategy.matrix.repo`, GitHub only preserves the LAST matrix leg's output. To
  correlate run-ids for every dispatched repo, add a fan-in job that collects per-leg outputs (e.g. via
  per-repo artifacts or a JSON-array output keyed by repo). The `::set-output`→`$GITHUB_OUTPUT` fix
  (W14) was a prerequisite; this aggregation is the remaining functional improvement.
- **Effort**: M — **Priority**: P3 — **Status**: OPEN

### DEBT-W16: validate-self.yml AUDIT 5 (check-anti-patterns) — the repo's own `|| true`/`--no-verify` self-audit was blind AND permanently noisy — CLOSED 2026-08-22

- **What was broken (found by actually running the mechanism, per AQ-003, not by reading the
  YAML and trusting it)**: `check-anti-patterns` (AUDIT 5, the job whose own header comment calls
  its `|| true` check a "FATAL anti-pattern") had two independent, compounding defects, same
  failure shape as DEBT-001/W07/W02 on this session: it *looked* like a working guard and was
  not.
  1. **Scope blind spot**: the job's `on.push`/`on.pull_request` triggers already watch
     `paths: [.github/workflows/**, .github/actions/**]` (line 21/24 of this file), but the
     check's own body only ever `grep -r`'d `.github/workflows` — never `.github/actions`. That
     is exactly where this session's own DEBT-W02 fix lived (`trigger-canary/action.yml`'s
     `kubectl patch ... 2>/dev/null || true` unconditional-success bug) — the repo's own
     self-audit could never have caught the bug this same session found and fixed by hand.
  2. **Regex bug (`|| true` check)**: the pattern
     `'\btest\b.*|| true\|\bcov\|coverage.*|| true'` has an untethered middle alternative
     (`\bcov`) with **no `|| true` requirement at all** — it matches any line containing
     "cov"/"coverage" regardless of content. Reproduced by running the *exact* old command
     against this repo's own tree before touching anything: **129 hits**, almost all just the
     word "coverage" in unrelated comments/step names — including the check's own source line
     describing itself. A signal drowned in 129:1 noise is indistinguishable from no signal.
  3. **Self-reference bug (`--no-verify` check)**: `grep -r '\--no-verify' .github/workflows`
     matches its own 4 lines of comment/echo text that literally contain the string
     `--no-verify` to explain what the check does — verified this fires on **every single run**
     regardless of repo content, since the check has never NOT matched itself. Confirmed this
     predates this session (unrelated to today's edits, present since the file's 2026-05-07
     origin per this document's own history).
  Neither defect is hypothetical or theoretical severity: (1) is a real blind spot proven by
  this session's own DEBT-W02 finding; (2) and (3) are 100%-of-runs alert fatigue that trains
  reviewers to ignore the `::warning::` line entirely — the exact precondition under which a
  *real* `|| true`/`--no-verify` addition would go unnoticed, i.e. the check protects against
  nothing while looking like it protects against everything.
- **Fix**: rewrote both checks in the same step to (a) scan `.github/workflows` AND
  `.github/actions` (matching the job's own real trigger paths), (b) strip shell comments
  per-file before matching (`sed -E 's/(^|[[:space:]])#.*$//'`, the exact idiom this file's own
  Census section already established and proved for the `scripts/` audit — Regla 13: pattern
  copied from `TECHNICAL-DEBT.md`'s own "Continuacion 2026-08-22 — confirmacion de ronda 2"
  suppression-audit control, cited above), so a line that *mentions* `|| true`/`--no-verify` in
  prose to explain why it was removed (this very file has several) is never counted as a use,
  (c) tighten the `|| true` regex to require the flag on *both* branches
  (`\b(test|cov(erage)?)\b.*\|\|[[:space:]]*true\b`), and (d) exclude `validate-self.yml` itself
  from the `--no-verify` scan (it legitimately has to say the string in prose to implement the
  check). Severity kept as-is (`::warning::`, never `exit 1`) — this fix is about signal
  accuracy and coverage, not about turning an advisory into a gate; that would be a separate,
  bigger decision this session does not make.
- **Blast radius checked before touching**: `validate-self.yml` is triggered by
  `push`/`pull_request`/`schedule`/`workflow_dispatch` on **this repo's own tree** — it is not a
  `workflow_call` reusable workflow consumed by the fleet (verified: `on:` block has no
  `workflow_call:` key). Unlike DEBT-002's regex, tightening this one carries zero cross-repo
  blast radius; it only changes what `alebrije-workflows`' own CI warns about on its own future
  commits.
- **Mechanism run, real content, structurally extracted (not retyped) — both checks**:
  ```
  $ python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/validate-self.yml')); \
      print([s['run'] for s in d['jobs']['check-anti-patterns']['steps'] \
      if s.get('name','').startswith('Check for error suppression')][0])" > /tmp/extracted.py
  $ python3 /tmp/extracted.py   # via bash wrapper, same content
  Checking for || true in test/coverage steps...
  ::warning::Found || true in test/coverage context (Rule #11):
  .github/workflows/reusable-test.yml:
  229:            grep -E "TOTAL|Total" coverage.txt >> $GITHUB_STEP_SUMMARY || true
  Checking for --no-verify flag...
  ✓ Anti-pattern check complete
  ```
  One real, legitimate hit remains — `reusable-test.yml:229`'s `grep -E "TOTAL|Total"
  coverage.txt >> $GITHUB_STEP_SUMMARY || true` — read in context
  (`.github/workflows/reusable-test.yml:217-232`): it is inside the "Write coverage summary"
  step (`if: always()`), a purely cosmetic step that appends to `$GITHUB_STEP_SUMMARY` for human
  visibility; the real fatal gate already ran earlier (`exit $EXIT_CODE` at line 213, no
  suppression) and the 90% coverage floor is enforced separately. `|| true` here only tolerates
  `grep` finding no `TOTAL`/`Total` line in `coverage.txt`, it does not swallow a test or
  coverage failure. Left as-is (verified benign, cited above), not part of this ticket's fix
  scope, and now visible instead of buried under 129 false positives.
- **Control in two directions (Edit on real repo files, not git; not a harness in `/tmp`)**:
  injected into `.github/workflows/reusable-benchmark.yml` (a real, unrelated workflow, chosen
  for low blast radius) a real anti-pattern (`go test ./... || true`, `git commit --no-verify -m
  "control"`) **and**, on the line right above, a comment-only mention of the exact same two
  strings ("nunca escribas go test ... || true ni git commit --no-verify aqui"):
  ```
  # RED — both real uses caught, the comment mention on the line above is absent from output:
  ::warning::Found || true in test/coverage context (Rule #11):
  .github/workflows/reusable-benchmark.yml:
  78:          go test ./... || true
  .github/workflows/reusable-test.yml:
  229:            grep -E "TOTAL|Total" coverage.txt >> $GITHUB_STEP_SUMMARY || true
  Checking for --no-verify flag...
  ::warning::Found --no-verify flag (bypasses commit hooks):
  .github/workflows/reusable-benchmark.yml:
  79:          git commit --no-verify -m "control"
  ```
  Restored `reusable-benchmark.yml` to its original content with Edit; re-ran:
  ```
  # GREEN — back to only the one pre-existing, verified-benign hit:
  ::warning::Found || true in test/coverage context (Rule #11):
  .github/workflows/reusable-test.yml:
  229:            grep -E "TOTAL|Total" coverage.txt >> $GITHUB_STEP_SUMMARY || true
  Checking for --no-verify flag...
  ✓ Anti-pattern check complete
  ```
  `git diff -- .github/workflows/reusable-benchmark.yml` and
  `git status --porcelain -- .github/workflows/reusable-benchmark.yml` both empty after restore.
  First attempt at the `--no-verify` self-exclusion used a `./`-prefixed path
  (`[ "$f" = "./.github/workflows/validate-self.yml" ]`) that never matched — `find
  .github/workflows .github/actions ...` (search roots without a leading `./`) yields paths
  like `.github/workflows/validate-self.yml`, not `./.github/workflows/...`. Caught by actually
  running it (the self-exclusion silently did nothing, self-match still fired) before trusting
  the fix — corrected to the real path shape and re-verified above.
- **Second, more serious defect found by testing the FAITHFUL GitHub Actions shell, not a
  loosely-flagged one — this one would have shipped as a real regression**: every mechanism run
  cited above through this point in the ticket had been executed with `bash -uo pipefail`, not
  GitHub Actions' real default for `run:` steps without an explicit `shell:`, which is
  `bash --noprofile --norc -eo pipefail {0}` (`-e` included). Re-ran the exact extracted step
  under the faithful invocation before considering this ticket closed:
  ```
  $ bash --noprofile --norc -eo pipefail /tmp/extracted_faithful.sh
  ::group::Anti-pattern detection...
  Checking for || true in test/coverage steps...
  EXIT=1
  ```
  The step **aborted after printing a single line**, never reaching a single real result. Root
  cause: `hit=$(sed ... | grep -nE ...)` is a bare assignment, not inside an `if`/`while`/`&&`
  test — under `-e`, a `grep` that finds **no match** (the expected, common case for the vast
  majority of files scanned) returns 1, and that non-zero status propagates through the
  assignment and kills the whole script on the very first non-matching file. This is exactly why
  the OLD, buggy one-liner had `suspicious=$(... || true)` — that `|| true` was not decorative,
  it was load-bearing for `-e` compatibility, and restructuring into a per-file loop silently
  dropped it. Had this shipped unverified, `check-anti-patterns` would have gone from
  "always warns, never fails" (the noisy bug) to **"always fails, on every single push and PR to
  this repo, for a shell-scripting reason unrelated to any real anti-pattern"** — a strictly
  worse regression than either original defect, and the exact class of bug this session's own
  guardrails warn about verifying before trusting a "0 hits"/"exit 0" result. **Fix**: added
  `|| true` back onto both `hit=$(...)` assignments (the `|| true` check's and the `--no-verify`
  check's). Re-verified under the faithful shell:
  ```
  $ bash --noprofile --norc -eo pipefail /tmp/extracted_faithful.sh
  ::group::Anti-pattern detection...
  Checking for || true in test/coverage steps...
  ::warning::Found || true in test/coverage context (Rule #11):
  .github/workflows/validate-self.yml:
  211:            hit=$(sed -E 's/(^|[[:space:]])#.*$//' "$f" | grep -nE '\b(test|cov(erage)?)\b.*\|\|[[:space:]]*true\b' || true)
  .github/workflows/reusable-test.yml:
  229:            grep -E "TOTAL|Total" coverage.txt >> $GITHUB_STEP_SUMMARY || true
  Checking for --no-verify flag...
  ✓ Anti-pattern check complete
  ::endgroup::
  EXIT=0
  ```
  **Third self-reference, found by this exact re-run**: the `|| true` just added to satisfy `-e`
  is itself a real, literal `|| true` sitting next to the word "test" on that same source line —
  a genuine textual match, not a regex bug this time, since the check's own necessary defensive
  code will always need to say `|| true` next to "test" to keep functioning under `-e`. Applied
  the same self-exclusion already used for the `--no-verify` check
  (`[ "$f" = ".github/workflows/validate-self.yml" ] && continue`) to this loop too. **Tradeoff
  accepted and documented, not silently chosen**: this excludes the ENTIRE `validate-self.yml`
  file (1600+ lines, dozens of jobs) from the `|| true` scan, not just this one line — a real
  business-logic `|| true` added to a different job in this same file in the future would not be
  caught by this check. Judged acceptable because this file's own jobs are exclusively
  meta-validation (yamllint, grep-based structural checks, actionlint) and never run `go
  test`/`pytest`/coverage business logic themselves — the risk this check exists to catch does
  not occur inside its own file except as this one necessary, cited exception. Re-verified clean
  under the faithful shell (shown above, `EXIT=0`), then re-ran the full both-directions control
  (inject into `reusable-benchmark.yml`, RED with both real hits + comment mention correctly
  ignored, restore, GREEN) a second time under `bash --noprofile --norc -eo pipefail`
  specifically (not the looser `-uo pipefail` used for the first pass) — same RED/GREEN result
  as documented above, this time under the shell that actually matches production.
- **Validated**: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/validate-self.yml'))"`
  → OK; `yamllint -d "{extends: default, rules: {line-length: {max: 180}, comments:
  {min-spaces-from-content: 2}}}" .github/workflows/validate-self.yml` → exit 0, only the two
  pre-existing `document-start`/`truthy` warnings shared by every workflow in this repo, no new
  warnings.
- **git diff scope**: `.github/workflows/validate-self.yml` only (the "Check for error
  suppression in critical contexts" step body).
- **Effort**: S — **Priority**: P1 by peor razon (this repo's own quality gate, ADR-001 Bloque
  R — same class as DEBT-W07, which also ranked #2 worst in the 2026-08-22 census) —
  **Status**: **CLOSED**

---

## §43 — Supply-chain audit (base-image whitelist)

### DEBT-§43-SUPPLY-CHAIN-6: approved-images gate had 0 callers (FIXED)
- **What**: `reusable-approved-images-check.yml` defined the base-image whitelist gate as a reusable
  `workflow_call`, but **no repo in the fleet referenced it** (`grep` across all `.github/workflows`
  returned 0 callers) — the gate never ran, so a Dockerfile could introduce an unapproved/unsafe base
  image and no CI step would catch it.
- **Root cause**: the gate was shipped as an opt-in reusable workflow that every consumer would have had
  to wire individually. Asking 33 repos to each add a `uses:` block is fragile and was never done.
- **Fix (robust)**: wired the same matcher **inline** into `reusable-build-push.yml` as a pre-build step
  (`Gate — validate Dockerfile base images against whitelist`). It sparse-checks out
  `approved-base-images.json` from `alebrije-workflows@main` and validates the exact Dockerfile being
  built (`${context}/${dockerfile}`) **before** the Docker build, failing the job on a non-approved
  `FROM`. All ~33 build-push consumers now get the gate for free — no change to their `ci.yml`. The
  standalone `reusable-approved-images-check.yml` is retained as opt-in (PR-only checks / repos that
  don't build images) and documents the enforcement path in its header comment.
- **Matcher hardening (prerequisite for wiring)**: the original matcher would have produced
  false-positive violations on multi-stage stage references (`FROM builder`) and templated FROMs
  (`${BUILDER_IMAGE}`, `golang:${GO_VERSION}-alpine`) — 14 build-arg FROMs across the fleet. Fixed in
  both the standalone workflow and the inline gate: collect `AS <stage>` aliases and skip them, and skip
  any `FROM` whose name/ref is templated. Validated against all 107 fleet `FROM` lines → 2 residual
  flags, both legitimate non-CI-built files (`arc/Dockerfile` ARC runner `:latest`; planificador
  `Dockerfile.local` dev-only) that the gate does not build.
- **Effort**: M — **Priority**: P2 — **Status**: **FIXED**

### DEBT-§43-SUPPLY-CHAIN-7: approved-base-images.json drifted from real Dockerfiles (FIXED)
- **What**: the whitelist tags no longer matched the fleet's real base images: golang listed
  `1.24/1.23/1.22` (real: `1.26.3-alpine`/`1.26.3-bookworm`), elixir `1.18-otp-27` (real: `1.19-alpine`/
  `1.19-slim`), alpine `3.21/3.20/3.19` (real: `3.23` dominant), and **distroless was entirely absent**
  even though 10 Go services use `gcr.io/distroless/static[-debian12]:nonroot` as their hardened runtime
  base — the gate would have flagged the fleet's *most secure* images as violations.
- **Fix**: rebuilt `approved-base-images.json` strictly from verified disk evidence (aggregated every
  `FROM` across the fleet). Now lists the real golang 1.26.3 / elixir 1.19 / alpine 3.23(+3.21,3.20)
  tags, the real python slim/slim-bookworm/alpine variants, node `22-bookworm-slim`, and adds the
  previously-missing production runtime bases: `gcr.io/distroless/static`,
  `gcr.io/distroless/static-debian12`, `debian` (bookworm-slim/trixie-slim), `nginx` (1.27-alpine).
  postgres/redis CI service-container tags retained. Validated: 0 false-positive violations against the
  real fleet.
- **Effort**: S — **Priority**: P2 — **Status**: **FIXED**

---

## §44 — DEBT-FN-ADR-79-EVENT-BUS-SCHEMA-REGISTRY (infra-CI portion) reconciliation

### DEBT-§44-CONTRACT-GAP-RECONCILE: consumers.yaml missing 2 real live consumers (FIXED); false premise that files "don't exist" corrected
- **Premise received (INCORRECT)**: assigned task stated `event-schemas/consumers.yaml` and
  `.github/workflows/reusable-event-contract.yml` "no existen." Verified on disk: **both already
  existed** before this session — `consumers.yaml` created `fd1c248` (2026-06-09) and iterated through
  `445b8c7` (2026-06-26); `reusable-event-contract.yml` created 2026-06-20, `uses:`-wired into 10
  consumer repos' `ci.yml`/`elixir-ci.yml` (crm-go, rewards-go, payments-go, mcp-go, agentic,
  control-medico, cadences-ex, notifications-ex, omnichannel-ex, planificador-ex). This corresponds to
  the already-**CLOSED** `DEBT-§34-EVT-CONTRACT-TEST-GAP` in the central `alebrije/TECHNICAL-DEBT.md`
  (§39, 2026-06-17). The task premise conflated that closed ticket with the still-**OPEN**
  `DEBT-FN-ADR-79-EVENT-BUS-SCHEMA-REGISTRY`, whose real remaining scope is deploying an actual schema
  registry TOOL (e.g. EventCatalog UI) on top of Redis Streams — a separate, undecided item (do-now: no;
  see `AQ-001` above). No files were recreated from scratch; recreating them would have discarded ~3
  weeks of accumulated, source-cited fleet reconciliation work.
- **Real gap found by re-grepping the fleet (2026-07-01)**: `consumers.yaml`'s own
  `derived_at: 2026-06-09` snapshot missed 2 live consumers that existed in the repos at grep time:
  1. `alebrije-mod-campaigns-ex` `AlebrijeCampaigns.Workers.EventConsumer` (Broadway over
     `events:crm`) — handles `crm.contact.opted_out`, `crm.contact.opted_in`, `crm.contact.created`,
     `crm.contact.updated`, `appointment.completed`. Was entirely absent from the map.
  2. `alebrije-svc-notifications-ex` `AlebrijeNotifications.Toronja.ResultConsumer` (Broadway,
     `toronja.result_validated` stream, group `notifications-ex-toronja`) — a REAL prod consumer gated
     by `TORONJA_CONSUMER_ENABLED=true` (`config/runtime.exs:329-348`). Was entirely absent; the only
     toronja entry in the map was mcp-go's (mismatched) `toronja.lab.result_ready`.
- **Fix**: added `alebrije-mod-campaigns-ex` / `crm.contact.created` to `subscriptions:` (schema IS
  registered, `crm.contact.created.v1.json`); added the other 4 campaigns-ex event types + the
  notifications-ex `toronja.result_validated` consumer to `unverified_drift:` (no schema registered for
  any of them yet — moving them to `subscriptions:` without a schema would break CI by design). Bumped
  `last_reconciled_at: 2026-07-01` in the file header.
- **Verified**: `python3 -c "import yaml; yaml.safe_load(open('event-schemas/consumers.yaml'))"` parses
  clean (22 subscriptions, 12 unverified_drift entries); replayed the exact
  `reusable-event-contract.yml` consumer-cross-check logic locally against the updated file — all 22
  `subscriptions:` entries resolve to a registered schema, contract check would PASS.
  `yamllint -d "{extends: default, rules: {line-length: disable, comments: {min-spaces-from-content: 1}, comments-indentation: disable, truthy: disable}}"` on both `consumers.yaml` and
  `reusable-event-contract.yml` → only the pre-existing `missing document start "---"` warning (no
  errors, no new warnings introduced).
- **Effort**: S — **Priority**: P2 — **Status**: **FIXED** (infra-CI portion reconciled; EventCatalog
  tool deployment remains separately OPEN per central `TECHNICAL-DEBT.md`, do-now: no)

---

## Próxima ola — SUPERSEDED 2026-08-22, ver "Census — 2026-08-22" arriba

Esta sección ordenaba por COSTO (lo más barato primero); el encargo de 2026-08-22 pidió
ordenar por RAZÓN (lo que hoy deja pasar algo malo primero) — son criterios distintos y dan
órdenes distintas. `DEBT-W08` (el ítem #1 de esta lista vieja) ya se cerró; `DEBT-W03` sigue
abierto pero rankea de los últimos en la lista por razón porque es plantilla pura, sin riesgo;
`DEBT-W12` subió al puesto #3 por razón (no por costo) porque, al verificarlo, destapó un output
declarado que nunca se puebla — ver la entrada `DEBT-W12` en la sección de arriba para la
evidencia completa (source de `hashicorp/vault-action` citado línea por línea).

**No recensar esto de nuevo bajo el criterio de costo** — el criterio vigente de esta unidad es
razón, no esfuerzo; la lista de 15 restantes ordenada por razón vive en "Census — 2026-08-22" al
inicio de este archivo y es la que debe usarse para decidir qué sigue.

---

## Hallazgo colateral 2026-08-22 — `test_catalog_covers_every_real_fleet_base_image` ya falla en HEAD (NO es uno de los 18, no se toca en esta sesión)

Nota: este encabezado NO contiene la cadena `DEBT` a propósito, para que el censo automatizado
(`grep -niE '^#.*debt'`) no lo cuente como un 19º ticket — es un hallazgo colateral, no un ítem
nuevo de la lista de 18.

**Qué se encontró**: al aplicar la Regla 13 (leer un archivo existente del mismo tipo antes de
escribir código nuevo) para el cierre de DEBT-W07, se corrió `tests/test_approved_base_images.py`
completo como parte de la verificación. Una de sus pruebas preexistentes —
`test_catalog_covers_every_real_fleet_base_image`, que reconcilia el whitelist contra CADA
`Dockerfile` real de la flota— falla:

```
FAIL test_catalog_covers_every_real_fleet_base_image: canonical fleet Dockerfiles use base
images missing from the whitelist (drift):
{'/Users/ileonelperea/.../alebrije-adapt-toronja/Dockerfile': ['playwright.sync_api']}
```

**Confirmado que NO lo causó esta sesión**: se extrajo `tests/test_approved_base_images.py` tal
como está en `HEAD` (`git show HEAD:tests/test_approved_base_images.py`, sin ningún cambio de
esta sesión) y se corrió standalone — falla exactamente igual. El defecto ya vivía en el árbol
antes de que esta unidad tocara nada.

**Causa raíz real (citada, no supuesta)**: `alebrije-adapt-toronja/Dockerfile:163` tiene una línea
`from playwright.sync_api import sync_playwright; \` dentro de un bloque `RUN python3 -c "..."`
multilínea. El `FROM_RE` que usa tanto el test como el gate real en producción
(`reusable-build-push.yml`) es `^FROM\s+...` con `re.MULTILINE` **y `re.IGNORECASE`** — el
`IGNORECASE` hace que la palabra clave de Python `from` (minúscula, al inicio de línea dentro del
heredoc) matchee como si fuera la directiva Docker `FROM`. No es un problema exclusivo del test:
la MISMA regex vive en el step `Gate — validate Dockerfile base images against whitelist` de
`reusable-build-push.yml` (línea ~168), así que si `alebrije-adapt-toronja` corre ese gate real,
recibiría un FALSO POSITIVO bloqueando su build por una imagen `playwright.sync_api:latest` que
no existe — el Dockerfile en sí es correcto (`FROM python:3.12-slim` en las líneas 6 y 41 son las
únicas directivas reales).

**Por qué no se toca en esta sesión**: el `FROM_RE` compartido es el matcher de PRODUCCIÓN que
gatea los ~33 repos de la flota (el mismo que cierran DEBT-§43-SUPPLY-CHAIN-6/7, ya CERRADOS).
Endurecerlo sin medir el impacto en las otras 32 Dockerfiles reales de la flota — para no
introducir un falso positivo NUEVO en dirección contraria, o un falso negativo que sí deje pasar
algo — es un cambio de diseño con su propio radio de explosión de 33 repos, exactamente la clase
de cambio que esta unidad tiene prohibido hacer de pasada. No es uno de los 18 ítems del encargo.
Queda escrito aquí, con `archivo:línea` citado, para que la próxima ronda no tenga que
redescubrirlo.

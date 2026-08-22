# renovate-config

Política compartida de dependencias para mis repos.

> **Actualizar una dependencia es una decisión consciente y planeada.** Nunca un efecto secundario de un build.

## Por qué existe

En julio de 2026, el CI de un proyecto quedó rojo **sin ningún cambio de código**: una dependencia transitiva sin pinear (`mcp`) publicó un major y entró sola en el build. No hubo commit, ni PR, ni una línea de log que mirara nadie. Se descubrió por casualidad, en un PR que solo agregaba dos archivos markdown.

Ese es el problema que este repo resuelve, y tiene dos mitades:

1. **Que nada entre solo.** Lockfiles en todos los repos, y el CI instalando desde el lockfile.
2. **Que actualizar sea visible y decidido.** Eso es Renovate: las actualizaciones llegan como PR, se leen y se aprueban.

## Qué hace la política

| Regla | Valor | Por qué |
|---|---|---|
| `minimumReleaseAge` | **3 días** | Un release malicioso se detecta y se baja en las primeras horas. Esperar tres días esquiva casi todos. |
| `internalChecksFilter` | `strict` | Sin esto, Renovate igual abre el PR y solo avisa que la versión es joven. Con `strict`, no lo abre hasta que cumpla la edad. |
| `automerge` | **false** | El punto entero es que un humano decida. |
| Majors | Requieren aprobación en el tablero | Un major se lee entero antes de existir como PR. |
| Runtime | Un PR por dependencia | Si algo se rompe, el PR dice cuál fue. |
| Dev tooling | Agrupado | No toca producción, no merece ruido. |
| Alertas de seguridad | Cooldown de **1 día**, fuera de horario | Un parche urgente corre distinto. No a cero: un release malicioso también se disfraza de parche. |
| Horario | Lunes de madrugada | Los PRs esperan a la semana, no interrumpen. |
| GitHub Actions | Pineadas por **SHA** | Un tag es un puntero mutable, y el cooldown no lo cubre. Ver abajo. |

## Por qué las Actions se pinean por SHA

`uses: actions/checkout@v7` no pide "la versión 7". Pide **lo que sea que el tag `v7` apunte en el momento de correr el job** — y un tag de Git lo puede mover el dueño del repo cuando quiera, sin cambiar el nombre. Traducido: *descargá código de un tercero, elegido por ese tercero en ese instante, y ejecutalo en un runner que tiene mis secretos en el entorno*.

Así funcionó el compromiso de `tj-actions/changed-files`: se repuntearon los tags existentes a un commit que volcaba los secretos del runner a los logs. Miles de repos que decían `@v35` lo ejecutaron sin haber cambiado una línea. Los que estaban pineados por SHA no se enteraron.

**Y acá está lo que no es obvio: el cooldown de 3 días no protege de esto.** Para las Actions el datasource es `github-tags`, que mira la fecha del **commit**, no la del push. Un tag repunteado a un commit viejo pasa el chequeo de edad sin problema. El pinning por digest es lo único que cierra ese vector.

Lo hace `helpers:pinGitHubActionDigests`, y el punto de tenerlo acá —en vez de pinear a mano en cada repo— es que pinear **no signifique abandonar**: Renovate propone el digest nuevo manteniendo el comentario con la versión, así que las actions siguen actualizándose como cualquier otra dependencia.

```yaml
- - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
+ - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7
```

Para que esos PRs existan, el PAT necesita `Workflows: Read and write` (ver *Setup inicial*). Sin ese permiso el pineo es real pero queda congelado, que es peor que no pinear.

## Sumar un repo

Crear `renovate.json` en la raíz del repo:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["github>CPManuelBovati/renovate-config"]
}
```

Y nada más. El workflow de acá descubre los repos solo, pero **únicamente actúa sobre los que ya tienen ese archivo** (`RENOVATE_ONBOARDING=false` + `RENOVATE_REQUIRE_CONFIG=required`). Un repo sin `renovate.json` se ignora: no hay PRs sorpresa.

Para sacar un repo, borrar el archivo.

## Cómo corre

Un workflow con cron en este repo, los lunes. Es **self-hosted en GitHub Actions**, no la app de Mend: ningún tercero tiene acceso de escritura a los repos privados. Como este repo es público, los minutos de Actions son gratis aunque escanee repos privados.

Corre en `ubuntu-latest` **a propósito**. Nunca en un runner self-hosted — en al menos un repo, ese runner es la máquina de producción.

Se puede disparar a mano desde la pestaña Actions, con `logLevel: debug` y `dryRun` para probar sin abrir PRs.

## Setup inicial (una sola vez)

Hace falta un **PAT** guardado como secret `RENOVATE_TOKEN` en este repo:

1. GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens**
2. Repository access: los repos que quieras que Renovate maneje
3. Permisos: `Contents: Read and write`, `Pull requests: Read and write`, `Issues: Read and write` (para el tablero), `Workflows: Read and write` (solo si querés que actualice actions), `Metadata: Read`
4. Guardarlo acá en Settings → Secrets and variables → Actions → `RENOVATE_TOKEN`

Un token clásico con scope `repo` también sirve, pero da mucho más acceso del necesario. Preferir el fine-grained.

## Si el repo usa pip-compile

El preset **no** configura el manager `pip-compile`, a propósito: depende de cómo se llamen los archivos en cada repo, y encenderlo sin decirle cuáles mirar no hace nada.

Si el repo tiene lockfiles generados con `pip-compile`, hay que declararlos en su propio `renovate.json`:

```json
{
  "extends": ["github>CPManuelBovati/renovate-config"],
  "pip-compile": {
    "managerFilePatterns": ["/^requirements\\.txt$/"]
  },
  "pip_requirements": { "enabled": false }
}
```

Las dos partes son necesarias. Sin la segunda, el manager `pip_requirements` —que sí trae patrones por defecto— le gana los archivos a `pip-compile` y **edita el lockfile generado sin recalcular los hashes**. El resultado es un lockfile inválido que el CI rechaza.

Apagar `pip_requirements` solo es seguro si **todos** los `requirements*.txt` del repo son generados. Si hay alguno escrito a mano, hay que acotar los patrones en vez de apagarlo entero.

## Gotchas conocidos

- **`RENOVATE_BINARY_SOURCE=install`** es necesario para regenerar lockfiles (`pip-compile`, `package-lock.json`). Sin eso, Renovate propone la versión nueva pero no puede actualizar el lockfile, y el PR queda a medias.
- **Si el repo destino tiene un gate de PRs que exige un issue vinculado**, los PRs de Renovate lo van a fallar: no referencian ningún issue porque el PR *es* el registro. Hay que exceptuar a los bots por autor en ese workflow.
- **Si mergear a `main` deploya**, un PR de Renovate mergeado deploya. Obvio, pero conviene tenerlo presente antes de aprobar tres seguidos.
- **La config de este repo se valida en CI** (`.github/workflows/validar-config.yml`). No es ceremonia: un `default.json` inválido no rompe este repo, rompe a **todos** los que lo extienden — y en silencio, porque Renovate falla del otro lado, en un run programado de un lunes a las 3 de la mañana. El síntoma es "hace semanas que no llegan PRs".

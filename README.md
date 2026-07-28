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

## Gotchas conocidos

- **`RENOVATE_BINARY_SOURCE=install`** es necesario para regenerar lockfiles (`pip-compile`, `package-lock.json`). Sin eso, Renovate propone la versión nueva pero no puede actualizar el lockfile, y el PR queda a medias.
- **Si el repo destino tiene un gate de PRs que exige un issue vinculado**, los PRs de Renovate lo van a fallar: no referencian ningún issue porque el PR *es* el registro. Hay que exceptuar a los bots por autor en ese workflow.
- **Si mergear a `main` deploya**, un PR de Renovate mergeado deploya. Obvio, pero conviene tenerlo presente antes de aprobar tres seguidos.

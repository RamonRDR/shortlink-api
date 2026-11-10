<div align="center">

# ShortLink API 🔗

**Acorta enlaces de forma segura. Mide cada redirección. Mantén el control.**

[🇺🇸 English](README.md) · [🇧🇷 Português](README.pt-BR.md) · [🇪🇸 Español](README.es.md)

[![CI](https://github.com/RamonRDR/shortlink-api/actions/workflows/ci.yml/badge.svg)](https://github.com/RamonRDR/shortlink-api/actions/workflows/ci.yml)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org/)
[![MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

![FastAPI](https://img.shields.io/badge/FastAPI-0.116%2B-009688)
![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063)
![SQLAlchemy 2](https://img.shields.io/badge/SQLAlchemy-2-red)
![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791)
![Alembic](https://img.shields.io/badge/Alembic-migrations-555555)
![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED)
![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-4051B5)
![Pydantic Settings](https://img.shields.io/badge/Pydantic-Settings-B72867)

![pytest](https://img.shields.io/badge/pytest-39%20passing-0A9EDC)
![Ruff](https://img.shields.io/badge/Ruff-lint%20%26%20format-D7FF64)
![mypy](https://img.shields.io/badge/mypy-type%20checked-2A6DB4)
![OpenAPI](https://img.shields.io/badge/OpenAPI-documented-6BA539)
![psycopg 3](https://img.shields.io/badge/psycopg-3-4169E1)

</div>

> **Estado del proyecto:** Implementado, revisado por Codex e integrado en `main` mediante el [PR #1](https://github.com/RamonRDR/shortlink-api/pull/1). Todos los hallazgos corregidos. Los checks del PR en GitHub Actions pasaron (39 pruebas, calidad/paquete, PostgreSQL y Docker Compose). Sin despliegue ni publicación.

Acortador de URL con API REST, **Python 3.14, FastAPI, SQLAlchemy, Alembic y
PostgreSQL**. Proyecto de portafolio backend que demuestra diseño de API,
integridad transaccional, concurrencia, pruebas automatizadas y seguridad.

**Público objetivo:** reclutadores de backend, Python, automatización e ingeniería
de software. El `README.md` en inglés es la documentación principal; las
versiones traducidas mantienen recursos, instrucciones y limitaciones equivalentes.

## Funcionalidades

- Crear códigos únicos aleatorios o alias personalizados (201; conflicto 409).
- Redirigir con HTTP 302; enlaces vencidos, inactivos o eliminados devuelven 404.
- Consultar, listar con paginación/filtros, modificar y eliminar lógicamente.
- Mostrar clics totales, agregaciones diarias UTC y enlaces populares.
- Proteger endpoints administrativos con API key y comparación constante.
- Limitar solicitudes administrativas por proceso y validar URL HTTP/HTTPS.
- Documentación OpenAPI en /docs y estado de base de datos en /health.
- Migraciones Alembic, pruebas PostgreSQL y CI con GitHub Actions.

## Tecnologías utilizadas

Python **3.14**, FastAPI, Pydantic v2 y Pydantic Settings para contratos HTTP y configuración tipada; SQLAlchemy **2**, psycopg **3**, PostgreSQL **16** y Alembic para persistencia y migraciones; Uvicorn para ejecutar la API y Docker Compose para orquestación local. GitHub Actions ejecuta pytest, Ruff, mypy, empaquetado wheel, comprobaciones de migración y una prueba de inicio de Compose.

## Estructura del proyecto

| Ruta | Responsabilidad |
| --- | --- |
| `src/shortlink/main.py` | Rutas, inyección de dependencias y respuestas HTTP |
| `src/shortlink/schemas.py` | Contratos validados de entrada y salida |
| `src/shortlink/services.py` | Reglas de negocio y ciclo de vida de enlaces |
| `src/shortlink/repositories.py` | Consultas SQLAlchemy y actualizaciones atómicas |
| `src/shortlink/analytics.py` | Informes agregados |
| `src/shortlink/security.py`, `rate_limit.py` | Autenticación administrativa y límite de solicitudes |
| `migrations/` | Control de versiones del esquema con Alembic |
| `tests/` | Pruebas con una base de datos PostgreSQL desechable |
| `.github/workflows/ci.yml` | Validaciones automáticas de GitHub Actions |

## Arquitectura

    Cliente -> FastAPI -> Pydantic / API key / límite de solicitudes
                             |
                       lógica de negocio
                             |
                         SQLAlchemy
                             |
                         PostgreSQL
                       links + daily_clicks

    Navegador -> GET /{code} -> actualización atómica -> HTTP 302

Sin Redis, colas ni administración compleja de usuarios. Consulte
[decisiones técnicas](docs/decisions.md) para conocer las compensaciones.

## Instalación y configuración

Requisitos: Python **3.14**, PostgreSQL **16** o Docker con Compose.

**Docker Compose:**

    cp .env.example .env
    # Edite .env: establezca POSTGRES_PASSWORD segura y
    # SHORTLINK_ADMIN_API_KEY aleatoria con 32 caracteres como mínimo.
    docker compose up --build -d
    curl http://localhost:8000/health

Compose espera la disponibilidad del banco y ejecuta migraciones. Envía
`POSTGRES_PASSWORD` por separado a la aplicación, que codifica los caracteres
reservados al construir la URL de PostgreSQL. Se admiten `@`, `:`, `/`,
`?` y `#` en la contraseña. No utilice credenciales de ejemplo en
producción; Git ignora el archivo .env.

**Python local:**

Configure PostgreSQL y estas variables:

| Variable | Descripción |
| --- | --- |
| SHORTLINK_DATABASE_URL | postgresql+psycopg://usuario:clave@localhost:5432/shortlink |
| SHORTLINK_ADMIN_API_KEY | Secreto ASCII aleatorio de al menos 32 caracteres |
| SHORTLINK_BASE_URL | URL pública, por ejemplo http://localhost:8000 |
| SHORTLINK_MAX_REQUESTS_PER_MINUTE | Límite administrativo por proceso; predeterminado 60 |

Si configura `SHORTLINK_DATABASE_URL` manualmente, codifique los caracteres
especiales de la contraseña mediante porcentajes. También puede configurar
`SHORTLINK_DB_PASSWORD` junto con `SHORTLINK_DB_HOST`, `SHORTLINK_DB_PORT`,
`SHORTLINK_DB_USER` y `SHORTLINK_DB_NAME` (valores predeterminados:
`db`, `5432`, `shortlink`, `shortlink`). La API key debe ser ASCII.

    python3.14 -m venv .venv
    . .venv/bin/activate
    pip install -e ".[dev]"
    alembic upgrade head
    uvicorn shortlink.main:app --reload

En PowerShell use .venv\Scripts\Activate.ps1.

## Referencia de endpoints

Las rutas públicas incluyen `GET /{code}`, `GET /health`, `GET /docs` y
`GET /openapi.json`. Las rutas de administración y análisis de
`/api/v1` requieren el encabezado `X-API-Key`.

| Método | Endpoint | Propósito |
| --- | --- | --- |
| `POST` | `/api/v1/links` | Crear enlace corto o alias personalizado |
| `GET` | `/api/v1/links` | Listar con `limit`, `offset` y filtro opcional `active` |
| `GET` | `/api/v1/links/{code}` | Consultar detalles administrativos |
| `PATCH` | `/api/v1/links/{code}` | Modificar estado activo o vencimiento |
| `DELETE` | `/api/v1/links/{code}` | Eliminar lógicamente un enlace (`204`) |
| `GET` | `/api/v1/links/{code}/analytics` | Total e historial diario UTC (`days`) |
| `GET` | `/api/v1/analytics` | Totales de enlaces, clics y enlaces populares (`top`) |
| `GET` | `/{code}` | Redirección pública HTTP `302` |
| `GET` | `/health` | Verificar disponibilidad de la base de datos |
| `GET` | `/docs` | Documentación OpenAPI interactiva |

## Ejemplos de solicitudes y respuestas

Sustituya YOUR_ADMIN_KEY por su secreto configurado.

**Crear enlace (201):**

    curl -X POST http://localhost:8000/api/v1/links \
      -H "X-API-Key: YOUR_ADMIN_KEY" \
      -H "Content-Type: application/json" \
      -d '{"target_url":"https://example.org/docs","alias":"my-docs"}'

Respuesta ilustrativa (fechas de ejemplo, no mediciones reales):

    {
      "code": "my-docs",
      "target_url": "https://example.org/docs",
      "short_url": "http://localhost:8000/my-docs",
      "is_active": true,
      "expires_at": null,
      "created_at": "2026-11-07T12:00:00Z",
      "updated_at": "2026-11-07T12:00:00Z",
      "click_count": 0,
      "last_accessed_at": null
    }

**Redireccionar (302):**

    curl -i http://localhost:8000/my-docs

La respuesta incluye Location; solamente GET, no HEAD.

**Administración y estadísticas (requiere X-API-Key):**

    curl -H "X-API-Key: YOUR_ADMIN_KEY" 'http://localhost:8000/api/v1/links?limit=20&offset=0'
    curl -H "X-API-Key: YOUR_ADMIN_KEY" http://localhost:8000/api/v1/links/my-docs
    curl -X PATCH -H "X-API-Key: YOUR_ADMIN_KEY" \
      -H "Content-Type: application/json" -d '{"is_active":false}' \
      http://localhost:8000/api/v1/links/my-docs
    curl -X DELETE -H "X-API-Key: YOUR_ADMIN_KEY" http://localhost:8000/api/v1/links/my-docs
    curl -H "X-API-Key: YOUR_ADMIN_KEY" 'http://localhost:8000/api/v1/links/my-docs/analytics?days=30'
    curl -H "X-API-Key: YOUR_ADMIN_KEY" 'http://localhost:8000/api/v1/analytics?top=10'

La documentación completa de contratos, errores HTTP y ejemplos interactivos
está en http://localhost:8000/docs. Autenticación fallida devuelve 401;
demasiadas solicitudes devuelven 429 con Retry-After.

## Analytics y privacidad

Los conteos reflejan respuestas de redirección preparadas, no visitas
completadas en el destino. Los días utilizan UTC. La aplicación no almacena direcciones
IP, agentes de usuario ni referentes. Docker y Compose desactivan por defecto
los registros de acceso HTTP de Uvicorn, pero los proxies y proveedores de
hosting pueden generar sus propios registros. Las transacciones PostgreSQL
mantienen los totales consistentes ante solicitudes simultáneas.

## Pruebas y GitHub Actions

Con una base de datos de prueba aislada (nombre terminado en _test) y variables configuradas:

    ruff check .
    ruff format --check .
    mypy src/shortlink
    alembic upgrade head
    pytest
    python -m build --wheel
    docker build .

GitHub Actions ejecuta Ruff lint/format, mypy, migraciones y comprobación
de cambios pendientes del esquema Alembic, pruebas PostgreSQL, construcción
del wheel Python y de arranque/health de Docker Compose en PR dirigidos a `main` y pushes
a `main`. Usa runners hospedados y credenciales de prueba, sin desplegar
ni publicar artefactos.

**Evidencia y mantenimiento de los badges:** `pytest 39 passing` representa
un resultado estático confirmado en la [ejecución #42731945341 de GitHub Actions](https://github.com/RamonRDR/shortlink-api/actions/runs/42731945341)
en `main` (`39 passed, 1 warning`). Al añadir, eliminar o parametrizar
pruebas, consulte el job completado `PostgreSQL integration / Test` en
`main` y actualice la cifra en **los tres READMEs** mediante un PR revisado.
El badge CI refleja el workflow dinámicamente; el recuento de pytest
no se actualiza automáticamente. El aviso corresponde a una deprecación
de un tercero y no a un fallo de pruebas.

**Precisión de versiones:** El CI utiliza Python 3.14 y PostgreSQL 16.
El badge `FastAPI 0.116+` indica la versión mínima declarada
(`>=0.116,<1`), no una versión fijada ni observada. Los intervalos de
`pyproject.toml` determinan las versiones compatibles. Uvicorn y
Pydantic Settings no muestran una versión exacta porque no están fijadas.

## Seguridad y limitaciones

Solo los administradores pueden crear enlaces. El servidor nunca visita
el destino. Los esquemas inseguros, IP privadas y hosts locales se rechazan,
pero no se comprueba la reputación de dominios ni se garantiza protección
contra phishing. No use el proyecto para registro público anónimo sin
controles adicionales.

Limitaciones: única clave administrativa; rate limiting en memoria por
proceso y no distribuido; sin seguimiento de visitantes únicos, limpieza
programada, tracing externo ni despliegue automático. Los alias eliminados siguen reservados. Lea
[decisiones técnicas](docs/decisions.md).

## Licencia

[MIT](LICENSE), Copyright (c) 2026 Ramon Rodriguez.

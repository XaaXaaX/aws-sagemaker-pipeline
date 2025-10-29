FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm AS build

RUN pip install uv

ENV BUILD_DIR=build  
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /${BUILD_DIR}

COPY core core

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev


FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm AS runtime

ENV APP_DIR=app \
    BUILD_DIR=build \
    VIRTUAL_ENV=.venv
   
ENV PATH="/$APP_DIR/$VIRTUAL_ENV/bin:$PATH"

WORKDIR /${APP_DIR}

COPY --from=build /${BUILD_DIR} .

RUN chmod +x core

ENTRYPOINT ["python", "core/main.py"]

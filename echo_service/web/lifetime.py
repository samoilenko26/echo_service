# flake8: noqa: B023
import logging
from typing import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from echo_service.constants import MEDIA_TYPE
from echo_service.db.meta import meta
from echo_service.db.models import load_all_models
from echo_service.db.models.endpoint import Endpoint
from echo_service.settings import settings
from echo_service.web.api.endpoints.utils import make_endpoint_name


def _setup_db(app: FastAPI) -> None:  # pragma: no cover
    """
    Creates connection to the database.

    This function creates SQLAlchemy engine instance,
    session_factory for creating sessions
    and stores them in the application's state property.

    :param app: fastAPI application.
    """
    engine = create_async_engine(str(settings.db_url), echo=settings.db_echo)
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )
    app.state.db_engine = engine
    app.state.db_session_factory = session_factory


async def _create_tables() -> None:  # pragma: no cover
    """Populates tables in the database."""
    load_all_models()
    engine = create_async_engine(str(settings.db_url))
    async with engine.begin() as connection:
        await connection.run_sync(meta.create_all)
    await engine.dispose()


async def _activate_routes(app: FastAPI) -> None:
    """
    Create routes from the database.

    :param app: FastAPI application instance
    """
    async with app.state.db_session_factory() as session:
        endpoints = await session.execute(select(Endpoint))
        for endpoint in endpoints.scalars():

            async def dynamic_route(req: Request) -> JSONResponse:
                return JSONResponse(
                    content=endpoint.get_body,
                    headers=endpoint.get_headers,
                    status_code=endpoint.get_code,
                )

            app.add_route(
                endpoint.get_path,
                dynamic_route,
                methods=[endpoint.get_verb],
                name=make_endpoint_name(endpoint.get_id),
            )
            logging.info(
                f"Added dynamic route for endpoint. "
                f"id:{endpoint.get_id}; "
                f"path:{endpoint.get_path}; "
                f"verb:{endpoint.get_verb}; ",
            )


def register_startup_event(
    app: FastAPI,
) -> Callable[[], Awaitable[None]]:  # pragma: no cover
    """
    Actions to run on application startup.

    This function uses fastAPI app to store data
    in the state, such as db_engine.

    :param app: the fastAPI application.
    :return: function that actually performs actions.
    """

    @app.on_event("startup")
    async def _startup() -> None:  # noqa: WPS430
        _setup_db(app)
        await _create_tables()
        await _activate_routes(app)
        pass  # noqa: WPS420

    return _startup


def register_exception_handler(
    app: FastAPI,
) -> Callable[[], Awaitable[None]]:  # pragma: no cover
    """
    Handle HTTPException and generate a JSON response with error details.

    :param app: the fastAPI application.
    :return: function that actually performs actions.
    """

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        response = {
            "errors": [
                {
                    "code": exc.status_code,
                    "detail": exc.detail,
                },
            ],
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=response,
            media_type=MEDIA_TYPE,
        )

    return _http_exception_handler


def register_shutdown_event(
    app: FastAPI,
) -> Callable[[], Awaitable[None]]:  # pragma: no cover
    """
    Actions to run on application's shutdown.

    :param app: fastAPI application.
    :return: function that actually performs actions.
    """

    @app.on_event("shutdown")
    async def _shutdown() -> None:  # noqa: WPS430
        await app.state.db_engine.dispose()

        pass  # noqa: WPS420

    return _shutdown

"""
Configuração de logging estruturado com structlog.

Fornece loggers contextualizados por release/feature para auditoria
completa do pipeline.
"""

from __future__ import annotations

import structlog


def configure_logging(*, json_output: bool = False) -> None:
    """Configura o structlog para o pipeline.

    Args:
        json_output: se True, emite logs em formato JSON.
                     Se False, usa formatação legível para console.
    """
    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(
    release: str | None = None,
    feature: str | None = None,
) -> structlog.BoundLogger:
    """Retorna um logger contextualizado.

    Args:
        release: nome da release (ex: 'JunoSR0').
        feature: label da feature (ex: 'CDT').

    Returns:
        Logger structlog com contexto vinculado.
    """
    log = structlog.get_logger()
    if release:
        log = log.bind(release=release)
    if feature:
        log = log.bind(feature=feature)
    return log

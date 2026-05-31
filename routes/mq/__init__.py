"""lis /v1/mq/* edge routes — proxy to loopback limq broker."""

from .handlers import handle_request

__all__ = ["handle_request"]

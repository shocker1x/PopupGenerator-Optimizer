import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit


class UnsafeURLError(ValueError):
    pass


@dataclass(frozen=True)
class SafeURL:
    scheme: str
    hostname: str
    port: int
    addresses: tuple[str, ...]
    path_and_query: str
    authority: str

    def pinned_url(self, address: str) -> str:
        ip = ipaddress.ip_address(address)
        host = f"[{ip.compressed}]" if ip.version == 6 else ip.compressed
        default_port = 443 if self.scheme == "https" else 80
        port = "" if self.port == default_port else f":{self.port}"
        return f"{self.scheme}://{host}{port}{self.path_and_query}"


async def _resolve_addresses(hostname: str, port: int) -> set[str]:
    loop = asyncio.get_running_loop()
    records = await asyncio.wait_for(
        loop.getaddrinfo(hostname, port, type=socket.SOCK_STREAM),
        timeout=3.0,
    )
    return {record[4][0].split("%", 1)[0] for record in records}


async def validate_url(url: str) -> SafeURL:
    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURLError("Invalid URL") from exc

    if scheme not in {"http", "https"}:
        raise UnsafeURLError("Only HTTP and HTTPS URLs are allowed")
    if not hostname or parsed.username is not None or parsed.password is not None:
        raise UnsafeURLError("URL must have a hostname and no credentials")

    try:
        ipaddress.ip_address(hostname)
        normalized_hostname = hostname.lower()
    except ValueError:
        try:
            normalized_hostname = hostname.rstrip(".").encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise UnsafeURLError("Invalid hostname") from exc
        if not normalized_hostname:
            raise UnsafeURLError("Invalid hostname")

    actual_port = port or (443 if scheme == "https" else 80)
    try:
        literal_ip = ipaddress.ip_address(normalized_hostname)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        addresses = {literal_ip.compressed}
    else:
        try:
            addresses = await _resolve_addresses(normalized_hostname, actual_port)
        except (OSError, asyncio.TimeoutError) as exc:
            raise UnsafeURLError("Could not safely resolve hostname") from exc

    if not addresses:
        raise UnsafeURLError("Hostname resolved to no addresses")
    if any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise UnsafeURLError("Hostname resolves to a non-public IP address")

    selected_addresses = tuple(sorted(addresses))
    if literal_ip is not None and literal_ip.version == 6:
        authority_host = f"[{literal_ip.compressed}]"
    else:
        authority_host = normalized_hostname
    default_port = 443 if scheme == "https" else 80
    authority_port = "" if actual_port == default_port else f":{actual_port}"
    path_and_query = parsed.path or "/"
    if parsed.query:
        path_and_query = f"{path_and_query}?{parsed.query}"

    return SafeURL(
        scheme=scheme,
        hostname=normalized_hostname,
        port=actual_port,
        addresses=selected_addresses,
        path_and_query=path_and_query,
        authority=f"{authority_host}{authority_port}",
    )
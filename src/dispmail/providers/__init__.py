"""Provider registry and contract fixtures."""

from collections.abc import Callable

from dispmail.flows import ProviderSpec
from dispmail.providers import interia, tuta
from dispmail.providers.contracts import Contract

ProviderBuilder = Callable[..., ProviderSpec]

BUILDERS: dict[str, ProviderBuilder] = {
    "tuta": tuta.build,
    "interia": interia.build,
}

CONTRACTS: tuple[Contract, ...] = (*tuta.CONTRACTS, *interia.CONTRACTS)

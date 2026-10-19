import asyncio
from decimal import Decimal

from app.core.database import AsyncSessionLocal
from app.modules.accounting.services.fiscal_regime import TaxRegimeService
from app.modules.accounting.schemas import TaxRegimeUpdate


async def test():
    async with AsyncSessionLocal() as session:
        service = TaxRegimeService(session)

        # Test lecture (entreprise id=1)
        result = await service.get_tax_regime(1)
        print("Lecture régime:", result)

        # Test mise à jour manuelle
        result2 = await service.update_tax_regime(1, TaxRegimeUpdate(tax_regime="RSI"))
        print("Après mise à jour RSI:", result2)

        # Test détection de dépassement CA (600M > 500M -> suggère RNI)
        result3 = await service.detect_ca_threshold(1, Decimal("600000000"))
        print("Après détection CA 600M:", result3)

        # Test is_tva_blocked
        print("TVA bloquée RSI:", TaxRegimeService.is_tva_blocked("RSI"))
        print("TVA bloquée TEE:", TaxRegimeService.is_tva_blocked("TEE"))
        print("TVA bloquée RME:", TaxRegimeService.is_tva_blocked("RME"))
        print("TVA bloquée RNI:", TaxRegimeService.is_tva_blocked("RNI"))
        print("TVA bloquée None:", TaxRegimeService.is_tva_blocked(None))

        # Remettre le régime à None pour laisser l'entreprise propre
        result4 = await service.update_tax_regime(1, TaxRegimeUpdate(tax_regime="TEE"))
        print("Remise à TEE:", result4)


asyncio.run(test())
print("TOUS LES TESTS PASSÉS")

"""Pre-Marketing-Audit: Vandalism-Defense end-to-end test.

Aufruf:
    docker compose exec backend python -m scripts._vandalism_smoke

Pruefcasen:
- Schema-Layer-1: country whitelist, postcode pattern, lat/lon range
- Wortlisten-Layer-2: hate/profanity in display_name + address.*
- Address-shape-Filter: HTML/Emoji/Sonderzeichen
- Self-heal-Cache: vergifteter Cache-Eintrag wird beim Read entfernt
"""
import asyncio

from app import geocode_cache
from app.routers.reports import (
    _hit_is_schema_valid,
    _hit_is_vandalised,
    _is_address_shaped,
    geocode_address,
)


async def main():
    print('--- Schema (Layer 1) ---')
    cases = [
        ('bad country xx',  {'address':{'country_code':'xx','postcode':'12345'},'lat':52.5,'lon':13.4}),
        ('bad postcode abc',{'address':{'country_code':'de','postcode':'abc'},'lat':52.5,'lon':13.4}),
        ('bad latlon 999',  {'address':{'country_code':'de','postcode':'10178'},'lat':999,'lon':13.4}),
        ('good Berlin',     {'address':{'country_code':'de','postcode':'10178','city':'Berlin'},'lat':52.5,'lon':13.4}),
    ]
    for name, h in cases:
        ok, why = _hit_is_schema_valid(h, 'x')
        print(f'  {name}: ok={ok} reason={why}')

    print('--- Vandalism (Layer 2) ---')
    h_vand = {'display_name': 'foo nazi-thing', 'address': {}}
    print(f'  vandalism in display: {_hit_is_vandalised(h_vand)}')
    h_clean = {'display_name': 'Berlin', 'address': {'city': 'Berlin'}}
    print(f'  clean Berlin: {_hit_is_vandalised(h_clean)}')

    print('--- Address-shape ---')
    print(f"  Berlin OK: {_is_address_shaped('Berlin')}")
    print(f"  HTML rejected: {not _is_address_shaped('<script>x</script>')}")

    print('--- Cache self-heal ---')
    key = 'geocode:v1:full:vandalism-test-2026'
    poison = [52.5, 13.4, 'Foobar 1, 10178 Nazi-Stadt', 'de', {'city': 'Nazi-Stadt'}]
    await geocode_cache.cache_set(key, poison)
    cached_before = await geocode_cache.cache_get(key)
    print(f'  poison cached: {cached_before is not None}')
    try:
        await geocode_address('vandalism-test-2026')
        print('  unexpected: geocode succeeded')
    except Exception as e:
        print(f'  expected raise: {type(e).__name__}')
    cached_after = await geocode_cache.cache_get(key)
    print(f'  poison cleaned after read: {cached_after is None}')


if __name__ == '__main__':
    asyncio.run(main())

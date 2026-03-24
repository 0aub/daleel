"""Tiered search query lists for business discovery."""

__all__ = ["TIER_1_QUERIES", "TIER_2_QUERIES", "TIER_3_QUERIES", "get_queries_for_target"]

# Tier 1: High-yield — most common business types, highest density
TIER_1_QUERIES = [
    # Food (most common, highest density)
    "restaurant", "مطعم",
    "coffee shop", "مقهى", "كافيه",
    "fast food", "shawarma",
    "bakery", "مخبز",
    # Grocery
    "supermarket", "سوبرماركت",
    "grocery", "بقالة", "تموينات",
    # Essentials
    "pharmacy", "صيدلية",
    "gas station", "محطة وقود",
    # Common retail
    "mobile phone shop", "جوالات",
    "clothing store", "ملابس",
]

# Tier 2: Medium-yield — broader retail, services, health & beauty
TIER_2_QUERIES = [
    # More food
    "pizza", "burger", "بوفيه",
    "juice bar", "ice cream",
    "مطبخ", "حلويات",
    # More retail
    "electronics store", "furniture store", "أثاث",
    "jewelry store", "shoe store",
    "perfume shop", "عطور",
    "gift shop", "bookstore",
    "toy store", "sports store",
    "stationery store", "shopping mall",
    # Health & beauty
    "beauty salon", "صالون",
    "barber shop", "حلاق",
    "spa", "optical shop", "نظارات",
    # Services
    "car wash", "auto repair", "ورشة",
    "laundry", "مغسلة",
    "tailoring", "خياط",
]

# Tier 3: Low-yield — niche categories for comprehensive coverage
TIER_3_QUERIES = [
    # Niche retail
    "pet shop", "flower shop", "زهور",
    "computer shop", "watch shop", "ساعات",
    "cosmetics store", "مستحضرات تجميل",
    "baby store", "مستلزمات أطفال",
    "camping store",
    # Niche food
    "seafood restaurant", "مأكولات بحرية",
    "indian restaurant", "chinese restaurant",
    "korean restaurant", "turkish restaurant",
    "مطعم يمني", "مطعم بخاري", "مطعم مندي",
    "chocolate shop", "محمصة",
    # Home & building
    "hardware store", "building materials", "مواد بناء",
    "paint store", "plumbing supply",
    "electrical supply", "garden center",
    "curtain shop", "ستائر", "carpet shop", "سجاد",
    # More services
    "tire shop", "car rental", "car dealership",
    "travel agency", "hotel", "فندق",
    "shipping company", "printing shop", "مطبعة",
    "key locksmith", "مفاتيح",
    # Health
    "clinic", "عيادة", "dental clinic",
    "veterinary", "gym", "نادي رياضي",
]


def get_queries_for_target(
    total_grid_points: int,
    target_count: int,
    avg_unique_per_call: int = 6,
) -> list[str]:
    """Select which query tiers to use based on target vs estimated yield.

    Starts with Tier 1 only. Adds Tier 2 and 3 if estimated yield is insufficient.
    """
    # Tier 1 estimate
    tier1_yield = total_grid_points * len(TIER_1_QUERIES) * avg_unique_per_call
    if tier1_yield >= target_count * 1.2:
        return list(TIER_1_QUERIES)

    # Tier 1+2 estimate
    tier2_yield = tier1_yield + total_grid_points * len(TIER_2_QUERIES) * (avg_unique_per_call // 2)
    if tier2_yield >= target_count * 1.2:
        return list(TIER_1_QUERIES) + list(TIER_2_QUERIES)

    # All tiers
    return list(TIER_1_QUERIES) + list(TIER_2_QUERIES) + list(TIER_3_QUERIES)

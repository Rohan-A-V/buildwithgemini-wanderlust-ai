"""Seed script to populate Firestore with sample travel destinations."""

import sys
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-02-0c9eee4fa492"

DESTINATIONS = [
    {
        "id": "kyoto-japan",
        "name": "Kyoto",
        "country": "Japan",
        "tagline": "Ancient temples, serene zen gardens, and traditional tea houses.",
        "description": "Kyoto is the cultural heart of Japan, famous for its classical Buddhist temples, gardens, imperial palaces, Shinto shrines, and traditional wooden houses.",
        "category": "Culture & Heritage",
        "best_season": "Spring (Cherry Blossom) & Autumn",
        "estimated_cost_per_day_usd": 180,
        "rating": 4.9,
        "top_attractions": ["Fushimi Inari Shrine", "Kinkaku-ji (Golden Pavilion)", "Arashiyama Bamboo Grove"],
    },
    {
        "id": "paris-france",
        "name": "Paris",
        "country": "France",
        "tagline": "The City of Light, art, fashion, gastronomy, and romance.",
        "description": "Paris is a global center for art, fashion, gastronomy, and culture. Its 19th-century cityscape is crisscrossed by wide boulevards and the River Seine.",
        "category": "Culture & Romance",
        "best_season": "Spring & Autumn",
        "estimated_cost_per_day_usd": 250,
        "rating": 4.8,
        "top_attractions": ["Eiffel Tower", "Louvre Museum", "Notre-Dame Cathedral", "Montmartre"],
    },
    {
        "id": "banff-canada",
        "name": "Banff National Park",
        "country": "Canada",
        "tagline": "Turquoise glacial lakes and majestic Canadian Rocky Mountain peaks.",
        "description": "Canada's oldest national park, Banff encompasses Rocky Mountain peaks, turquoise glacial lakes, a picture-perfect mountain town, and abundant wildlife.",
        "category": "Nature & Adventure",
        "best_season": "Summer (Hiking) & Winter (Skiing)",
        "estimated_cost_per_day_usd": 200,
        "rating": 4.9,
        "top_attractions": ["Lake Louise", "Moraine Lake", "Banff Upper Hot Springs", "Johnston Canyon"],
    },
    {
        "id": "serengeti-tanzania",
        "name": "Serengeti National Park",
        "country": "Tanzania",
        "tagline": "Home to the Great Migration and vast African savanna wildlife.",
        "description": "The Serengeti is famous for its massive annual migration of wildebeest and zebra, alongside incredible predator-prey wildlife action.",
        "category": "Nature & Safari",
        "best_season": "June to October (Dry Season)",
        "estimated_cost_per_day_usd": 400,
        "rating": 4.95,
        "top_attractions": ["Great Migration River Crossings", "Seronera Valley", "Ngorongoro Crater Nearby"],
    },
    {
        "id": "bali-indonesia",
        "name": "Bali",
        "country": "Indonesia",
        "tagline": "Island of Gods: lush rice terraces, vibrant beaches, and spiritual retreats.",
        "description": "Bali is an Indonesian island known for its forested volcanic mountains, iconic rice paddies, beaches, coral reefs, and rich Hindu culture.",
        "category": "Beach & Wellness",
        "best_season": "April to October",
        "estimated_cost_per_day_usd": 110,
        "rating": 4.75,
        "top_attractions": ["Ubud Rice Terraces", "Uluwatu Temple", "Tegallalang", "Seminyak Beach"],
    },
]


def seed_database():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("destinations")

    count = 0
    for dest in DESTINATIONS:
        doc_id = dest["id"]
        collection_ref.document(doc_id).set(dest)
        print(f"  ✓ Seeded destination: {dest['name']} ({doc_id})")
        count += 1

    print(f"Successfully seeded {count} destinations into Firestore collection 'destinations'!")


if __name__ == "__main__":
    seed_database()

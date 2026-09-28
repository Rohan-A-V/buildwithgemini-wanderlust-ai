import datetime
import json
import urllib.request
import uuid
from typing import List, Optional
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types

from .a2ui_utils import a2ui_callback

# Hardcoded project ID and bucket name as required for Agent Platform compatibility
PROJECT_ID = "qwiklabs-gcp-02-0c9eee4fa492"
BUCKET_NAME = "wanderlust-ai-media-qwiklabs-gcp-02-0c9eee4fa492"


def get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with the hardcoded GCP project ID."""
    return firestore.Client(project=PROJECT_ID)


def get_exchange_rate(from_currency: str = "USD", to_currency: str = "JPY") -> str:
    """Fetches real-time live currency exchange rates.

    Args:
        from_currency: 3-letter source currency code (e.g. 'USD', 'EUR', 'GBP').
        to_currency: 3-letter target currency code (e.g. 'JPY', 'EUR', 'GBP', 'CAD').

    Returns:
        A string with the current exchange rate.
    """
    try:
        from_c = from_currency.upper().strip()
        to_c = to_currency.upper().strip()
        url = f"https://api.frankfurter.app/latest?from={from_c}&to={to_c}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            rate = data.get("rates", {}).get(to_c)
            if rate:
                return f"1 {from_c} = {rate} {to_c} (as of {data.get('date')})"
            return f"Rate from {from_c} to {to_c} not found."
    except Exception as e:
        return f"Error getting exchange rate: {e}"


def get_public_holidays(country_code: str = "JP") -> str:
    """Fetches upcoming public holidays for a destination country using the Nager.Date API.

    Args:
        country_code: 2-letter ISO country code (e.g. 'JP' for Japan, 'FR' for France, 'US' for USA, 'IN' for India).

    Returns:
        A formatted list of upcoming public holidays for the specified country.
    """
    try:
        cc = country_code.upper().strip()
        url = f"https://date.nager.at/api/v3/NextPublicHolidays/{cc}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 204:
                return f"No upcoming public holiday records found in Nager.Date for country code '{cc}'."
            content = resp.read().decode().strip()
            if not content:
                return f"No upcoming public holiday records found for country code '{cc}'."

            holidays = json.loads(content)
            if not holidays or not isinstance(holidays, list):
                return f"No upcoming public holidays found for country code '{cc}'."

            items = []
            for h in holidays[:6]:
                name = h.get("name")
                local_name = h.get("localName")
                date = h.get("date")
                items.append(f"• {date}: {name} ({local_name})")

            return f"Upcoming Public Holidays in {cc}:\n" + "\n".join(items)
    except Exception as e:
        return f"Error fetching public holidays for '{country_code}': {e}"


def generate_destination_image(
    prompt: str, tool_context: ToolContext
) -> str:
    """Generates a travel preview image or postcard for a destination.

    Uses gemini-3.1-flash-lite-image in the global region. Saves the image as
    an ADK artifact for the Playground's Artifacts panel, uploads the bytes directly
    to public Cloud Storage, and returns its public HTTPS URL.

    Args:
        prompt: Descriptive prompt for the travel image to generate (e.g. 'A vintage travel postcard of Kyoto cherry blossoms').
        tool_context: Tool execution context provided automatically by ADK framework.

    Returns:
        The public HTTPS GCS URL of the generated image (https://storage.googleapis.com/<bucket>/<object>).
    """
    try:
        genai_client = genai.Client(
            vertexai=True, project=PROJECT_ID, location="global"
        )
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not image_bytes:
            return "Failed to generate image bytes from model."

        ext = "jpg" if "jpeg" in mime_type or "jpg" in mime_type else "png"
        filename = f"generated_{uuid.uuid4().hex[:8]}.{ext}"

        # 1. Save artifact for Playground Artifacts panel
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload image bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating destination image: {e}"


def generate_destination_video(
    prompt: str, tool_context: ToolContext
) -> str:
    """Generates a short travel video for a destination, hotel, or activity.

    Uses Google's Omni model (gemini-omni-flash-preview) in the global region. Saves the video
    as an ADK artifact for the Playground's Artifacts panel, uploads the video bytes directly
    to public Cloud Storage, and returns its public HTTPS URL.

    Args:
        prompt: Descriptive prompt for the travel video to generate (e.g. 'A 3-second video of sunset over Kyoto bamboo forest').
        tool_context: Tool execution context provided automatically by ADK framework.

    Returns:
        The public HTTPS GCS URL of the generated video (https://storage.googleapis.com/<bucket>/<object>).
    """
    try:
        import base64
        import google.auth
        from google.auth.transport.requests import Request
        import requests

        credentials, _ = google.auth.default()
        credentials.refresh(Request())
        token = credentials.token

        url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/global/interactions"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "gemini-omni-flash-preview",
            "input": [{"type": "text", "text": prompt}],
            "generation_config": {
                "video_config": {
                    "task": "text_to_video"
                }
            },
        }

        res = requests.post(url, headers=headers, json=body, timeout=120)
        if res.status_code != 200:
            return f"Error from Omni video API (HTTP {res.status_code}): {res.text}"

        data = res.json()
        video_bytes = None
        mime_type = "video/mp4"

        for step in data.get("steps", []):
            for content in step.get("content", []):
                if content.get("type") == "video":
                    raw_data = content.get("data") or content.get("bytesBase64Encoded")
                    if raw_data:
                        video_bytes = base64.b64decode(raw_data)
                    if content.get("mime_type"):
                        mime_type = content.get("mime_type")
                    break

        if not video_bytes:
            return "Failed to extract video bytes from Omni model response."

        filename = f"video_{uuid.uuid4().hex[:8]}.mp4"

        # 1. Save artifact for Playground Artifacts panel
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload video bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating destination video: {e}"


def search_destinations(query: str = "") -> str:

    """Searches the destination catalog in Firestore for travel destinations matching a query.

    Args:
        query: Optional search keyword or destination name (e.g. 'Japan', 'beach', 'Paris').
               If empty, returns all available destinations.

    Returns:
        A formatted list of matching travel destinations with key details.
    """
    try:
        db = get_firestore_client()
        docs = db.collection("destinations").stream()
        results = []
        q_lower = query.lower().strip()

        for doc in docs:
            data = doc.to_dict()
            doc_id = doc.id
            name = data.get("name", "")
            country = data.get("country", "")
            description = data.get("description", "")
            tags = [t.lower() for t in data.get("tags", [])]

            if (
                not q_lower
                or q_lower in name.lower()
                or q_lower in country.lower()
                or q_lower in description.lower()
                or any(q_lower in tag for tag in tags)
            ):
                results.append(
                    f"• ID: {doc_id} | Name: {name}, {country}\n"
                    f"  Description: {description}\n"
                    f"  Best Time to Visit: {data.get('best_time_to_visit', 'N/A')}\n"
                    f"  Avg Cost/Day: {data.get('avg_cost_per_day', 'N/A')}\n"
                    f"  Highlights: {', '.join(data.get('highlights', []))}"
                )

        if not results:
            return f"No destinations found matching '{query}' in Firestore."

        return f"Found {len(results)} destination(s):\n\n" + "\n\n".join(results)
    except Exception as e:
        return f"Error querying Firestore destinations: {e}"


def get_destination_details(destination_id: str) -> str:
    """Retrieves full details for a specific destination by its ID from Firestore.

    Args:
        destination_id: The document ID of the destination (e.g. 'kyoto-japan', 'paris-france').

    Returns:
        A detailed summary of the destination or an error message if not found.
    """
    try:
        db = get_firestore_client()
        doc_ref = db.collection("destinations").document(destination_id)
        doc = doc_ref.get()

        if not doc.exists:
            return f"Destination with ID '{destination_id}' not found."

        data = doc.to_dict()
        return (
            f"Destination Details for {data.get('name')}, {data.get('country')}:\n"
            f"- Description: {data.get('description')}\n"
            f"- Best Time to Visit: {data.get('best_time_to_visit')}\n"
            f"- Avg Cost Per Day: {data.get('avg_cost_per_day')}\n"
            f"- Highlights: {', '.join(data.get('highlights', []))}\n"
            f"- Tags: {', '.join(data.get('tags', []))}"
        )
    except Exception as e:
        return f"Error retrieving destination '{destination_id}': {e}"


def save_destination(
    name: str,
    country: str,
    description: str,
    best_time_to_visit: str,
    avg_cost_per_day: str,
    highlights: List[str],
) -> str:
    """Saves a new travel destination or updates an existing destination in Firestore.

    Args:
        name: Name of the destination city or region (e.g. 'Tokyo').
        country: Country name (e.g. 'Japan').
        description: Brief description of the destination.
        best_time_to_visit: Best seasons or months to visit.
        avg_cost_per_day: Estimated daily budget (e.g. '$150/day').
        highlights: List of top attractions or activities.

    Returns:
        Confirmation message upon saving to Firestore.
    """
    try:
        db = get_firestore_client()
        doc_id = f"{name.lower().replace(' ', '-')}-{country.lower().replace(' ', '-')}"
        dest_data = {
            "name": name,
            "country": country,
            "description": description,
            "best_time_to_visit": best_time_to_visit,
            "avg_cost_per_day": avg_cost_per_day,
            "highlights": highlights,
            "tags": [name.lower(), country.lower()],
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        db.collection("destinations").document(doc_id).set(dest_data, merge=True)
        return f"Successfully saved destination '{name}, {country}' with ID '{doc_id}' to Firestore."
    except Exception as e:
        return f"Error saving destination to Firestore: {e}"


def save_trip_itinerary(
    destination: str, duration_days: int, total_budget: str, notes: str = ""
) -> str:
    """Saves a traveler's trip itinerary into the Firestore 'itineraries' collection.

    Args:
        destination: Destination name or city.
        duration_days: Duration of the trip in days.
        total_budget: Estimated total budget (e.g., '$1,200').
        notes: Special requirements, activities, or notes for the trip.

    Returns:
        Confirmation message upon creating the trip itinerary document.
    """
    try:
        db = get_firestore_client()
        doc_ref = db.collection("itineraries").document()
        itinerary_data = {
            "destination": destination,
            "duration_days": duration_days,
            "total_budget": total_budget,
            "notes": notes,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        doc_ref.set(itinerary_data)
        return f"Successfully saved trip itinerary to Firestore (Itinerary ID: {doc_ref.id})!"
    except Exception as e:
        return f"Error saving trip itinerary to Firestore: {e}"


def get_weather(query: str) -> str:
    """Simulates a web search for current weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    elif "kyoto" in query.lower() or "japan" in query.lower():
        return "It's 68°F (20°C) and clear with mild pleasant breezes."
    elif "paris" in query.lower():
        return "It's 64°F (18°C) and partly cloudy."
    return "It's 75°F (24°C) and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    elif "kyoto" in query.lower() or "tokyo" in query.lower() or "japan" in query.lower():
        tz_identifier = "Asia/Tokyo"
    elif "paris" in query.lower():
        tz_identifier = "Europe/Paris"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


from pathlib import Path
from google.adk.agents.callback_context import CallbackContext
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

# Memory Bank ID derived from remote_agent_runtime_id in deployment_metadata.json
MEMORY_BANK_ID = "804303750834421760"


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback to automatically extract and save user memories at the end of each turn."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        print(f"Memory bank save ignored: {e}")
    return None


def memory_bank_service_builder():
    """Memory Bank service builder for deployed agent runtime."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-east1",
        agent_engine_id=MEMORY_BANK_ID,
    )


# Load Agent Engine resource name from deployment_metadata.json for sandbox code execution
metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
code_executor = None
if metadata_path.exists():
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        sandbox_name = metadata.get("sandbox_resource_name")
        engine_name = metadata.get("remote_agent_runtime_id")
        if sandbox_name:
            code_executor = AgentEngineSandboxCodeExecutor(sandbox_resource_name=sandbox_name)
        elif engine_name:
            code_executor = AgentEngineSandboxCodeExecutor(agent_engine_resource_name=engine_name)
    except Exception as e:
        print(f"Warning: Failed to initialize AgentEngineSandboxCodeExecutor: {e}")


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are Wanderlust AI, a personalized travel concierge agent. "
        "You remember user travel preferences, budget levels, and interests across sessions. "
        "You help users discover amazing travel destinations, search catalog options stored in Firestore, "
        "save new destinations or itineraries to Firestore, check weather and time, calculate trip budgets "
        "and expense splits by writing Python code in ```python ... ``` code blocks, and plan memorable trips."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property (\'h1\', \'h2\', \'body\') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or \'kind\'/\'data\'/\'metadata\' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="wanderlust_ai",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        search_destinations,
        get_destination_details,
        save_destination,
        save_trip_itinerary,
        get_exchange_rate,
        get_public_holidays,
        generate_destination_image,
        generate_destination_video,
        get_weather,
        get_current_time,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)


import json
import os
from datetime import datetime

from google.cloud import firestore
from google.oauth2 import service_account


def init_firestore_client():
    """Initialize a Firestore client from JSON credentials or a credentials path."""
    creds_json_env = os.getenv("GOOGLE_CREDENTIALS_JSON")
    creds_path_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if creds_json_env:
        try:
            creds_info = json.loads(creds_json_env)
            creds = service_account.Credentials.from_service_account_info(creds_info)
            project_id = creds_info.get("project_id")
            return firestore.Client(credentials=creds, project=project_id)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Firestore credentials from GOOGLE_CREDENTIALS_JSON: {e}"
            ) from e

    if creds_path_env:
        if not os.path.exists(creds_path_env):
            raise RuntimeError(
                f"GOOGLE_APPLICATION_CREDENTIALS path not found: {creds_path_env}"
            )
        return firestore.Client()

    raise RuntimeError(
        "No Firestore credentials found. Set GOOGLE_CREDENTIALS_JSON or "
        "GOOGLE_APPLICATION_CREDENTIALS."
    )


try:
    db = init_firestore_client()
except Exception as e:
    db = None
    print(f"WARNING: Firestore disabled: {e}")


def backup_to_firestore(company: str, section: str, items: list):
    """
    Save overflow items to Firestore under:
    - companies/{company}/{section}/{doc}
    - korean_sources/{source}/articles/{doc}
    """
    if not items:
        return

    if db is None:
        print(
            f"WARNING: Skipping Firestore backup for {company}/{section}: "
            "client is not configured."
        )
        return

    collection_name = "korean_sources" if section == "articles" else "companies"
    doc_ref = db.collection(collection_name).document(company).collection(section)

    for item in items:
        doc_id = item.get("url") or item.get("title")
        if doc_id:
            doc_id = doc_id.replace("/", "_")[:500]
        else:
            doc_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

        item_with_meta = {
            **item,
            "backed_up_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

        try:
            doc_ref.document(doc_id).set(item_with_meta)
        except Exception as e:
            print(f"WARNING: Firestore backup failed for {company} ({section}): {e}")

    print(f"Backed up {len(items)} items for {company} -> {section}")


def restore_from_firestore(company: str, section: str, limit: int = 20) -> list:
    """Restore items from Firestore for a given company/source and section."""
    if db is None:
        print(
            f"WARNING: Skipping Firestore restore for {company}/{section}: "
            "client is not configured."
        )
        return []

    collection_name = "korean_sources" if section == "articles" else "companies"
    doc_ref = db.collection(collection_name).document(company).collection(section)

    try:
        docs = (
            doc_ref.order_by("backed_up_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        restored_items = [doc.to_dict() for doc in docs]
        print(f"Restored {len(restored_items)} items for {company} -> {section}")
        return restored_items
    except Exception as e:
        print(f"WARNING: Firestore restore failed for {company} ({section}): {e}")
        return []

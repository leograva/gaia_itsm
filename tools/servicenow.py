"""
ServiceNow tools for incident management.

All functions read credentials from environment variables:
    SERVICENOW_INSTANCE  - your instance subdomain (e.g. "mycompany")
    SERVICENOW_USERNAME  - basic-auth username
    SERVICENOW_PASSWORD  - basic-auth password

Alternatively, token-based auth is supported via:
    SERVICENOW_API_TOKEN - Bearer token (takes precedence over basic auth)
"""

import os
import requests
from typing import Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _base_url() -> str:
    instance = os.getenv("SERVICENOW_INSTANCE", "")
    if not instance:
        raise ValueError(
            "Environment variable SERVICENOW_INSTANCE is not set. "
            "Set it to your ServiceNow subdomain (e.g. 'mycompany')."
        )
    return f"https://{instance}.service-now.com/api/now/table"


def _auth() -> tuple | None:
    """Returns (username, password) tuple or None if token auth is used."""
    username = os.getenv("SERVICENOW_USERNAME")
    password = os.getenv("SERVICENOW_PASSWORD")
    if username and password:
        return (username, password)
    return None


def _headers() -> dict:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    token = os.getenv("SERVICENOW_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(endpoint: str, params: dict) -> dict:
    """Executes a GET request against the ServiceNow Table API."""
    try:
        response = requests.get(
            url=f"{_base_url()}/{endpoint}",
            headers=_headers(),
            auth=_auth(),
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        return {"status": "success", "data": response.json().get("result", [])}
    except requests.exceptions.HTTPError as e:
        return {
            "status": "error",
            "message": f"HTTP error {e.response.status_code}: {e.response.text}",
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "Could not connect to ServiceNow. Check SERVICENOW_INSTANCE.",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------

# Mapping of human-readable state names to ServiceNow state codes
INCIDENT_STATES = {
    "new": "1",
    "in_progress": "2",
    "on_hold": "3",
    "resolved": "6",
    "closed": "7",
    "canceled": "8",
}


def get_incident_by_number(incident_number: str) -> dict:
    """
    Retrieves a specific incident by its number (e.g. 'INC0010001').

    Args:
        incident_number: The ServiceNow incident number.

    Returns:
        A dict with 'status' and either 'data' (incident fields) or 'message' on error.
    """
    params = {
        "sysparm_query": f"number={incident_number}",
        "sysparm_fields": (
            "number,short_description,description,state,priority,urgency,"
            "impact,caller_id,assigned_to,assignment_group,opened_at,"
            "resolved_at,close_notes,category,subcategory,sys_id"
        ),
        "sysparm_limit": 1,
    }
    result = _get("incident", params)

    if result["status"] == "success":
        data = result["data"]
        if not data:
            return {"status": "not_found", "message": f"Incident {incident_number} not found."}
        return {"status": "success", "incident": data[0]}

    return result


def search_incidents_by_caller(
    caller_name: str,
    limit: int = 10,
    state: Optional[str] = None,
) -> dict:
    """
    Searches for incidents associated with a specific caller/requester.

    Args:
        caller_name: Full or partial name of the caller (e.g. 'John Doe').
        limit: Maximum number of incidents to return (default 10, max 50).
        state: Optional filter by state: 'new', 'in_progress', 'on_hold',
               'resolved', 'closed', or 'canceled'.

    Returns:
        A dict with 'status' and a list of incidents in 'data', or 'message' on error.
    """
    limit = min(int(limit), 50)
    query = f"caller_id.nameLIKE{caller_name}^ORDERBYDESCopened_at"

    if state:
        state_code = INCIDENT_STATES.get(state.lower())
        if not state_code:
            return {
                "status": "error",
                "message": (
                    f"Invalid state '{state}'. "
                    f"Valid options: {', '.join(INCIDENT_STATES.keys())}"
                ),
            }
        query = f"caller_id.nameLIKE{caller_name}^state={state_code}^ORDERBYDESCopened_at"

    params = {
        "sysparm_query": query,
        "sysparm_fields": (
            "number,short_description,state,priority,urgency,"
            "caller_id,assigned_to,opened_at,resolved_at"
        ),
        "sysparm_limit": limit,
    }
    result = _get("incident", params)

    if result["status"] == "success" and not result["data"]:
        return {"status": "not_found", "message": f"No incidents found for caller '{caller_name}'."}

    return result


def search_incidents_by_state(
    state: str,
    limit: int = 10,
    assignment_group: Optional[str] = None,
) -> dict:
    """
    Lists incidents filtered by their current state.

    Args:
        state: Incident state to filter by — 'new', 'in_progress', 'on_hold',
               'resolved', 'closed', or 'canceled'.
        limit: Maximum number of incidents to return (default 10, max 50).
        assignment_group: Optional filter by assignment group name.

    Returns:
        A dict with 'status' and a list of incidents in 'data', or 'message' on error.
    """
    state_code = INCIDENT_STATES.get(state.lower())
    if not state_code:
        return {
            "status": "error",
            "message": (
                f"Invalid state '{state}'. "
                f"Valid options: {', '.join(INCIDENT_STATES.keys())}"
            ),
        }

    limit = min(int(limit), 50)
    query = f"state={state_code}^ORDERBYDESCopened_at"

    if assignment_group:
        query = (
            f"state={state_code}"
            f"^assignment_group.nameLIKE{assignment_group}"
            f"^ORDERBYDESCopened_at"
        )

    params = {
        "sysparm_query": query,
        "sysparm_fields": (
            "number,short_description,state,priority,urgency,"
            "caller_id,assigned_to,assignment_group,opened_at"
        ),
        "sysparm_limit": limit,
    }
    result = _get("incident", params)

    if result["status"] == "success" and not result["data"]:
        return {
            "status": "not_found",
            "message": f"No incidents found with state '{state}'.",
        }

    return result


def get_incident_updates(incident_number: str, limit: int = 10) -> dict:
    """
    Retrieves the activity/journal entries (work notes and comments) of an incident.

    Args:
        incident_number: The ServiceNow incident number (e.g. 'INC0010001').
        limit: Maximum number of journal entries to return (default 10).

    Returns:
        A dict with 'status' and journal entries in 'data', or 'message' on error.
    """
    # First resolve the sys_id from the incident number
    incident_result = get_incident_by_number(incident_number)
    if incident_result["status"] != "success":
        return incident_result

    sys_id = incident_result["incident"].get("sys_id")
    if not sys_id:
        return {"status": "error", "message": "Could not retrieve sys_id for incident."}

    params = {
        "sysparm_query": f"element_id={sys_id}^ORDERBYDESCsys_created_on",
        "sysparm_fields": "sys_created_on,sys_created_by,element,value",
        "sysparm_limit": min(int(limit), 50),
    }
    result = _get("sys_journal_field", params)

    if result["status"] == "success" and not result["data"]:
        return {
            "status": "not_found",
            "message": f"No journal entries found for incident {incident_number}.",
        }

    return result

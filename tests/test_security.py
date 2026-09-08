import uuid

from fastapi.testclient import TestClient



def register_org(client: TestClient, name: str, slug: str, email: str, password: str):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": name,
            "organization_slug": slug,
            "full_name": f"{name} Owner",
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": email,
            "password": password,
        },
    )
    assert response.status_code == 200, response.text

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def test_tenant_isolation(client: TestClient) -> None:
    suffix = uuid.uuid4().hex[:8]

    email_a = f"owner-a-{suffix}@example.com"
    email_b = f"owner-b-{suffix}@example.com"

    password_a = "TenantA123!"
    password_b = "TenantB123!"


    org_a = register_org(
        client,
        "Security Tenant A",
        f"security-a-{suffix}",
        email_a,
        password_a,
    )

    org_b = register_org(
        client,
        "Security Tenant B",
        f"security-b-{suffix}",
        email_b,
        password_b,
    )

    assert org_a["organization_id"] != org_b["organization_id"]

    headers_a = login(client, email_a, password_a)
    headers_b = login(client, email_b, password_b)

    ticket_a_response = client.post(
        "/api/v1/tickets",
        headers=headers_a,
        json={
            "title": "Tenant A ticket",
            "description": "Visible only to Tenant A",
            "priority": "high",
        },
    )
    assert ticket_a_response.status_code == 201, ticket_a_response.text

    ticket_b_response = client.post(
        "/api/v1/tickets",
        headers=headers_b,
        json={
            "title": "Tenant B secret ticket",
            "description": "Tenant A must never access this ticket",
            "priority": "high",
        },
    )
    assert ticket_b_response.status_code == 201, ticket_b_response.text

    ticket_b = ticket_b_response.json()

    # Tenant A list must contain only Tenant A data.
    list_response = client.get(
        "/api/v1/tickets",
        headers=headers_a,
    )

    assert list_response.status_code == 200

    titles = [ticket["title"] for ticket in list_response.json()]

    assert "Tenant A ticket" in titles
    assert "Tenant B secret ticket" not in titles

    # Tenant A must not be able to read Tenant B's ticket.
    read_response = client.get(
        f"/api/v1/tickets/{ticket_b['id']}",
        headers=headers_a,
    )

    assert read_response.status_code == 404
    assert read_response.json()["detail"] == "Ticket not found"

    # Tenant A must not be able to modify Tenant B's ticket.
    patch_response = client.patch(
        f"/api/v1/tickets/{ticket_b['id']}",
        headers=headers_a,
        json={
            "status": "resolved",
        },
    )

    assert patch_response.status_code == 404
    assert patch_response.json()["detail"] == "Ticket not found"


def test_member_role_enforcement(client: TestClient) -> None:
    suffix = uuid.uuid4().hex[:8]

    owner_email = f"owner-{suffix}@example.com"
    agent_email = f"agent-{suffix}@example.com"
    blocked_email = f"blocked-{suffix}@example.com"

    owner_password = "OwnerTest123!"
    agent_password = "AgentTest123!"

    owner = register_org(
        client,
        "Membership Security",
        f"membership-{suffix}",
        owner_email,
        owner_password,
    )

    owner_headers = login(
        client,
        owner_email,
        owner_password,
    )

    # Owner creates an agent.
    agent_response = client.post(
        "/api/v1/members",
        headers=owner_headers,
        json={
            "full_name": "Security Test Agent",
            "email": agent_email,
            "password": agent_password,
            "role": "agent",
        },
    )

    assert agent_response.status_code == 201, agent_response.text

    agent = agent_response.json()

    # Server must assign the owner's tenant automatically.
    assert agent["organization_id"] == owner["organization_id"]
    assert agent["role"] == "agent"

    agent_headers = login(
        client,
        agent_email,
        agent_password,
    )

    # Agent must not have organization-management privileges.
    forbidden_response = client.post(
        "/api/v1/members",
        headers=agent_headers,
        json={
            "full_name": "Forbidden User",
            "email": blocked_email,
            "password": "BlockedTest123!",
            "role": "user",
        },
    )

    assert forbidden_response.status_code == 403
    assert (
        forbidden_response.json()["detail"]
        == "Only organization owners can create members"
    )

    # Prove the failed request produced no database side effect:
    # the owner should still be able to create that same email.
    owner_create_response = client.post(
        "/api/v1/members",
        headers=owner_headers,
        json={
            "full_name": "Allowed User",
            "email": blocked_email,
            "password": "AllowedTest123!",
            "role": "user",
        },
    )

    assert owner_create_response.status_code == 201, owner_create_response.text
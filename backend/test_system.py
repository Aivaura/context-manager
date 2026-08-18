import asyncio
import sys
import httpx

from app.main import app

async def run_async_tests():
    print("--- 1. Testing /health Endpoint ---")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        print(f"Health Status: {resp.status_code}, Response: {resp.json()}")
        assert resp.status_code == 200

        print("\n--- 2. Testing /api/v1/auth/login ---")
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@aivaura.com", "password": "changeme123"}
        )
        print(f"Login Status: {login_resp.status_code}")
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Authenticated successfully.")

        print("\n--- 3. Testing GET /api/v1/connectors ---")
        conn_resp = await client.get("/api/v1/connectors", headers=headers)
        print(f"Connectors Status: {conn_resp.status_code}, Count: {len(conn_resp.json()['data'])}")
        assert conn_resp.status_code == 200

        print("\n--- 4. Testing GET /api/v1/documents ---")
        doc_resp = await client.get("/api/v1/documents", headers=headers)
        print(f"Documents Status: {doc_resp.status_code}, Count: {len(doc_resp.json()['data'])}")
        assert doc_resp.status_code == 200

        print("\n--- 5. Testing POST /api/v1/notes (Note Studio CRUD & RAG indexing) ---")
        note_resp = await client.post(
            "/api/v1/notes",
            headers=headers,
            json={
                "title": "Q3 Enterprise Strategy Note",
                "content": "Our key Q3 strategy involves launching Context Store to 1000+ users. [[Google Drive]]",
                "tags": ["strategy", "enterprise", "q3"]
            }
        )
        print(f"Create Note Status: {note_resp.status_code}, Title: {note_resp.json()['data']['title']}")
        assert note_resp.status_code == 200
        note_id = note_resp.json()["data"]["id"]

        print("\n--- 6. Testing GET /api/v1/notes ---")
        list_notes_resp = await client.get("/api/v1/notes", headers=headers)
        print(f"List Notes Status: {list_notes_resp.status_code}, Count: {len(list_notes_resp.json()['data'])}")
        assert list_notes_resp.status_code == 200

        print("\n--- 7. Testing GET /api/v1/graph (Knowledge Network Graph) ---")
        graph_resp = await client.get("/api/v1/graph", headers=headers)
        print(f"Graph Status: {graph_resp.status_code}, Total Nodes: {graph_resp.json()['data']['stats']['total_nodes']}")
        assert graph_resp.status_code == 200

        print("\n--- 8. Testing POST /api/v1/connectors/google_drive/test (Ping Test) ---")
        test_resp = await client.post("/api/v1/connectors/google_drive/test", headers=headers)
        print(f"Connector Ping Status: {test_resp.status_code}, Result: {test_resp.json()['data']['status']}")
        assert test_resp.status_code == 200

        print("\n--- 9. Testing GET /api/v1/admin/stats ---")
        stats_resp = await client.get("/api/v1/admin/stats", headers=headers)
        print(f"Stats Status: {stats_resp.status_code}, Data: {stats_resp.json()['data']}")
        assert stats_resp.status_code == 200

        print("\n--- 10. Clean-up: DELETE /api/v1/notes/{id} ---")
        del_note_resp = await client.delete(f"/api/v1/notes/{note_id}", headers=headers)
        print(f"Delete Note Status: {del_note_resp.status_code}")
        assert del_note_resp.status_code == 200

        print("\nALL ENTERPRISE BACKEND SYSTEM TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    try:
        asyncio.run(run_async_tests())
    except Exception as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)

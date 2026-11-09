async def test_root(client):
    response = await client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["message"] == "success"
    assert body["data"] is None

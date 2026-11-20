def authenticate_client(client, access_token: str, csrf_token: str = "test-csrf-token") -> None:
    client.cookies.set("campusflow_session", access_token)
    client.cookies.set("campusflow_csrf", csrf_token)
    client.headers.update({"Origin": "http://localhost:3000", "X-CSRF-Token": csrf_token})

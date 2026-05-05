def test_security_hashing_and_access_token_decode(app_ctx):
    security = app_ctx["security"]

    password_hash = security.hash_password("12345678")
    assert password_hash != "12345678"
    assert security.verify_password("12345678", password_hash)
    assert not security.verify_password("87654321", password_hash)

    otp_hash = security.hash_otp("654321")
    assert security.verify_otp("654321", otp_hash)
    assert not security.verify_otp("000000", otp_hash)

    access_token = security.generate_access_token("user-1")
    payload = security.decode_token(access_token)
    assert payload["sub"] == "user-1"
    assert payload["type"] == "access"
    assert payload["iss"] == "gapkassa-test"
